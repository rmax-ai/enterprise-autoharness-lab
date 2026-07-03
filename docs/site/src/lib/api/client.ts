const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type Environment = {
  id: string;
  name: string;
  description: string;
  action_count: number;
  rule_count: number;
  scenario_counts: {
    train: number;
    validation: number;
    test: number;
  };
  status: string;
};

export type PolicyRule = {
  rule_id: string;
  description: string;
  priority: number;
};

export type Scenario = {
  scenario_id: string;
  task: string;
  actor: {
    user_id: string;
    role: string;
    approval_limit?: number | null;
  };
  max_steps: number;
  tags: string[];
  expense_count: number;
  initial_state_preview: Record<string, unknown>;
  initial_state: Record<string, unknown>;
};

export type ExperimentMetrics = {
  task_success_rate: number;
  invalid_action_rate: number;
  policy_denial_rate?: number | null;
  runtime_error_rate?: number | null;
  false_rejection_rate?: number | null;
  false_acceptance_rate?: number | null;
  composite_score: number;
  total_actions: number;
};

export type Experiment = {
  experiment_id: string;
  environment: string;
  agent: string;
  timestamp: string;
  metrics: ExperimentMetrics;
};

export type ExperimentDetail = Experiment & {
  source_file: string;
};

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function fetchEnvironments(): Promise<{ environments: Environment[] }> {
  return request("/api/v1/environments");
}

export async function fetchPolicies(envId: string): Promise<{ environment: string; rules: PolicyRule[] }> {
  return request(`/api/v1/environments/${envId}/policies`);
}

export async function fetchScenarios(
  envId: string,
  split: string
): Promise<{ environment: string; split: string; count: number; scenarios: Scenario[] }> {
  return request(`/api/v1/scenarios/${envId}?split=${encodeURIComponent(split)}`);
}

export async function fetchExperiments(): Promise<{ experiments: Experiment[] }> {
  return request("/api/v1/experiments");
}

export async function fetchExperiment(id: string): Promise<ExperimentDetail> {
  return request(`/api/v1/experiments/${id}`);
}
