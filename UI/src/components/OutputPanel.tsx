import React, { useState } from 'react';

interface Props {
  output: string;
}

const OutputPanel: React.FC<Props> = ({ output }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(output).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleClear = () => {
    const event = new CustomEvent('clear-output');
    window.dispatchEvent(event);
  };

  return (
    <div className="output-panel" style={{ position: "relative" }}>
      <textarea value={output} readOnly placeholder="Response will appear here..." />
      <button onClick={handleCopy} style={{
        position: "absolute",
        top: "15px",
        right: "60px",
        padding: "6px 10px",
        fontSize: "0.8rem",
        background: output?"#444" : "#eee",
        color: "#fff",
        border: "1px solid #888",
        borderRadius: "4px",
        cursor: output? "pointer": "not-allowed",
      }}
        disabled={!output}
      >{copied ? 'Copied!' : 'Copy'}</button>
      <button onClick={handleClear} style={{
        position: "absolute",
        top: "15px",
        right: "0px",
        padding: "6px 10px",
        fontSize: "0.8rem",
        background: output?"#444" : "#eee",
        color: "#fff",
        border: "1px solid #888",
        borderRadius: "4px",
        cursor: output? "pointer": "not-allowed",
      }}
        disabled={!output}>Clear</button>
    </div>
  );
};

export default OutputPanel;
