export type Speaker = 'user' | 'assistant';
export type MessageKind = 'text' | 'voice' | 'call_event';

export interface Message {
  id: string;
  speaker: Speaker;
  kind: MessageKind;
  text: string;
  createdAt: string;
  callId?: string;
  audioUrl?: string;
  durationMs?: number;
  voiceStatus?: 'generating'|'ready'|'failed';
}

export interface CallTurn {
  speaker: Speaker;
  text: string;
  createdAt: string;
}

export interface CallRecord {
  id: string;
  direction: 'incoming' | 'outgoing';
  status: 'ringing' | 'active' | 'answered' | 'missed' | 'declined';
  startedAt: string;
  answeredAt?: string;
  endedAt?: string;
  durationSeconds: number;
  turns: CallTurn[];
}

export interface Memory {
  id: string;
  layer: 'personality' | 'relationship' | 'user' | 'event' | 'feeling' | 'plan' | 'sample';
  content: string;
  summary: string;
  status: 'candidate' | 'active' | 'archived' | 'superseded' | 'deleted';
  importance: number;
  confidence: number;
  tags: string[];
  createdAt: string;
}

export interface ImportBatch {
  id: string;
  filename: string;
  status: 'reading' | 'previewed' | 'failed';
  conversation_count: number;
  message_count: number;
  cursor: number;
  duplicate?: boolean;
  resumed?: boolean;
}

export interface MemoryCandidate {
  id: string;
  layer: 'relationship' | 'user' | 'event' | 'feeling' | 'plan' | 'sample';
  summary: string;
  evidence_text: string;
  confidence: number;
  status: 'pending' | 'accepted' | 'rejected';
  conflict_count?: number;
  has_conflict?: number;
}

export interface IntegrityReport {
  batchId: string;
  sourceStatus: string;
  sourceSha256: string;
  conversations: number;
  messages: number;
  candidates: Record<string,number>;
  acceptedMemories: number;
  openIssues: Record<string,number>;
  checks: Record<string,boolean>;
  safeToBackup: boolean;
}

export interface RestorePreview {
  token: string;
  checksum: string;
  exportedAt?: string;
  counts: Record<string,number>;
  mode: 'merge-only';
  warning: string;
}

export interface ExtractionJob {
  id: string;
  batch_id: string;
  status: 'ready'|'running'|'paused'|'complete';
  total: number;
  processed: number;
  failed: number;
  created: number;
  last_error?: string;
}
