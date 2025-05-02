export type AgentType =
  | "binary"
  | "classification"
  | "openai-binary"
  | "openai-classification"
  | "openai-answer"
  | "duckduckgo"
  | "router"
  | "failover"
  | "failing"
  | "fork"
  | "join";

export interface BaseAgent {
  id: string;
  type: AgentType;
  queue: string;
  prompt?: string;
}

// Extend specific agents
export interface OpenAIClassificationAgent extends BaseAgent {
  type: "openai-classification";
  options: string[];
}

export interface OpenAIBinaryAgent extends BaseAgent {
  type: "openai-binary";
}

export interface OpenAIAnswerAgent extends BaseAgent {
  type: "openai-answer";
}

export interface DuckDuckGoAgent extends BaseAgent {
  type: "duckduckgo";
}

export interface RouterAgent extends BaseAgent {
  type: "router";
  params: {
    decision_key: string;
    routing_map: Record<string, string | string[]>;  // Support multiple targets
    input_node?: string; // Added for failover
  };
}

// 🔥 New for failover
export interface FailoverAgent extends BaseAgent {
  type: "failover";
  children: string[];
}

// 🔥 New for join
export interface JoinForAgent extends BaseAgent {
  type: "join";
  group: string;
}

interface ForkAgent extends BaseAgent {
  type: "fork";
  targets: string[];
}

// Define general Agent union
export type Agent =
  | OpenAIClassificationAgent
  | OpenAIBinaryAgent
  | OpenAIAnswerAgent
  | DuckDuckGoAgent
  | RouterAgent
  | FailoverAgent
  | JoinForAgent
  | ForkAgent;

// Node UI representation (canvas)
export interface AgentNode extends BaseAgent {
  x: number;
  y: number;
  options?: string[];
  params?: {
    decision_key: string;
    routing_map: Record<string, string[]>;
    input_node?: string; // Added for failover
  };
  children?: string[];   // Added for failover nodes
  group?: string;        // Added for join nodes
  targets?: string[];    // Added for fork nodes
}
