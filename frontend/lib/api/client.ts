export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "/api";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user?: User;
};

export type UploadedFile = {
  id: string;
  organization_id: string;
  uploaded_by_user_id: string;
  original_filename: string;
  stored_filename: string;
  file_type: string;
  row_count: number | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type FilePreview = {
  file_id: string;
  columns: string[];
  sample_rows: Record<string, unknown>[];
};

export type ColumnMapping = {
  date?: string | null;
  amount?: string | null;
  reference?: string | null;
  description?: string | null;
  customer_name?: string | null;
  currency?: string | null;
};

export type NormalizeResponse = {
  uploaded_file_id: string;
  status: "normalized" | "normalized_with_rejections" | "failed";
  total_rows: number;
  valid_rows: number;
  rejected_rows: number;
  rejected_examples: RejectedRecord[];
  message: string;
};

export type RejectedRecord = {
  id: string;
  uploaded_file_id: string;
  source_row_number: number;
  raw_data: Record<string, unknown>;
  rejection_reason: string;
  field_errors: Record<string, string> | null;
  created_at: string;
};

export type RejectedRecordsResponse = {
  uploaded_file_id: string;
  total_rejected: number;
  records: RejectedRecord[];
};

export type ReconciliationRun = {
  id: string;
  organization_id: string;
  created_by_user_id: string;
  file_a_id: string;
  file_b_id: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type NormalizedRecord = {
  id: string;
  transaction_date: string | null;
  amount: string | null;
  reference: string | null;
  description: string | null;
  customer_name: string | null;
};

export type MatchResult = {
  id: string;
  reconciliation_run_id: string;
  file_a_record_id: string | null;
  file_b_record_id: string | null;
  status: string;
  confidence_score: number;
  match_reason: string | null;
  amount_difference: string | null;
  date_difference_days: number | null;
  reference_similarity: number | null;
  description_similarity: number | null;
  created_at: string;
  reviewed_at: string | null;
  file_a_record: NormalizedRecord | null;
  file_b_record: NormalizedRecord | null;
};

export type ReconciliationResults = {
  run_id: string;
  status: string;
  green_matches: MatchResult[];
  yellow_possible_matches: MatchResult[];
  red_unmatched: MatchResult[];
  summary: {
    total_matches: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
    approved_count: number;
    rejected_count: number;
  };
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken() {
  if (typeof window === "undefined") return null;
  // TODO: migrate MVP localStorage token storage to httpOnly cookies before production.
  return window.localStorage.getItem("novoriq_token");
}

export function setToken(token: string) {
  if (typeof window !== "undefined") window.localStorage.setItem("novoriq_token", token);
}

export function clearToken() {
  if (typeof window !== "undefined") window.localStorage.removeItem("novoriq_token");
}

async function parseError(response: Response) {
  try {
    const payload: { detail?: string | Record<string, unknown> | Array<{ msg?: string }>; message?: string } =
      await response.json();
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg ?? "Invalid field").join(", ");
    }
    if (payload.detail && typeof payload.detail === "object") {
      const message = payload.detail.message;
      if (typeof message === "string") return message;
      return JSON.stringify(payload.detail);
    }
    return payload.message ?? "Request failed";
  } catch {
    return response.statusText || "Request failed";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  const hasFormData = init.body instanceof FormData;

  if (!hasFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function download(path: string): Promise<Blob> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  return response.blob();
}

export const api = {
  register: (payload: {
    full_name?: string;
    email: string;
    password: string;
    organization_name: string;
  }) => request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<User>("/auth/me"),
  listFiles: () => request<UploadedFile[]>("/files"),
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<UploadedFile>("/files/upload", { method: "POST", body: formData });
  },
  previewFile: (fileId: string) => request<FilePreview>(`/files/${fileId}/preview`),
  normalizeFile: (fileId: string, mapping: ColumnMapping) =>
    request<NormalizeResponse>(`/files/${fileId}/normalize`, {
      method: "POST",
      body: JSON.stringify(mapping),
    }),
  getRejectedRecords: (fileId: string) =>
    request<RejectedRecordsResponse>(`/files/${fileId}/rejected-records`),
  listRuns: () => request<ReconciliationRun[]>("/reconciliation-runs"),
  createRun: (payload: { file_a_id: string; file_b_id: string }) =>
    request<ReconciliationRun>("/reconciliation-runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRun: (runId: string) => request<ReconciliationRun>(`/reconciliation-runs/${runId}`),
  runMatching: (runId: string) =>
    request<ReconciliationResults>(`/reconciliation-runs/${runId}/run`, { method: "POST" }),
  getReconciliationResults: (runId: string) =>
    request<ReconciliationResults>(`/reconciliation-runs/${runId}/results`),
  approveMatch: (matchId: string) =>
    request<{ id: string; status: string; reviewed_at: string }>(`/match-results/${matchId}/approve`, { method: "POST" }),
  rejectMatch: (matchId: string) =>
    request<{ id: string; status: string; reviewed_at: string }>(`/match-results/${matchId}/reject`, { method: "POST" }),
  exportReconciliationRun: (runId: string) => download(`/reconciliation-runs/${runId}/export`),
};
