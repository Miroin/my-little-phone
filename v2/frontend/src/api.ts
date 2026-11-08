import type { ImportBatch,Memory,MemoryCandidate,Message } from './types';

const API_BASE=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'');

export async function loadMessages():Promise<Message[]> {
  const response=await fetch(`${API_BASE}/api/messages`);
  if(!response.ok) throw new Error('读取聊天失败');
  return response.json();
}

export async function sendMessage(text:string):Promise<{user:Message;assistant:Message}> {
  const response=await fetch(`${API_BASE}/api/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  if(!response.ok) throw new Error((await response.json().catch(()=>null))?.detail||'发送失败');
  return response.json();
}

export async function loadMemories():Promise<Memory[]> {
  const response=await fetch(`${API_BASE}/api/memories?limit=100`);
  if(!response.ok) throw new Error('读取记忆失败');
  return response.json();
}

export async function uploadChatHistory(file:File):Promise<ImportBatch> {
  const body=new FormData();body.append('file',file);
  const response=await fetch(`${API_BASE}/api/history-imports/chatgpt`,{method:'POST',body});
  if(!response.ok) throw new Error((await response.json().catch(()=>null))?.detail||'读取聊天文件失败');
  return response.json();
}

export async function createLocalCandidates(batchId:string):Promise<{created:number;counts:Record<string,number>}> {
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/local-candidates`,{method:'POST'});
  if(!response.ok) throw new Error((await response.json().catch(()=>null))?.detail||'本地初筛失败');
  return response.json();
}

export async function loadCandidates(batchId:string,offset=0):Promise<{total:number;items:MemoryCandidate[]}> {
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/candidates?offset=${offset}&limit=20`);
  if(!response.ok) throw new Error('读取候选记忆失败');
  return response.json();
}

export async function acceptCandidates(batchId:string,ids:string[]):Promise<{accepted:number;skippedDuplicates:number}> {
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/candidates/accept`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
  if(!response.ok) throw new Error('写入长期记忆失败');
  return response.json();
}
