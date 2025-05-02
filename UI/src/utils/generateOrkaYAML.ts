import { AgentNode } from "../types";
import yaml from "js-yaml";

function generateTopologicalOrder(
  agents: AgentNode[],
  links: { source: string; target: string }[]
): string[] {
  const graph = new Map<string, Set<string>>();
  const inDegree = new Map<string, number>();

  agents.forEach(({ id }) => {
    graph.set(id, new Set());
    inDegree.set(id, 0);
  });

  links.forEach(({ source, target }) => {
    graph.get(source)?.add(target);
    inDegree.set(target, (inDegree.get(target) || 0) + 1);
  });

  const queue: string[] = [];
  inDegree.forEach((deg, node) => {
    if (deg === 0) queue.push(node);
  });

  const ordered: string[] = [];
  while (queue.length > 0) {
    const node = queue.shift()!;
    ordered.push(node);
    graph.get(node)?.forEach((neighbor) => {
      inDegree.set(neighbor, (inDegree.get(neighbor) || 1) - 1);
      if (inDegree.get(neighbor) === 0) queue.push(neighbor);
    });
  }

  return ordered;
}

function collectBranchPath(
  startId: string,
  links: { source: string; target: string }[],
  visited = new Set<string>(),
  usedInSpecialNodes: Set<string>
): string[] {
  const path: string[] = [];
  let current = startId;
  while (current && !visited.has(current)) {
    visited.add(current);
    path.push(current);
    const nextLink = links.find((link) => link.source === current);
    if (!nextLink) break;
    if (nextLink.target.indexOf("join") === -1) {
      usedInSpecialNodes.add(nextLink.target);
    }
    current = nextLink.target;
  }
  console.log({
    startId,
    path,
    visited,
    links,
  })
  return path;
}

// Helper to find direct children nodes
const findChildren = (id: string, links: { source: string; target: string }[]) =>
  links.filter(link => link.source === id).map(link => link.target);

// Trace branches from Fork to Join, explicitly excluding Fork from the path
function collectForkBranches(
  forkId: string,
  links: { source: string; target: string }[],
  agents: AgentNode[],
  usedNodes: Set<string>
): { branches: string[][], joinedBy: string | null } {
  const joinNodes = new Set(agents.filter(a => a.type === "join").map(a => a.id));
  const joinMapping: Record<string, string> = {};

  const traceBranch = (current: string, path: string[]): string[] => {
    if (current.indexOf("join") === -1) usedNodes.add(current);
    else return [...path];
    if (joinNodes.has(current)) {
      joinMapping[current] = forkId;
      return [...path, current];
    }

    const next = findChildren(current, links);
    if (next.length === 0) return [...path, current];
    if (next.length > 1) throw new Error(`Branching inside fork path detected at node ${current}`);

    return traceBranch(next[0], [...path, current]);
  };

  const branches = findChildren(forkId, links).map(child => traceBranch(child, []));
  return { branches, joinedBy: Object.keys(joinMapping)[0] || null };
}


// Collect failover children explicitly
function buildFailoverChildren(
  failoverAgent: AgentNode,
  agents: AgentNode[]
) {
  const input = failoverAgent.params?.input_node;
  console.log("Building failover children...", { input, failoverAgent });
  return (failoverAgent.children || []).map(childId => {
    const child = agents.find(a => {
      return a?.id !== input && a?.id === childId
    });
    if (!child) return;

    const base: any = { id: child.id, type: child.type, queue: child.queue };
    if (child.prompt) base.prompt = child.prompt;
    if (child.options) base.options = child.options;
    if (child.params) base.params = child.params;

    return base;
  });
}

