export type Settings = {
  aider_python: string; web_search: boolean; debug_logging: boolean; sandbox: boolean; sandbox_network: string;
  sandbox_memory: string; sandbox_cpus: number; sandbox_pids: number; sandbox_ports: string; research_domains: string;
  python: string; base: string; model: string; context_tokens: number; output_tokens: number; temperature: number;
  top_p: number; edit: string; budget: number; timeout: number; allow_pip: boolean; allow_choco: boolean;
  allow_npm: boolean; simulation: boolean; provider: string; opencode_fallback: boolean; opencode_order: string[];
  small_model_mode: boolean; source_mode: string; preference: string; local_model: string; free_model: string;
  api_model: string; api_base: string; api_key?: string; remote_api_key?: string;
};

export type Task = { id: string; title: string; instruction: string; acceptance: string[]; files: string[]; depends_on: string[]; priority?: number };

export type State = {
  blocked_tasks?: { id: string; dependencies: string[]; file_conflicts: string[]; approval_missing?: string[] }[];
  status: string; message: string; runs: number; session_used: number; current: string | null; plan_file?: string;
  plan: { version: number; goal: string; tasks: Task[]; acceptance_scenarios?: Record<string, unknown>[]; replanning?: { version: number; reason: string; task: string; children: string[] }[] };
  tasks: Record<string, { status: string; attempts: number; error: string; question: string | null; question_id?: string; ever_verified?: boolean; invalidation_reason?: string }>;
  installations?: { manager: string; name: string; version: string; success: boolean; at: string }[];
};

export type PlanDiff = {
  old_version: number | null; new_version: number;
  added: { id: string; title: string; files: string[]; estimate: number[] }[];
  removed: { id: string; title: string; files: string[] }[];
  changed: { id: string; fields: string[]; checks_added: number; checks_removed: number; files_before: string[]; files_after: string[] }[];
  dependencies: { task: string; before: string[]; after: string[] }[];
  verified_impacted: { task: string; files: string[]; affected_by: string[] }[];
  effort: { before: number; after: number; delta: number };
  task_count: { before: number; after: number }; risk: string; warnings: string[]; requires_confirmation: boolean;
  checks_added: { task: string; check: Record<string, unknown> }[];
  checks_removed: { task: string; check: Record<string, unknown> }[];
};

export type SourcesInfo = {
  mode: string; preference: string; labels: Record<string, string>; modes: Record<string, string>;
  preferences: Record<string, string>; effective: string[]; remote_key_set: boolean;
};

export type PreflightAlternative = {
  model: string; source?: string; temperature: number; context_tokens: number; score?: number; reason?: string;
};

export type PreflightSample = {
  id: string; model: string; temperature: number; valid: boolean; seconds?: number; response?: string; error?: string;
  context_tokens?: number; quantization?: string | null; selected_variant?: string;
};

export type Preflight = {
  goal?: string; goal_signature?: string; status: string; error?: string; accepted?: boolean; note: string;
  kind?: string; judge?: string; context_tokens?: number; candidates?: string[];
  recommendation?: { model: string; temperature: number; context_tokens: number; output_tokens?: number;
    reason: string; source?: string; score?: number } | null;
  verdict?: { scores: Record<string, number>; winner?: string; reason?: string };
  samples: PreflightSample[]; base?: string; provider?: string; source_mode?: string; preference?: string;
  sources?: string[]; source_prefix?: boolean; skipped_sources?: string[]; alternatives?: PreflightAlternative[];
  accepted_settings?: { provider?: string; source?: string; model?: string; temperature?: number;
    context_tokens?: number; output_tokens?: number };
  judge_response?: { response?: string; seconds?: number; finish_reason?: string };
};

export type Model = {
  id: string; loaded_context: number | null; max_context: number | null; source: string; source_label?: string;
  type: string; name?: string; family?: string; variants?: string[]; free?: boolean; small_model?: boolean;
  size_bytes?: number | null; quantization?: string | null; selected_variant?: string;
  saved_profile?: { context_tokens: number; output_tokens: number; temperature: number };
};

export type OpenCodeStatus = {
  available: boolean; url?: string; version?: string; error?: string; order?: string[];
  models?: { id: string; name?: string; family?: string; context?: number; variants?: string[] }[];
};

export type Snapshot = {
  pause_requested: boolean; preflight?: Preflight | null; pending_answers?: string[]; folder: string; busy: boolean;
  phase: string; error: string; settings: Settings; state: State | null;
  progress: { implemented: number; recheck: number; waiting: number; percent: number; done: number; total: number; low: number; high: number; samples: number } | null;
  logs: string; log_folder: string;
  scan: { files: string[]; file_count: number; truncated: boolean; documents: Record<string, string>; git_present: boolean; has_environment: boolean };
  index?: { indexed: boolean; summary?: Record<string, unknown> | null; last_change?: { changed_count: number; removed_count: number; unchanged: number; changed: string[]; removed: string[] } | null };
  graph?: Record<string, unknown>; scenarios?: Record<string, unknown> | null; benchmark?: Record<string, unknown> | null;
  opencode?: { last_model?: string; blocked_models?: string[]; blocked_sources?: Record<string, number>; order?: string[] };
  sources?: SourcesInfo | null;
  operations?: Record<string, unknown>; environment?: { lock_file: string; presets: { file: string; name: string; created_at: number; model?: string }[] };
};
