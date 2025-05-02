import { AgentType } from "../../types";

export const colorsByType: Record<string, string> = {
  router: "#0082ADFF", // Logical blue (logic)
  failover: "#006EFFFF", // Logical blue (logic)
  join: "#510CF1FF", // Logical blue (logic)
  fork: "#043B3DFF", // Logical blue (logic)
  duckduckgo: "#FFD700", // DataCollector Yellow
  "openai-answer": "#7FFF00",
  "openai-binary": "#FF69B4",
  "openai-classification": "#9370DB",
};

export const logicTypes: AgentType[] = ["router", "failover", "fork", "join"];

export const agentTypes: AgentType[] = [
    "openai-binary",
    "openai-classification",
    "openai-answer"
];

export const dataCollectorTypes: AgentType[] = [
    "duckduckgo"
];

export const descriptionsByType: Record<string, string> = {
    router: "Routes input to different agents based on a decision key.",
    failover: "Retries fallback agents if the main one fails.",
    join: "COMING SOON! > Waits for multiple inputs to complete before continuing.",
    fork: "COMING SOON! > Split signal to multiple parallel inputs.",
    "openai-binary": "Uses OpenAI to answer true/false binary questions.",
    "openai-classification": "Uses OpenAI to classify input into categories.",
    "openai-answer": "Uses OpenAI to generate a direct answer.",
    duckduckgo: "Collects data by searching DuckDuckGo search engine.",
  };
  