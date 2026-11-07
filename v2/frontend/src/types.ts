export type Speaker = 'user' | 'assistant';
export type MessageKind = 'text' | 'voice' | 'call_event';

export interface Message {
  id: string;
  speaker: Speaker;
  kind: MessageKind;
  text: string;
  createdAt: string;
  callId?: string;
}

export interface CallTurn {
  speaker: Speaker;
  text: string;
  createdAt: string;
}

export interface CallRecord {
  id: string;
  direction: 'incoming' | 'outgoing';
  status: 'answered' | 'missed' | 'declined';
  startedAt: string;
  endedAt?: string;
  durationSeconds: number;
  turns: CallTurn[];
}

export interface Memory {
  id: string;
  category: 'persona' | 'relationship' | 'user' | 'event' | 'feedback';
  text: string;
  createdAt: string;
}
