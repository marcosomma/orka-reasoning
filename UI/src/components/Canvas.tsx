import React, { useState, useRef } from "react";
import EditorPanel from "./EditorPanel";
import CanvasSVG from "./canvas/CanvasSVG";
import { AgentNode, AgentType } from "../types";
import { colorsByType, logicTypes, agentTypes, dataCollectorTypes, descriptionsByType } from "./canvas/contants";

interface CanvasProps {
  agents: AgentNode[];
  setAgents: React.Dispatch<React.SetStateAction<AgentNode[]>>;
  links: { source: string; target: string }[];
  setLinks: React.Dispatch<React.SetStateAction<{ source: string; target: string }[]>>;
}

const Canvas: React.FC<CanvasProps> = ({
  agents,
  setAgents,
  links,
  setLinks,
}) => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const selectedLinkRef = useRef<{ source: string; target: string } | null>(null);

  const addAgent = (type: AgentType) => {
    const id = `${type}_${agents.length}`;
    const newNode: AgentNode = {
      id,
      type,
      x: 100 + Math.random() * 400,
      y: 100 + Math.random() * 300,
      queue: `orka:${id}`,
      options: type === "openai-classification" ? ["opt1", "opt2"] : undefined,
      params: type === "router" ? { decision_key: "decision", routing_map: {} } : undefined,
      children: type === "failover" ? [] : undefined,
      group: type === "join" ? '' : undefined,
      targets: type === "fork" ? [] : undefined,
      prompt: ["router", "failover", "join"].includes(type) ? undefined : "",
    };
    setAgents([...agents, newNode]);
  };

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <div className="editor">
        <h4 style={{
          backgroundColor: "#333",
          lineHeight: "20px",
          border: "1px solid",
          borderRight: 'none',
          borderLeft: 'none',
          padding: "10px",
          margin: "-10px -10px 10px -10px",
          textAlign: "center",
        }}>
          Logic Nodes
        </h4>
        {logicTypes.map((type) => (
          <button
            key={type}
            title={descriptionsByType[type]} 
            onClick={() => addAgent(type)}
            style={{
              marginBottom: "10px",
              width: "100%",
              backgroundColor: colorsByType[type],
              minHeight: "35px",
              borderRadius: "20px",
              border: "1px solid #fff",
            }}
            // disabled={type === "join" || type === "fork" }
          >
            {type}
          </button>
        ))}
        <h4 style={{
          backgroundColor: "#333",
          lineHeight: "20px",
          border: "1px solid",
          borderRight: 'none',
          borderLeft: 'none',
          padding: "10px",
          margin: "10px -10px 10px -10px",
          textAlign: "center",
        }}>
          Intelligent Agent
        </h4>
        {agentTypes.map((type) => (
          <button
            key={type}
            title={descriptionsByType[type]} 
            onClick={() => addAgent(type)}
            style={{
              marginBottom: "10px",
              width: "100%",
              backgroundColor: colorsByType[type],
              minHeight: "35px",
              borderRadius: "20px",
              border: "1px solid #fff",
            }}
          >
            {type}
          </button>
        ))}
        <h4 style={{
          backgroundColor: "#333",
          lineHeight: "20px",
          border: "1px solid",
          borderRight: 'none',
          borderLeft: 'none',
          padding: "10px",
          margin: "10px -10px 10px -10px",
          textAlign: "center",
        }}>
          Data Collectors
        </h4>
        {dataCollectorTypes.map((type) => (
          <button
            key={type}
            title={descriptionsByType[type]} 
            onClick={() => addAgent(type)}
            style={{
              marginBottom: "10px",
              width: "100%",
              backgroundColor: colorsByType[type],
              minHeight: "35px",
              borderRadius: "20px",
              border: "1px solid #fff",
            }}
          >
            {type}
          </button>
        ))}
      </div>
      <EditorPanel
        // @ts-ignore
        selectedAgent={agents.find((node) => node.id === selectedNode) || null}
        onChange={(updatedAgent) => {
          // @ts-ignore
          setAgents(
            // @ts-ignore
            agents.map((node) =>
              node.id === updatedAgent.id ? updatedAgent : node
            )
          );
        }}
        allAgents={agents}
        allLinks={links}
      />
      <CanvasSVG
        agents={agents}
        setAgents={setAgents}
        links={links}
        setLinks={setLinks}
        selectedNode={selectedNode}
        setSelectedNode={setSelectedNode}
        selectedLinkRef={selectedLinkRef}
      />
    </div>
  );
};

export default Canvas;
