/**
 * OpenCode API Type Definitions
 * Maps Python Pydantic models to TypeScript interfaces
 */

/**
 * Tool execution state
 */
export type ToolStateStatus = "pending" | "running" | "completed" | "error";

export interface ToolState {
  status: ToolStateStatus;
  input: Record<string, unknown>;
  output?: string;
  title?: string;
  metadata: Record<string, unknown>;
  time_start?: number;
  time_end?: number;
  error?: string;
}

/**
 * Message role type
 */
export type MessageRole = "user" | "assistant" | "system";

/**
 * Part types
 */
export type PartType =
  | "text"
  | "file"
  | "tool"
  | "reasoning"
  | "snapshot"
  | "patch"
  | "agent"
  | "subtask"
  | "retry"
  | "compaction";

/**
 * Text content part
 */
export interface TextPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "text";
  text: string;
  time: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  synthetic?: boolean;
  ignored?: boolean;
}

/**
 * File attachment part
 */
export interface FilePart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "file";
  url: string;
  mime: string;
  filename?: string;
  source?: Record<string, unknown>;
}

/**
 * Tool execution part
 */
export interface ToolPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "tool";
  tool: string;
  call_id?: string;
  state: ToolState;
  source?: Record<string, unknown>;
}

/**
 * LLM reasoning/thinking part
 */
export interface ReasoningPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "reasoning";
  text: string;
  time: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

/**
 * Git snapshot part
 */
export interface SnapshotPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "snapshot";
  snapshot: string;
}

/**
 * File patch summary part
 */
export interface PatchPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "patch";
  hash: string;
  files: string[];
}

/**
 * Agent delegation part
 */
export interface AgentPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "agent";
  name: string;
  source?: Record<string, unknown>;
}

/**
 * Subtask invocation part
 */
export interface SubtaskPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "subtask";
  category: string;
}

/**
 * Retry attempt part
 */
export interface RetryPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "retry";
  attempt: number;
}

/**
 * Session compaction marker part
 */
export interface CompactionPart {
  id: string;
  session_id: string;
  message_id: string;
  part_type: "compaction";
  auto: boolean;
}

/**
 * Union type for all part types
 */
export type Part =
  | TextPart
  | FilePart
  | ToolPart
  | ReasoningPart
  | SnapshotPart
  | PatchPart
  | AgentPart
  | SubtaskPart
  | RetryPart
  | CompactionPart;

/**
 * Token usage tracking
 */
export interface TokenUsage {
  input: number;
  output: number;
  reasoning: number;
  cache: Record<string, number>;
}

/**
 * Message summary info
 */
export interface MessageSummary {
  title?: string;
  body?: string;
  diffs?: Array<Record<string, unknown>>;
}

/**
 * Message model - container for parts
 */
export interface Message {
  id: string;
  session_id: string;
  role: MessageRole;
  time: Record<string, unknown>;
  text: string;
  parts: Part[];
  summary?: MessageSummary;
  token_usage?: TokenUsage;
  metadata: Record<string, unknown>;
}

/**
 * User message - alias for Message with role='user'
 */
export interface UserMessage extends Message {
  role: "user";
}

/**
 * Assistant message - alias for Message with role='assistant'
 */
export interface AssistantMessage extends Message {
  role: "assistant";
  finish?: string;
  title?: string;
  body?: string;
  diffs?: Array<Record<string, unknown>>;
}

/**
 * Session share metadata
 */
export interface SessionShare {
  url?: string;
}

/**
 * Session revert state
 */
export interface SessionRevert {
  message_id: string;
  part_id?: string;
  snapshot: string;
  diff?: string;
}

/**
 * Memory model - stores agent memories with embeddings
 */
export interface Memory {
  id: string;
  session_id: string;
  content: string;
  embedding?: number[];
  metadata: Record<string, unknown>;
  created: number;
}

/**
 * Memory summary model for compressed conversation history
 */
export interface MemorySummary {
  session_id: string;
  summary: string;
  key_points: string[];
  original_token_count: number;
  compressed_token_count: number;
  compression_ratio: number;
  timestamp: number;
  target_compression: number;
}

/**
 * Session model
 */
export interface Session {
  id: string;
  slug: string;
  project_id: string;
  directory: string;
  parent_id?: string;
  title: string;
  version: string;
  summary?: MessageSummary;
  share?: SessionShare;
  permission?: Array<Record<string, unknown>>;
  revert?: SessionRevert;
  time_created: number;
  time_updated: number;
  time_compacting?: number;
  time_archived?: number;
  message_counter: number;
  message_count: number;
  total_cost: number;
}

/**
 * API Response wrapper (common pattern)
 */
export interface ApiResponse<T> {
  data: T;
  error?: string;
}
