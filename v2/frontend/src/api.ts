import type { ImportBatch,Memory,MemoryCandidate,Message } from './types';

const API_BASE=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'');

export async function loadMessages():Promise<Message[]> {
  const response=await fetch(`${API_BASE}/api/messages`);
  if(!response.ok) throw new Error('读取聊天失败');
  return response.json();
}

type StreamHandlers={
  onMeta:(data:{requestId:string;user:Message;memoryIds:string[]})=>void;
  onDelta:(text:string)=>void;
  onDone:(data:{assistant:Message;scene:string})=>void;
};

export async function streamMessage(text:string,requestId:string,signal:AbortSignal,handlers:StreamHandlers):Promise<void>{
  const response=await fetch(`${API_BASE}/api/chat/stream`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,request_id:requestId}),signal});
  if(!response.ok) throw new Error((await response.json().catch(()=>null))?.detail||'发送失败');
  if(!response.body) throw new Error('当前浏览器不能读取流式回复');
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
  const dispatch=(block:string)=>{
    const lines=block.split('\n');
    const event=lines.find(line=>line.startsWith('event:'))?.slice(6).trim();
    const raw=lines.filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trim()).join('');
    if(!event||!raw)return;
    const data=JSON.parse(raw);
    if(event==='meta')handlers.onMeta(data);
    if(event==='delta')handlers.onDelta(data.text||'');
    if(event==='done')handlers.onDone(data);
    if(event==='error')throw new Error(data.message||'回复中断');
  };
  while(true){
    const {done,value}=await reader.read();
    buffer+=decoder.decode(value||new Uint8Array(),{stream:!done}).replace(/\r\n/g,'\n');
    let boundary=buffer.indexOf('\n\n');
    while(boundary>=0){dispatch(buffer.slice(0,boundary));buffer=buffer.slice(boundary+2);boundary=buffer.indexOf('\n\n');}
    if(done)break;
  }
  if(buffer.trim())dispatch(buffer);
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
