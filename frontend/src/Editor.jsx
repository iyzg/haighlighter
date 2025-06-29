import React, { forwardRef, useEffect, useLayoutEffect, useRef } from 'react';
import Quill from 'quill';

const Inline = Quill.import('blots/inline');

class HighlightBlot extends Inline {
    static blotName = 'highlight';
    static tagName = 'span';
    static className = 'ql-highlight';

    static create(value) {
        const node = super.create();
        node.setAttribute('data-highlight', value || 'true');
        return node;
    }

    static formats(node) {
        return node.getAttribute('data-highlight');
    }
}

Quill.register(HighlightBlot);

// Editor is an uncontrolled React component
const Editor = forwardRef(
    ({ readOnly, defaultValue, onTextChange, onSelectionChange, onSubmit }, ref) => {
        const containerRef = useRef(null);
        const defaultValueRef = useRef(defaultValue);
        const onTextChangeRef = useRef(onTextChange);
        const onSelectionChangeRef = useRef(onSelectionChange);
        const onSubmitRef = useRef(onSubmit);

        useLayoutEffect(() => {
            onTextChangeRef.current = onTextChange;
            onSelectionChangeRef.current = onSelectionChange;
            onSubmitRef.current = onSubmit;
        });

        useEffect(() => {
            ref.current?.enable(!readOnly);
        }, [ref, readOnly]);

        useEffect(() => {
            const container = containerRef.current;
            const editorContainer = container.appendChild(
                container.ownerDocument.createElement('div'),
            );

            // Create the Quill instance first
            const quill = new Quill(editorContainer, {
                theme: 'snow',
                modules: { toolbar: false }
            });

            ref.current = quill;

            // Now add the click event listener (quill is in scope)
            editorContainer.addEventListener('click', (e) => {
                if (e.target.classList.contains('ql-highlight')) {
                    // Get the position of the clicked highlight
                    const range = quill.getSelection();
                    if (range) {
                        // Find the bounds of the highlight
                        const [leaf] = quill.getLeaf(range.index);
                        const leafIndex = quill.getIndex(leaf);
                        const leafLength = leaf.text.length;

                        // Remove the highlight format
                        quill.formatText(leafIndex, leafLength, 'highlight', false);
                    }
                }
            });


            editorContainer.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    console.log('Ctrl+Enter pressed via event listener!');
                    const text = quill.getText();
                    if (onSubmitRef.current) {
                        onSubmitRef.current(text);
                    } else {
                        console.log('onSubmitRef.current is not available');
                    }
                }
            });

            if (defaultValueRef.current) {
                quill.setContents(defaultValueRef.current);
            }

            quill.on(Quill.events.TEXT_CHANGE, (...args) => {
                onTextChangeRef.current?.(...args);
            });

            quill.on(Quill.events.SELECTION_CHANGE, (...args) => {
                onSelectionChangeRef.current?.(...args);
            });

            return () => {
                ref.current = null;
                container.innerHTML = '';
            };
        }, [ref]);

        return <div ref={containerRef}></div>;
    },
);

Editor.displayName = 'Editor';

export default Editor;