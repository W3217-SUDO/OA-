export type AgentCapability = {
  name: string;
  label: string;
  description: string;
  read_only: boolean;
};

export type AgentRun = {
  id: string;
  status: string;
  skill: string;
  input: string;
  output: string;
  created_at: string;
  read_only: boolean;
};