export const generateOrkaYAML = (
  agents: AgentNode[],
  links: { source: string; target: string, depends_on?: string }[],
  orchestratorId: string = "orka-ui",
  orchestratorQueue: string = "orka:generated"
): string => {
  console.log("Generating YAML...", { agents, links, orchestratorId, orchestratorQueue });
  // Validation
  const missing = agents.filter((agent) => {
    if (!agent.id || !agent.type || !agent.queue) return true;

    switch (agent.type) {
      case "openai-classification":
        return !agent.options?.length;
      case "router":
        return !agent.params?.decision_key || !agent.params?.routing_map;
      case "fork":
        return !findChildren(agent.id, links).length;
      case "failover":
        return !agent.params?.input_node || !agent.children?.length;
      case "join":
        return !agent.group && !Object.values(joinGroupMap).includes(agent.id);
      default:
        return false;
    }
  });

  if (missing.length > 0) {
    throw new Error(`Missing required fields in ${missing.length} agent(s)`);
  }

  const usedInSpecialNodes = new Set<string>();
  const usedInFailOver = new Set<string>();
  const joinGroupMap: Record<string, string> = {};
  const joinNodes: any[] = [];
  const orderedIds = generateTopologicalOrder(agents, links);
  const dependsMap: Record<string, string[]> = {};

  links.forEach(link => {
    if (link.depends_on) {
      if (!dependsMap[link.target]) dependsMap[link.target] = [];
      dependsMap[link.target].push(link.source);
    }
  });
  console.log("Depends map:", dependsMap);

  let agentBlocks: any[] = [];

  agents.forEach(agent => {
    const base: any = { id: agent.id, type: agent.type, queue: agent.queue };

    if (agent.type === "fork") {
      const { branches, joinedBy } = collectForkBranches(agent.id, links, agents, usedInSpecialNodes);
      if (joinedBy) joinGroupMap[joinedBy] = agent.id;
      branches.flat().forEach(id => {
        if (id.indexOf("join") === -1) {
          usedInSpecialNodes.add(id);
        }
        console.log("Used in special nodes:", usedInSpecialNodes);
      });
      base.targets = branches;
      delete base.queue; // Forks don't have a queue
    }

    else if (agent.type === "failover") {
      const children = buildFailoverChildren(agent, agents);
      base.input = agent.params?.input_node;
      children.filter(child => child && child.id).forEach(child => {
        console.log("Adding to usedInFailOver:", child.id);
        usedInSpecialNodes.add(child.id);
        usedInFailOver.add(child.id);
      });
      base.children = children.filter(child => child && child.id);
      delete base.queue; // failover don't have a queue
    }

    else if (agent.type === "router" && agent.params?.routing_map) {
      const routingMap = agent.params.routing_map;
      const parsedRoutingMap: Record<string, string[]> = {};

      for (const [key, targets] of Object.entries(routingMap)) {
        const targetList = Array.isArray(targets) ? targets : [targets];
        parsedRoutingMap[key] = targetList.flatMap(targetId =>
          collectBranchPath(targetId, links, new Set(), usedInSpecialNodes)
        );
        targetList.forEach(id => usedInSpecialNodes.add(id));
      }

      base.params = {
        decision_key: agent.params.decision_key,
        routing_map: parsedRoutingMap,
      };
      delete base.queue;
    }

    else if (agent.type === "join") {
      base.group = joinGroupMap[agent.id] || agent.group || "";
      joinNodes.push(base);
      delete base.queue; // join don't have a queue
      return; // defer adding to agentBlocks
    }

    if (agent.prompt) base.prompt = agent.prompt;
    if (agent.options) base.options = agent.options;
    if (dependsMap[agent.id]) base.depends_on = dependsMap[agent.id];

    agentBlocks.push(base);
  });

  // Append join nodes at the end to preserve topological order
  joinNodes.forEach(joinNode => {
    const groupId = joinNode.group;
    const groupIndex = agentBlocks.findIndex(agent => agent.id === groupId);
    if (groupIndex !== -1) {
      agentBlocks.splice(groupIndex + 1, 0, joinNode);
    } else {
      agentBlocks.push(joinNode); // If no group is found, place it at the end
    }
  });

  console.log("Agent blocks:", agentBlocks);
  console.log("Used in special nodes:", Array.from(usedInSpecialNodes));
  // Filter out nodes used in fork/failover from root orchestrator list
  const rootAgents = agentBlocks
    .map(a => a.id)
    .filter(id => !usedInSpecialNodes.has(id))
    .sort((a, b) => orderedIds.indexOf(a) - orderedIds.indexOf(b));


  const orchestrator = {
    id: orchestratorId,
    strategy: agents.some(a => a.type === "fork") ? "parallel" : agents.some(a => a.type === "router") ? "decision-tree" : "sequential",
    queue: orchestratorQueue,
    agents: rootAgents,
  };

  const finalYAML = {
    orchestrator,
    agents: agentBlocks.filter(agent => !usedInFailOver.has(agent.id)).sort((a, b) => orderedIds.indexOf(a.id) - orderedIds.indexOf(b.id)),
  };

  const dumpResult = yaml.dump(finalYAML, {
    noRefs: true,
    lineWidth: -1,
    forceQuotes: false,
    quotingType: '"',
  });
  console.log("YAML finalYAML:", finalYAML);
  console.log("Generated YAML dumpResult:", dumpResult);

  return dumpResult;
};