from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from typing import List, Dict, Any, Tuple
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Text Editor Feedback API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


class DraftRequest(BaseModel):
    text: str


class WordRange(BaseModel):
    start: int
    end: int


class FeedbackItem(BaseModel):
    category: str
    word_range: WordRange
    comments: str


class FeedbackResponse(BaseModel):
    feedback: List[FeedbackItem]
    word_count: int
    numbered_text: str
    character_positions: List[Tuple[int, int]]  # List of (start_index, length) tuples


def number_words(text: str) -> tuple[str, int]:
    """
    Number each word in the text and return the numbered text and word count.
    """
    # Split text into words while preserving whitespace and punctuation
    words = re.findall(r"\S+|\s+", text)

    numbered_words = []
    word_count = 0

    for item in words:
        if re.match(r"\S+", item):  # If it's a word (not whitespace)
            word_count += 1
            numbered_words.append(f"[{word_count}]{item}")
        else:
            numbered_words.append(item)  # Preserve whitespace as-is

    numbered_text = "".join(numbered_words)
    return numbered_text, word_count


def convert_word_ranges_to_char_positions(
    text: str, feedback_items: List[FeedbackItem]
) -> List[Tuple[int, int]]:
    """
    Convert word ranges to character positions in the original text.
    Returns a list of tuples (start_index, length) for highlighting.
    """
    # Split text into words while preserving whitespace and punctuation
    words = re.findall(r"\S+|\s+", text)

    # Create a mapping from word number to character position and length
    word_to_char = {}
    char_pos = 0
    word_num = 0

    for item in words:
        if re.match(r"\S+", item):  # If it's a word (not whitespace)
            word_num += 1
            word_to_char[word_num] = (char_pos, len(item))
            char_pos += len(item)
        else:
            char_pos += len(item)  # Skip whitespace

    # Convert feedback word ranges to character positions
    char_positions = []

    for feedback in feedback_items:
        start_word = feedback.word_range.start
        end_word = feedback.word_range.end

        if start_word in word_to_char and end_word in word_to_char:
            start_char, start_length = word_to_char[start_word]

            if end_word == start_word:
                # Single word
                char_positions.append((start_char, start_length))
            else:
                # Multiple words - calculate from start of first word to end of last word
                end_char, end_length = word_to_char[end_word]
                total_length = (end_char + end_length) - start_char
                char_positions.append((start_char, total_length))

    return char_positions


async def get_chatgpt_feedback(
    numbered_text: str, word_count: int
) -> List[Dict[str, Any]]:
    """
    Send numbered text to ChatGPT and get structured feedback.
    """
    prompt = f"""
Please analyze the following text and provide feedback in JSON format. The text has numbered words like [1]word [2]another [3]word.

Text to analyze:
{numbered_text}

Please provide feedback as a JSON array where each feedback item has:
- "category": one of "Grammar", "Style", "Content", "Structure", "Clarity"
- "word_range": object with "start" and "end" numbers (referring to the word numbers in brackets)
- "comments": detailed feedback comment

Focus on providing as many meaningful feedback items as possible. Make sure word ranges are accurate based on the numbered words. Each piece of feedback should be non-overlapping.

Your feedback will go into highlighting certain parts of the text, so they should be small chunks of text. Don't give any highlights that span the entire thing.
Make your feedback extremely targetted. Sentences and words as highlights to consider changes to are much productive than entire paragraphs. If you think an entire paragraph
should be rewritten, it is okay to highlight the whole thing.

Overall, your highlights should not exceed 10% of the total text.

Example format:
[
  {{
    "category": "Grammar",
    "word_range": {{"start": 5, "end": 7}},
    "comments": "Consider revising this phrase for better clarity."
  }}
]

Return only the JSON array, no additional text.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful writing assistant that provides constructive feedback on text. Always respond with valid JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.7,
        )

        feedback_text = response.choices[0].message.content.strip()

        # Try to parse the JSON response
        import json

        try:
            feedback_data = json.loads(feedback_text)
            return feedback_data
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            json_match = re.search(r"\[.*\]", feedback_text, re.DOTALL)
            if json_match:
                feedback_data = json.loads(json_match.group())
                return feedback_data
            else:
                raise ValueError("Could not parse JSON from ChatGPT response")

    except Exception as e:
        print(f"Error getting ChatGPT feedback: {e}")
        # Return sample feedback if ChatGPT fails
        return [
            {
                "category": "Content",
                "word_range": {"start": 1, "end": min(5, word_count)},
                "comments": "Consider expanding on your main points for better clarity.",
            }
        ]


@app.post("/submit-draft")
async def submit_draft(request: DraftRequest):
    """
    Process a draft text submission and return character positions for highlighting.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Number the words in the text
        numbered_text, word_count = number_words(request.text)

        # Get feedback from ChatGPT
        feedback_data = await get_chatgpt_feedback(numbered_text, word_count)

        # Validate and structure the feedback
        feedback_items = []
        for item in feedback_data:
            try:
                feedback_item = FeedbackItem(
                    category=item.get("category", "General"),
                    word_range=WordRange(
                        start=item.get("word_range", {}).get("start", 1),
                        end=item.get("word_range", {}).get("end", 1),
                    ),
                    comments=item.get("comments", "No comment provided"),
                )

                # Validate word range
                if (
                    feedback_item.word_range.start <= word_count
                    and feedback_item.word_range.end <= word_count
                    and feedback_item.word_range.start <= feedback_item.word_range.end
                ):
                    feedback_items.append(feedback_item)

            except Exception as e:
                print(f"Error processing feedback item: {e}")
                continue

        # Convert word ranges to character positions
        char_positions = convert_word_ranges_to_char_positions(
            request.text, feedback_items
        )

        return char_positions

    except Exception as e:
        print(f"Error processing draft: {e}")
        raise HTTPException(status_code=500, detail="Error processing draft")


@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {"message": "Text Editor Feedback API is running"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "service": "Text Editor Feedback API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
