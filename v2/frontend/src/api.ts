import type { Message } from './types';

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
