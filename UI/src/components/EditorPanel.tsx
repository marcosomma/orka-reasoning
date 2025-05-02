import React from "react";
import { Agent, AgentNode } from "../types";
import { findOriginalFork, hasPrompt, isNodeType } from "../utils/generic";
import { FailoverChildrenEditor } from "./editorPanel/FailoverChildrenEditor";
import { JoinInputsEditor } from "./editorPanel/JoinInputsEditor";
import { ForkInputsEditor } from "./editorPanel/ForkInputsEditor";


interface EditorPanelProps {
  selectedAgent: Agent | null;
  onChange: (updated: Agent) => void;
  allAgents: AgentNode[];
  allLinks: { source: string; target: string }[];
}

const EditorPanel: React.FC<EditorPanelProps> = ({
  selectedAgent,
  onChange,
  allAgents,
  allLinks,
}) => {
  if (!selectedAgent) return null;

  const handleInputChange = (field: keyof Agent, value: any) => {
    onChange({ ...selectedAgent, [field]: value } as Agent);
  };

  return (
    <div className="settings-panel">
      <h3>{selectedAgent.id}</h3>

      <label>ID</label>
      <input
        type="text"
        value={selectedAgent.id}
        disabled
        style={{ width: "80%" }}
      />

      <label>Type</label>
      <input
        type="text"
        value={selectedAgent.type}
        disabled
        style={{ width: "80%" }}
      />

      {selectedAgent.type === "failover" && (() => {
        const newChildren = allLinks
          .filter((link) => link.target === selectedAgent.id)
          .map((link) => link.source);


        if (JSON.stringify(selectedAgent.children || []) !== JSON.stringify(newChildren)) {
          onChange({
            ...selectedAgent,
            children: newChildren,
          });
        }

        const handleFailoverEditorChange = (updated: Agent) => {
          console.log("Failover editor change", updated);
          onChange(updated);
        };

        return (
          <FailoverChildrenEditor
            agent={selectedAgent}
            allLinks={allLinks}
            onChange={handleFailoverEditorChange}
          />
        );
      })()}

      {selectedAgent.type === "fork" && (() => {
        const targets = allLinks
          .filter((link) => link.source === selectedAgent.id)
          .map((link) => link.target);


        if (JSON.stringify(selectedAgent.targets || []) !== JSON.stringify(targets)) {
          onChange({
            ...selectedAgent,
            targets,
          });
        }

        return (
          <ForkInputsEditor
            agent={selectedAgent}
            targetIds={targets}
          />
        );
      })()}

      {selectedAgent.type === "join" && (() => {
        const incomingSignals = allLinks
          .filter((link) => link.target === selectedAgent.id)
          .map((link) => link.source);
        console.log("Incoming signals for join:", incomingSignals);

        const originForks = incomingSignals
          .map((src) => {
            const srcAgent = allAgents.find((a) => a.id === src);
            console.log("Source agent for join:", srcAgent);
            if (!srcAgent) return null;
            const isNode = isNodeType(srcAgent.type);
            if (isNode) return findOriginalFork(allAgents, allLinks, new Set(), undefined, src);
            else return findOriginalFork(allAgents, allLinks, new Set(), src);
          })
          .filter((id): id is string => !!id);
        console.log("Origin forks for join:", originForks);

        const uniqueForks = Array.from(new Set(originForks));
        console.log("Unique forks for join:", uniqueForks);

        const groupId = uniqueForks.length === 1 ? uniqueForks[0] : null;
        if (!groupId) console.warn("Join node is fed by inconsistent or missing fork groups.");
        if (selectedAgent.group !== groupId) {
          onChange({
            ...selectedAgent,
            group: groupId as string,
          });
        }

        return (
          <JoinInputsEditor
            agent={selectedAgent}
            group={groupId || ""}
          />
        );
      })()}

      {!hasPrompt(selectedAgent?.type) && (
        <>
          <label>Prompt</label>
          <textarea
            value={selectedAgent.prompt || ""}
            onChange={(e) => handleInputChange("prompt", e.target.value)}
            style={{ width: "80%" }}
          />
        </>
      )}

      {selectedAgent.type === "openai-classification" && (
        <>
          <label>Options (IMPORTANT! Use lower case! otherwise there is no match)</label>
          <textarea
            value={selectedAgent.options.join(", ")}
            onChange={(e) =>
              onChange({
                ...selectedAgent,
                options: e.target.value.split(",").map((o) => o.trim()),
              })
            }
            style={{ width: "80%" }}
          />
        </>
      )}

      {selectedAgent.type === "router" && (
        <>
          <label>Decision Key</label>
          <select
            value={selectedAgent.params.decision_key}
            onChange={(e) =>
              onChange({
                ...selectedAgent,
                params: {
                  ...selectedAgent.params,
                  decision_key: e.target.value,
                },
              })
            }
            style={{ width: "80%" }}
          >
            <option value="">-- Select Agent --</option>
            {allAgents
              .filter(
                (a) => a.id !== selectedAgent.id && a.type === "openai-binary"
              )
              .map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.id}
                </option>
              ))}
          </select>

          {(() => {
            const routerId = selectedAgent.id;
            const routingMap = selectedAgent.params.routing_map || {};

            // Get actual linked targets from graph
            const linkedTargets = allLinks
              .filter((link) => link.source === routerId)
              .map((link) => link.target);

            // Already selected targets (true/false)
            const usedTargets = new Set<string>();
            if (routingMap.true) usedTargets.add(routingMap.true as string);
            if (routingMap.false) usedTargets.add(routingMap.false as string);

            // Helper: avoid duplicate selection, except for current one
            const getAvailableOptions = (key: "true" | "false") =>
              linkedTargets.filter(
                (id) => ![...usedTargets].includes(id) || routingMap[key] === id
              );

            return (
              <>
                <label>Routing Map – True</label>
                <select
                  value={routingMap.true || ""}
                  onChange={(e) =>
                    onChange({
                      ...selectedAgent,
                      params: {
                        ...selectedAgent.params,
                        routing_map: {
                          ...routingMap,
                          true: e.target.value,
                        },
                      },
                    })
                  }
                  style={{ width: "80%" }}
                >
                  <option value="">-- Select Agent --</option>
                  {getAvailableOptions("true").map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                </select>

                <label>Routing Map – False</label>
                <select
                  value={routingMap.false || ""}
                  onChange={(e) =>
                    onChange({
                      ...selectedAgent,
                      params: {
                        ...selectedAgent.params,
                        routing_map: {
                          ...routingMap,
                          false: e.target.value,
                        },
                      },
                    })
                  }
                  style={{ width: "80%" }}
                >
                  <option value="">-- Select Agent --</option>
                  {getAvailableOptions("false").map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                </select>
              </>
            );
          })()}
        </>
      )}
    </div>
  );
};

export default EditorPanel;
