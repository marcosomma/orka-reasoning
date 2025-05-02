import { useState, useEffect } from "react";
import { Agent } from "../../types";

interface FailoverChildrenEditorProps {
  agent: Agent;
  allLinks: { source: string; target: string }[];
  onChange: (updated: Agent) => void;
}

export function FailoverChildrenEditor({ agent, allLinks, onChange }: FailoverChildrenEditorProps) {
  const incomingChildren = allLinks
    .filter((link) => link.target === agent.id)
    .map((link) => link.source);

  const [inputNode, setInputNode] = useState<string>("");

  useEffect(() => {
    if (!inputNode && incomingChildren.length > 0) {
      setInputNode(incomingChildren[0]);
    }
  }, [incomingChildren, inputNode]);

  const handleInputChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = e.target.value;
    setInputNode(selected);
    const newChildren = incomingChildren.filter((child) => child !== selected);
    onChange({
      ...agent,
      // @ts-ignore
      params: {
        // @ts-ignore
        ...agent.params,
        input_node: selected,
      },
      children: newChildren,
    });
  };

  const remainingChildren = incomingChildren.filter((child) => child !== inputNode);

  return (
    <div className="p-2 border rounded">
      <h3 className="font-bold mb-2" style={{ marginTop: 30 }}>Failover Input Node</h3>
      <select value={inputNode} onChange={handleInputChange} className="border p-1 rounded w-40 bg-gray-900 text-gray-100">
        <option value="">-- Select Input Node --</option>
        {incomingChildren.map((childId) => (
          <option key={childId} value={childId}>{childId}</option>
        ))}
      </select>

      <h3 className="font-bold mb-2" style={{ marginTop: 30 }}>Failover Children</h3>

      {remainingChildren.length === 0 ? (
        <p className="text-gray-500 italic">No linked fallback agents yet.</p>
      ) : (
        remainingChildren.map((childId) => (
          <input
            key={childId}
            type="text"
            value={childId}
            disabled
            className="border p-1 rounded w-40 bg-gray-900 text-gray-100"
            style={{ width: "80%", marginTop: 10 }}
          />
        ))
      )}
    </div>
  );
}
