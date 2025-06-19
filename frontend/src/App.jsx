import React, { useRef, useState, useEffect } from 'react';
import Editor from './Editor';
import Quill from 'quill'

const Delta = Quill.import('delta');

const FEEDBACK_URL = 'http://0.0.0.0:8000/submit-draft';

const App = () => {
    const [range, setRange] = useState();
    const [lastChange, setLastChange] = useState();
    const [readOnly, setReadOnly] = useState(false);

    // Use a ref to access the quill instance directly
    const quillRef = useRef();

    // Handle text submission from editor
    const handleTextSubmit = async (text) => {
        console.log('Text submitted from editor:', text);

        try {
            const response = await fetch(FEEDBACK_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text }),
            });

            const result = await response.json();
            console.log('Feedback API response:', result);

            // Apply highlights based on API response
            if (quillRef.current && result && Array.isArray(result)) {
                const quill = quillRef.current;

                // Remove all existing highlights first
                const text = quill.getText();
                quill.formatText(0, text.length, 'highlight', false);

                // Apply new highlights based on tuples (start, length)
                result.forEach(([start, length]) => {
                    if (typeof start === 'number' && typeof length === 'number' && length > 0) {
                        quill.formatText(start, length, 'highlight', true);
                    }
                });
            }
        } catch (error) {
            console.error('Error calling feedback API:', error);
        }
    };

    return (
        <div>
            <Editor
                ref={quillRef}
                readOnly={readOnly}
                onSubmit={handleTextSubmit}
                defaultValue={new Delta()
                    .insert('Hello')
                    .insert('\n', { header: 1 })
                    .insert('Some ')
                    .insert('initial', { bold: true })
                    .insert(' ')
                    .insert('highlighted text', { highlight: true })  // This will be highlighted
                    .insert(' and ')
                    .insert('content', { underline: true })
                    .insert('\n')
                }
                onSelectionChange={setRange}
                onTextChange={setLastChange}
            />
            {/* <div className="state">
                <div className="state-title">Current Range:</div>
                {range ? JSON.stringify(range) : 'Empty'}
            </div>
            <div className="state">
                <div className="state-title">Last Change:</div>
                {lastChange ? JSON.stringify(lastChange.ops) : 'Empty'}
            </div> */}
        </div>
    );
};

export default App;