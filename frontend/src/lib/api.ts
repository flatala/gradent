import type {
  AssignmentAssessmentRequestPayload,
  AssignmentAssessmentResponsePayload,
  AssignmentProgressResponsePayload,
  ChatHistoryResponsePayload,
  ChatRequestPayload,
  ChatResponsePayload,
  HealthResponse,
  ProgressLogRequestPayload,
  ProgressLogResponsePayload,
  ProgressSummaryResponsePayload,
  ScheduleRequestPayload,
  ScheduleResponsePayload,
  SimpleStatusResponse,
  SuggestionsMutationResponse,
  SuggestionsRequest,
  SuggestionsResetRequest,
  SuggestionsResponse,
  ExamResponsePayload,
  SessionsResponsePayload,
  AutonomousConfigPayload,
  AutonomousConfigResponse,
} from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type");

  let data: unknown = null;
  if (contentType?.includes("application/json")) {
    data = await response.json();
  } else if (contentType) {
    data = await response.text();
  }

  if (!response.ok) {
    const message =
      (data as any)?.detail ||
      (data as any)?.error ||
      response.statusText ||
      "Request failed";
    throw new Error(message);
  }

  return (data as T) ?? ({} as T);
}

const jsonHeaders = {
  "Content-Type": "application/json",
};

export const api = {
  // Health -----------------------------------------------------------------
  async getHealth() {
    return request<HealthResponse>("/health");
  },

  // Chat -------------------------------------------------------------------
  async listChatSessions() {
    return request<SessionsResponsePayload>("/chat/sessions");
  },

  async getChatHistory(sessionId: string) {
    return request<ChatHistoryResponsePayload>(`/chat/${sessionId}/history`);
  },

  async resetChatSession(sessionId: string) {
    return request<SimpleStatusResponse>(`/chat/${sessionId}`, {
      method: "DELETE",
    });
  },

  async sendChatMessage(payload: ChatRequestPayload) {
    return request<ChatResponsePayload>("/chat", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  // Suggestions ------------------------------------------------------------
  async listSuggestions(params?: SuggestionsRequest) {
    const searchParams = new URLSearchParams();
    if (params?.status) {
      searchParams.set("status", params.status);
    }
    if (params?.user_id) {
      searchParams.set("user_id", params.user_id.toString());
    }
    const query = searchParams.toString();
    return request<SuggestionsResponse>(
      `/suggestions${query ? `?${query}` : ""}`,
    );
  },

  async generateSuggestions(payload?: SuggestionsRequest) {
    return request<SuggestionsResponse>("/suggestions/generate", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload ?? {}),
    });
  },

  async resetSuggestions(payload: SuggestionsResetRequest) {
    return request<SuggestionsMutationResponse>("/suggestions/reset", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  // Assignment assessment ---------------------------------------------------
  async assessAssignment(payload: AssignmentAssessmentRequestPayload) {
    return request<AssignmentAssessmentResponsePayload>("/assess-assignment", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  // Scheduling --------------------------------------------------------------
  async scheduleEvent(payload: ScheduleRequestPayload) {
    return request<ScheduleResponsePayload>("/schedule", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  // Progress tracking ------------------------------------------------------
  async logProgress(payload: ProgressLogRequestPayload) {
    return request<ProgressLogResponsePayload>("/progress/log", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  async getProgressSummary(userId: number, days = 7) {
    const query = new URLSearchParams({
      user_id: userId.toString(),
      days: days.toString(),
    });
    return request<ProgressSummaryResponsePayload>(
      `/progress/summary?${query.toString()}`,
    );
  },

  async getAssignmentProgress(userId: number, assignmentId: number) {
    const query = new URLSearchParams({ user_id: userId.toString() });
    return request<AssignmentProgressResponsePayload>(
      `/progress/assignments/${assignmentId}?${query.toString()}`,
    );
  },

  // Exam generation --------------------------------------------------------
  async generateExam(payload: {
    files: File[];
    questionHeader: string;
    questionDescription: string;
    apiKey?: string;
    modelName?: string;
  }) {
    const formData = new FormData();
    payload.files.forEach((file) => {
      formData.append("files", file);
    });
    formData.append("question_header", payload.questionHeader);
    formData.append("question_description", payload.questionDescription);
    if (payload.apiKey?.trim()) {
      formData.append("api_key", payload.apiKey.trim());
    }
    if (payload.modelName?.trim()) {
      formData.append("model_name", payload.modelName.trim());
    }

    return request<ExamResponsePayload>("/generate-exam", {
      method: "POST",
      body: formData,
    });
  },

  async cleanupUploads() {
    return request<SimpleStatusResponse>("/cleanup", {
      method: "DELETE",
    });
  },

  // Autonomous Mode endpoints
  async getAutonomousConfig() {
    return request<AutonomousConfigResponse>("/api/autonomous/config", {
      method: "GET",
    });
  },

  async updateAutonomousConfig(config: AutonomousConfigPayload) {
    return request<SimpleStatusResponse>("/api/autonomous/config", {
      method: "PUT",
      body: JSON.stringify(config),
    });
  },

  async triggerAutonomousExecution() {
    return request<SimpleStatusResponse>("/api/autonomous/execute", {
      method: "POST",
    });
  },

  async testDiscordWebhook(webhookUrl: string) {
    return request<SimpleStatusResponse>("/api/autonomous/test-webhook", {
      method: "POST",
      body: JSON.stringify({ webhook_url: webhookUrl }),
    });
  },
};
