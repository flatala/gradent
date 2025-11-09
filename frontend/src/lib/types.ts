export interface HealthResponse {
  status: string;
  message: string;
}

export type ChatRole = "user" | "assistant";

export interface ChatHistoryMessage {
  role: ChatRole;
  content: string;
}

export interface ToolCallInfo {
  tool_name: string;
  tool_type: "scheduler" | "assessment" | "suggestions" | "exam_generation";
  status: "started" | "completed" | "failed";
  result?: Record<string, any>;
  error?: string;
  timestamp: string;
}

export interface ChatRequestPayload {
  session_id: string;
  message: string;
  reset?: boolean;
}

export interface ChatResponsePayload {
  session_id: string;
  response: string;
  history: ChatHistoryMessage[];
  tool_calls: ToolCallInfo[];
}

export interface ChatHistoryResponsePayload {
  session_id: string;
  history: ChatHistoryMessage[];
}

export interface SessionsResponsePayload {
  sessions: string[];
}

export interface SuggestionsRequest {
  status?: string;
  user_id?: number;
}

export interface SuggestionRecord {
  id: number;
  user_id: number;
  title: string;
  message: string;
  category?: string | null;
  priority?: string | null;
  suggested_time?: string | null;
  suggested_time_text?: string | null;
  status?: string | null;
  channel_config?: Record<string, unknown>;
  linked_assignments?: unknown[];
  linked_events?: unknown[];
  tags?: unknown[];
  sources?: unknown[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SuggestionsResponse {
  suggestions: SuggestionRecord[];
}

export interface SuggestionsResetRequest {
  user_id?: number;
  status?: string;
}

export interface SuggestionsMutationResponse {
  success: boolean;
  updated: number;
  message: string;
}

export interface AssignmentAssessmentRequestPayload {
  title: string;
  description: string;
  course_name?: string;
  assignment_id?: number;
}

export interface AssignmentAssessmentResponsePayload {
  success: boolean;
  data?: Record<string, unknown>;
  error?: string;
}

export interface ScheduleRequestPayload {
  meeting_name: string;
  duration_minutes: number;
  topic?: string;
  event_description?: string;
  attendee_emails?: string[];
  location?: string;
  constraints?: string;
}

export interface ScheduleResponsePayload {
  success: boolean;
  data?: Record<string, unknown>;
  error?: string;
}

export interface ProgressLogRequestPayload {
  user_id: number;
  assignment_id?: number;
  course_id?: number;
  minutes: number;
  focus_rating?: number;
  quality_rating?: number;
  source?: string;
  study_block_id?: number;
  notes?: string;
}

export interface ProgressLogResponsePayload {
  success: boolean;
  message: string;
  hours_logged: number;
  study_history_id?: number;
  assignment_progress?: Record<string, unknown> | null;
  focus_rating?: number | null;
  quality_rating?: number | null;
}

export interface ProgressSummaryResponsePayload {
  success: boolean;
  period_days?: number;
  total_minutes?: number;
  total_hours?: number;
  total_sessions?: number;
  assignments_worked_on?: number;
  avg_focus?: number | null;
  avg_quality?: number | null;
  message?: string | null;
  top_assignments?: Array<Record<string, unknown>>;
}

export interface AssignmentProgressResponsePayload {
  success: boolean;
  message?: string | null;
  assignment_id?: number;
  assignment_title?: string;
  course_name?: string;
  due_at?: string | null;
  status?: string | null;
  hours_done?: number | null;
  hours_remaining?: number | null;
  last_worked_at?: string | null;
  total_sessions?: number | null;
  recent_focus_avg?: number | null;
  recent_quality_avg?: number | null;
  priority?: number | null;
}

export interface ExamResponsePayload {
  success: boolean;
  questions?: string | null;
  error?: string | null;
  uploaded_files?: string[] | null;
}

export interface ExamAssessmentRequestPayload {
  assignment_title: string;
  course_name: string;
  questions: Array<{
    number: string;
    text: string;
    options: string[];
  }>;
  user_answers: Record<string, string>;
  correct_answers: Record<string, string>;
}

export interface ExamAssessmentResponsePayload {
  success: boolean;
  score?: number;
  total_questions?: number;
  percentage?: number;
  study_recommendation?: string;
  detailed_feedback?: string;
  error?: string;
}

export interface SimpleStatusResponse {
  status: string;
  message: string;
}

// Autonomous Mode types
export type ExecutionFrequency = "15min" | "30min" | "1hour" | "3hours" | "6hours" | "12hours" | "24hours";

export interface AutonomousConfigPayload {
  enabled: boolean;
  frequency: ExecutionFrequency;
  ntfy_topic?: string;
}

export interface AutonomousConfigResponse extends AutonomousConfigPayload {
  last_execution?: string;
  next_execution?: string;
}
