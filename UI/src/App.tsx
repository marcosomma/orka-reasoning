import React, { useState } from "react";
import { useDispatch } from "react-redux";
import Canvas from "./components/Canvas";
import InputPanel from "./components/InputPanel";
import OutputPanel from "./components/OutputPanel";
import { AgentNode } from "./types";
import { generateOrkaYAML } from "./utils/generateOrkaYAML";
import "./styles.css";
import YMLPanel from "./components/YMLPanel";
import Notification from "./components/Notification";
import { showNotification } from "./redux/notificationSlice";

const App: React.FC = () => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [generatedYAML, setGeneratedYAML] = useState("");
  const [agents, setAgents] = useState<AgentNode[]>([]);
  const [links, setLinks] = useState<{ source: string; target: string }[]>([]);

  const handleGenerate = async () => {
    try {
      const yml = await generateOrkaYAML(agents, links);
      console.log(yml);
      setGeneratedYAML(yml);
      dispatch(showNotification("YAML generated — check console."));
    } catch (err) {
      alert(`Error: ${(err as Error).message}`);
    }
  };

  const handleTestLocal = async () => {
    try {
      setLoading(true); // Start loading
      console.log("Testing local API with input:", generatedYAML);
      const request = {
        input,
        yaml_config: generatedYAML,
      };

      console.log("Request to local API:", request);
      const response = await fetch(
        "http://localhost:8000/api/run",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error("API Error:", errorText);
        alert(`Error: ${errorText}`);
        return;
      }

      const result = await response.json();

      if (result.execution_log && Array.isArray(result.execution_log)) {
        const readable = result.execution_log
          .map(
            (log: any) =>
              `[${log.agent_id}] (${log.event_type}) ${
                log.payload.result || JSON.stringify(log.payload)
              }`
          )
          .join("\n\n");

        setOutput(readable);
      } else {
        setOutput("No execution log returned.");
      }
    } catch (err) {
      console.error("Fetch failed:", err);
      alert("Failed to reach OrKa API. Is it running?");
    } finally {
      setLoading(false); // End loading
    }
  };

  return (
    <div className="app">
      {loading && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            color: "white",
            fontSize: "1.5rem",
            fontWeight: "bold",
          }}
        >
          ⏳ Running OrKa pipeline...
        </div>
      )}
      <header className="header">
        <img src="/logo.png" alt="OrKa logo" className="logo" />
        <h1>(localhost) Orchestrator Kit Agents</h1>
        <img src="/logo.png" alt="OrKa logo" className="logo" />
      </header>
      <Canvas
        agents={agents}
        setAgents={setAgents}
        links={links}
        setLinks={setLinks}
      />
      <footer className="footer">
        <div style={{ flex: "1", overflow: "hidden" }}>
          <YMLPanel yml={generatedYAML} />
        </div>
        <div
          style={{
            display: "flex",
            gap: "12px",
            flexDirection: "column",
            backgroundColor: "#333",
            padding: "10px",
            borderRadius: "5px",
            maxWidth: "150px",
          }}
        >
          <button style={{ height: "40px" }} onClick={handleGenerate}>
            Generate YML
          </button>
          <button style={{ height: "40px" }} onClick={handleTestLocal} disabled={true}>
            Test Local
          </button>
          <button style={{ height: "40px" }} onClick={handleTestLocal} disabled={input.length === 0}>
            Test API
          </button>
        </div>
        <div
          className="input-wrapper"
          style={{ flex: "1", overflow: "hidden" }}
        >
          <OutputPanel output={output} />
          <InputPanel input={input} setInput={setInput} />
        </div>
      </footer>
      <Notification />
    </div>
  );
};

export default App;
