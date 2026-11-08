import type { CallRecord,ExtractionJob,ImportBatch,IntegrityReport,Memory,MemoryCandidate,Message,RestorePreview } from './types';

const API_BASE=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'');

export async function loadMessages():Promise<Message[]> {
  const response=await fetch(`${API_BASE}/api/messages`);
  if(!response.ok) throw new Error('读取聊天失败');
  const items:Message[]=await response.json();
  return items.map(message=>message.audioUrl?{...message,audioUrl:`${API_BASE}${message.audioUrl}`}:message);
}

export async function synthesizeVoice(messageId:string):Promise<{audioUrl:string;duration_ms:number;transcript:string}>{
  const response=await fetch(`${API_BASE}/api/voice/messages/${messageId}`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'语音生成失败');
  const result=await response.json();
  return {...result,audioUrl:`${API_BASE}${result.audioUrl}`};
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

export async function updateMemory(memory:Memory):Promise<Memory>{
  const response=await fetch(`${API_BASE}/api/memories/${memory.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({layer:memory.layer,content:memory.content,summary:memory.summary,importance:memory.importance,confidence:memory.confidence,tags:memory.tags})});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'记忆修改失败');
  return response.json();
}

export async function setMemoryStatus(id:string,status:Memory['status']):Promise<Memory>{
  const response=await fetch(`${API_BASE}/api/memories/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  if(!response.ok)throw new Error('记忆状态修改失败');
  return response.json();
}

export async function reinforceMemory(id:string):Promise<Memory>{
  const response=await fetch(`${API_BASE}/api/memories/${id}/reinforce`,{method:'POST'});
  if(!response.ok)throw new Error('记忆加强失败');
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

export async function acceptCandidates(batchId:string,ids:string[]):Promise<{accepted:number;skippedDuplicates:number;blockedConflicts:string[]}> {
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/candidates/accept`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
  if(!response.ok) throw new Error('写入长期记忆失败');
  return response.json();
}

export async function analyzeCandidates(batchId:string):Promise<{analyzed:number;created:number;counts:Record<string,number>}>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/candidates/analyze`,{method:'POST'});
  if(!response.ok)throw new Error('相似与冲突检查失败');
  return response.json();
}

export async function updateCandidate(batchId:string,id:string,layer:MemoryCandidate['layer'],summary:string):Promise<MemoryCandidate>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/candidates/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({layer,summary})});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'候选修改失败');
  return response.json();
}

export async function rejectCandidates(batchId:string,ids:string[]):Promise<{rejected:number}>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/candidates/reject`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
  if(!response.ok)throw new Error('忽略候选失败');
  return response.json();
}

export async function loadIntegrityReport(batchId:string):Promise<IntegrityReport>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/integrity-report`);
  if(!response.ok)throw new Error('生成迁移报告失败');
  return response.json();
}

export async function downloadBackup():Promise<void>{
  const response=await fetch(`${API_BASE}/api/backups/export`);
  if(!response.ok)throw new Error('备份生成失败');
  const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
  const disposition=response.headers.get('Content-Disposition')||'';
  link.href=url;link.download=disposition.match(/filename="([^"]+)"/)?.[1]||'my-little-phone-v2-backup.json';
  document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
}

export async function previewRestore(file:File):Promise<RestorePreview>{
  const body=new FormData();body.append('file',file);
  const response=await fetch(`${API_BASE}/api/backups/restore-preview`,{method:'POST',body});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'备份检查失败');
  return response.json();
}

export async function confirmRestore(token:string):Promise<{restored:boolean;inserted:Record<string,number>}>{
  const response=await fetch(`${API_BASE}/api/backups/restore-confirm`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,mode:'merge'})});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'恢复失败');
  return response.json();
}

export async function createExtractionJob(batchId:string):Promise<ExtractionJob>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/extraction-jobs`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'创建精提取任务失败');
  return response.json();
}

export async function controlExtractionJob(batchId:string,jobId:string,action:'pause'|'resume'|'retry'):Promise<ExtractionJob>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/extraction-jobs/${jobId}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});
  if(!response.ok)throw new Error('任务操作失败');
  return response.json();
}

export async function runExtractionStep(batchId:string,jobId:string):Promise<{job:ExtractionJob;created:number;failed:number;complete:boolean}>{
  const response=await fetch(`${API_BASE}/api/history-imports/${batchId}/deepseek-candidates?max_conversations=3&job_id=${jobId}`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'精提取暂停');
  return response.json();
}

export async function startCall(direction:'incoming'|'outgoing'='outgoing'):Promise<CallRecord>{
  const response=await fetch(`${API_BASE}/api/calls`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({direction})});
  if(!response.ok)throw new Error('通话建立失败');
  return response.json();
}

export async function endCall(id:string,status:'answered'|'missed'|'declined'='answered'):Promise<CallRecord>{
  const response=await fetch(`${API_BASE}/api/calls/${id}/end`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  if(!response.ok)throw new Error('挂断失败');
  return response.json();
}

export async function loadCalls():Promise<CallRecord[]>{
  const response=await fetch(`${API_BASE}/api/calls`);
  if(!response.ok)throw new Error('读取通话记录失败');
  return response.json();
}

export async function answerCall(id:string):Promise<CallRecord>{
  const response=await fetch(`${API_BASE}/api/calls/${id}/answer`,{method:'POST'});
  if(!response.ok)throw new Error('接听失败');
  return response.json();
}

export interface CompanionSettings {enabled:boolean;allow_calls:boolean;dnd_enabled:boolean;dnd_start:string;dnd_end:string;timezone:string}
export async function loadCompanionSettings():Promise<CompanionSettings>{
  const response=await fetch(`${API_BASE}/api/companion/settings`);if(!response.ok)throw new Error('读取主动陪伴设置失败');return response.json();
}
export async function saveCompanionSettings(settings:CompanionSettings):Promise<CompanionSettings>{
  const response=await fetch(`${API_BASE}/api/companion/settings`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});if(!response.ok)throw new Error('保存主动陪伴设置失败');return response.json();
}

function decodeApplicationKey(value:string):ArrayBuffer{
  const padded=(value+'='.repeat((4-value.length%4)%4)).replace(/-/g,'+').replace(/_/g,'/');
  return Uint8Array.from(atob(padded),character=>character.charCodeAt(0)).buffer as ArrayBuffer;
}

export async function subscribeToPush():Promise<void>{
  if(!('serviceWorker' in navigator)||!('PushManager' in window))throw new Error('当前浏览器不支持网页推送，请先把小手叽添加到主屏幕');
  const permission=await Notification.requestPermission();
  if(permission!=='granted')throw new Error('通知权限没有开启');
  const registration=await navigator.serviceWorker.ready;
  const keyResponse=await fetch(`${API_BASE}/api/notifications/vapid-public-key`);
  if(!keyResponse.ok)throw new Error((await keyResponse.json().catch(()=>null))?.detail||'推送服务尚未配置');
  const {publicKey}=await keyResponse.json();
  const current=await registration.pushManager.getSubscription();
  const subscription=current||await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:decodeApplicationKey(publicKey)});
  const response=await fetch(`${API_BASE}/api/notifications/subscribe`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(subscription.toJSON())});
  if(!response.ok)throw new Error('保存通知订阅失败');
}
