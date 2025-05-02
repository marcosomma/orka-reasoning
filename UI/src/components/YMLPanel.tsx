import React from "react";
import { useDispatch } from "react-redux";
import { showNotification } from "../redux/notificationSlice";

interface Props {
  yml: string;
}

const YMLPanel: React.FC<Props> = ({ yml }) => {
  const dispatch = useDispatch();
  const handleCopy = () => {
    navigator.clipboard.writeText(yml).then(() => {
          dispatch(showNotification("YAML generated — check console."));
    });
  };

  return (
    <div className="yml-panel" style={{ position: "relative" }}>
      <textarea value={yml} readOnly placeholder="YML will appear here..." />
      <button
        onClick={handleCopy}
        style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          padding: "6px 10px",
          fontSize: "0.8rem",
          background: yml?"#444" : "#eee",
          color: "#fff",
          border: "1px solid #888",
          borderRadius: "4px",
          cursor: yml? "pointer": "not-allowed",
        }}
      >
        Copy
      </button>
    </div>
  );
};

export default YMLPanel;
