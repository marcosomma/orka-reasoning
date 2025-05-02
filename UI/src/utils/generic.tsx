import { AgentNode, AgentType } from "../types";

export const hasPrompt = (type: AgentType) => {
    return ["router", "failover", "join", "fork"].includes(type);
}
export const isNodeType = (type: AgentType) => {
    return ["router", "failover", "join", "fork"].includes(type);
}
export const isDataCollectorType = (type: AgentType) => {
    return ["duckduckgo"].includes(type);
}
export const isOpenAIType = (type: AgentType) => {
    return ["openai-binary", "openai-classification", "openai-answer"].includes(type);
}

export const findOriginalFork = (
    allAgents: AgentNode[],
    allLinks: { source: string; target: string }[],
    visited = new Set<string>(),
    agentId?: string,
    nodeId?: string
  ): string | null => {
    if (agentId && visited.has(agentId)) return null;
    if (nodeId && visited.has(nodeId)) return null;
    if(agentId) visited.add(agentId);
    if(nodeId) visited.add(nodeId);
  
    const node = agentId ? allAgents.find((a) => a.id === agentId) : allAgents.find((a) => a.id === nodeId);
    console.log("Finding original fork...", { agentId, nodeId, visited: Array.from(visited), node });
    if (!node) return null;
  
    if (node.type === "fork") return node.id;
    else {
      const incoming = allLinks.filter((l) => l.target === agentId).map((l) => l.source);
      for (const src of incoming) {
        const srcAgent = allAgents.find((a) => a.id === src)
        if (!srcAgent) continue;
        const isNode = isNodeType(srcAgent.type);
        const found = isNode 
            ? findOriginalFork(allAgents, allLinks, visited, undefined, src)
            : findOriginalFork(allAgents, allLinks, visited, src, undefined);
        if (found) return found;
      }
    }
  
    return null;
  }