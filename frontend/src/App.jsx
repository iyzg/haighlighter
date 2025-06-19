import React, { useRef, useState } from 'react';
import Editor from './Editor';
import Quill from 'quill'

const Delta = Quill.import('delta');

const API_BASE_URL = 'TODOCHANGE';

const App = () => {
    const [range, setRange] = useState();
    const [lastChange, setLastChange] = useState();
    const [readOnly, setReadOnly] = useState(false);

    // Use a ref to access the quill instance directly
    const quillRef = useRef();

    return (
        <div>
            <Editor
                ref={quillRef}
                readOnly={readOnly}
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
            <div className="state">
                <div className="state-title">Current Range:</div>
                {range ? JSON.stringify(range) : 'Empty'}
            </div>
            <div className="state">
                <div className="state-title">Last Change:</div>
                {lastChange ? JSON.stringify(lastChange.ops) : 'Empty'}
            </div>
        </div>
    );
};

export default App;