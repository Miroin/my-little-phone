import type { CallRecord,ExtractionJob,ImportBatch,IntegrityReport,Memory,MemoryCandidate,Message,RestorePreview } from './types';

let API_BASE=(localStorage.getItem('mlp_v2_api_base')||import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'');
export const currentApiBase=()=>API_BASE;
export const currentAccessToken=()=>localStorage.getItem('mlp_v2_access_token')||'';
export function saveApiBase(value:string){const normalized=value.trim().replace(/\/$/,'');if(!/^https?:\/\//i.test(normalized))throw new Error('请输入完整的 http 或 https 地址');API_BASE=normalized;localStorage.setItem('mlp_v2_api_base',normalized);}
export function saveAccessToken(value:string){localStorage.setItem('mlp_v2_access_token',value.trim());}
async function apiFetch(input:RequestInfo|URL,init:RequestInit={}):Promise<Response>{
  const headers=new Headers(init.headers||{}),token=currentAccessToken();
  if(token)headers.set('X-MLP-Access-Token',token);
  return window.fetch(input,{...init,headers});
}
const assetCache=new Map<string,string>();
async function assetObjectUrl(path:string):Promise<string>{const cached=assetCache.get(path);if(cached)return cached;const response=await apiFetch(`${API_BASE}${path}`);if(!response.ok)throw new Error('读取媒体失败');const url=URL.createObjectURL(await response.blob());assetCache.set(path,url);return url;}
export interface ServiceReadiness{ready:boolean;checks:Record<'database'|'deepseek'|'minimax'|'scheduler'|'accessProtection'|'push',boolean>;missing:string[];memoryCount:number}
export async function checkBackend():Promise<ServiceReadiness>{const health=await window.fetch(`${API_BASE}/health`);if(!health.ok)throw new Error('后端连接失败');const session=await apiFetch(`${API_BASE}/api/session`);if(!session.ok)throw new Error(session.status===401?'服务访问口令不正确':'后端连接失败');const response=await apiFetch(`${API_BASE}/api/readiness`);if(!response.ok)throw new Error('无法读取服务配置状态');return {...await response.json(),memoryCount:(await health.json()).memoryCount};}
export interface CharacterProfile{subject:'shenyan'|'user';displayName:string;categories:Record<'identity'|'appearance'|'personality'|'relationship'|'habits'|'life',string>;updatedAt:string}
export async function loadProfiles():Promise<CharacterProfile[]>{const response=await apiFetch(`${API_BASE}/api/profiles`);if(!response.ok)throw new Error('读取人物档案失败');return response.json();}
export async function saveProfile(profile:CharacterProfile):Promise<CharacterProfile>{const response=await apiFetch(`${API_BASE}/api/profiles/${profile.subject}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:profile.displayName,categories:profile.categories})});if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'保存档案失败');return response.json();}
export async function sendMessageFeedback(messageId:string,verdict:'like'|'dislike',reason=''):Promise<void>{const response=await apiFetch(`${API_BASE}/api/memory-feedback`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message_id:messageId,scene:'chat',verdict,reason})});if(!response.ok)throw new Error('反馈保存失败');}
export interface LifeNote{id:string;kind:'home'|'music'|'schedule';title:string;content:string;created_at:string;updated_at:string}
export interface MediaAsset{id:string;title:string;url:string;mime_type:string;created_at:string}
export async function loadLifeNotes(kind?:LifeNote['kind']):Promise<LifeNote[]>{const response=await apiFetch(`${API_BASE}/api/life/notes${kind?`?kind=${kind}`:''}`);if(!response.ok)throw new Error('读取共同生活记录失败');return response.json();}
export async function addLifeNote(kind:LifeNote['kind'],title:string,content:string):Promise<LifeNote>{const response=await apiFetch(`${API_BASE}/api/life/notes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,title,content})});if(!response.ok)throw new Error('保存失败');return response.json();}
export async function deleteLifeNote(id:string):Promise<void>{const response=await apiFetch(`${API_BASE}/api/life/notes/${id}`,{method:'DELETE'});if(!response.ok)throw new Error('删除失败');}
export interface HomeGameState{version:number;scene:'ground'|'upstairs'|'yard';actors:Record<string,{x:number;y:number;facing:number}>;pet_names:Record<'dog'|'cat',string>;furniture:Record<string,unknown>}
export async function loadHomeState():Promise<HomeGameState|null>{const response=await apiFetch(`${API_BASE}/api/life/home-state`);if(!response.ok)throw new Error('读取小家存档失败');return (await response.json()).state;}
export async function saveHomeState(state:HomeGameState):Promise<HomeGameState>{const response=await apiFetch(`${API_BASE}/api/life/home-state`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(state)});if(!response.ok)throw new Error('保存小家失败');return (await response.json()).state;}
export async function loadMedia():Promise<MediaAsset[]>{const response=await apiFetch(`${API_BASE}/api/life/media`);if(!response.ok)throw new Error('读取相册失败');const items:MediaAsset[]=await response.json();return Promise.all(items.map(async item=>({...item,url:await assetObjectUrl(item.url)})));}
export async function uploadMedia(file:File,title=''):Promise<MediaAsset>{const body=new FormData();body.append('file',file);body.append('title',title);const response=await apiFetch(`${API_BASE}/api/life/media`,{method:'POST',body});if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'上传图片失败');const item:MediaAsset=await response.json();return {...item,url:await assetObjectUrl(item.url)};}
export async function deleteMedia(id:string):Promise<void>{const response=await apiFetch(`${API_BASE}/api/life/media/${id}`,{method:'DELETE'});if(!response.ok)throw new Error('删除照片失败');}
export interface WorldbookEntry{id:string;title:string;content:string;keywords:string[];enabled:boolean;createdAt:string;updatedAt:string}
export async function loadWorldbook():Promise<WorldbookEntry[]>{const response=await apiFetch(`${API_BASE}/api/worldbook`);if(!response.ok)throw new Error('读取世界书失败');return response.json();}
export async function createWorldbookEntry(entry:Omit<WorldbookEntry,'id'|'createdAt'|'updatedAt'>):Promise<WorldbookEntry>{const response=await apiFetch(`${API_BASE}/api/worldbook`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(entry)});if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'保存世界书失败');return response.json();}
export async function updateWorldbookEntry(entry:WorldbookEntry):Promise<WorldbookEntry>{const response=await apiFetch(`${API_BASE}/api/worldbook/${entry.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:entry.title,content:entry.content,keywords:entry.keywords,enabled:entry.enabled})});if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'修改世界书失败');return response.json();}
export async function deleteWorldbookEntry(id:string):Promise<void>{const response=await apiFetch(`${API_BASE}/api/worldbook/${id}`,{method:'DELETE'});if(!response.ok)throw new Error('删除世界书条目失败');}

export async function loadMessages(limit=100,offset=0):Promise<Message[]> {
  const response=await apiFetch(`${API_BASE}/api/messages?limit=${limit}&offset=${offset}`);
  if(!response.ok) throw new Error('读取聊天失败');
  const items:Message[]=await response.json();
  return Promise.all(items.map(async message=>{
    if(message.audioUrl)return {...message,audioUrl:await assetObjectUrl(message.audioUrl)};
    const marked=message.speaker==='assistant'&&/^\s*(?:\[voice\]|\[\[voice\]\]|【voice】)/i.test(message.text);
    if(!marked)return message;
    const clean=message.text.replace(/^\s*(?:\[voice\]|\[\[voice\]\]|【voice】)\s*/i,'');
    try{const audio=await synthesizeVoice(message.id);return {...message,kind:'voice' as const,text:audio.transcript,audioUrl:audio.audioUrl,durationMs:audio.duration_ms,voiceStatus:'ready' as const};}
    catch{return {...message,text:clean,voiceStatus:'failed' as const};}
  }));
}

type VoiceResult={audioUrl:string;duration_ms:number;transcript:string};
const voiceJobs=new Map<string,Promise<VoiceResult>>();
export function synthesizeVoice(messageId:string,retry=false):Promise<VoiceResult>{
  const key=`${messageId}:${retry?'retry':'normal'}`,running=voiceJobs.get(key);if(running)return running;
  const job=(async()=>{const response=await apiFetch(`${API_BASE}/api/voice/messages/${messageId}${retry?'?retry=true':''}`,{method:'POST'});if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'语音生成失败');const result=await response.json();return {...result,audioUrl:await assetObjectUrl(result.audioUrl)};})();
  voiceJobs.set(key,job);job.then(()=>voiceJobs.delete(key),()=>voiceJobs.delete(key));return job;
}

type StreamHandlers={
  onMeta:(data:{requestId:string;user:Message;memoryIds:string[]})=>void;
  onDelta:(text:string)=>void;
  onDone:(data:{assistant:Message;scene:string})=>void;
};

export async function streamMessage(text:string,requestId:string,signal:AbortSignal,handlers:StreamHandlers):Promise<void>{
  const response=await apiFetch(`${API_BASE}/api/chat/stream`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,request_id:requestId}),signal});
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
  const all:Memory[]=[];
  for(let offset=0;;offset+=500){
    const response=await apiFetch(`${API_BASE}/api/memories?limit=500&offset=${offset}`);
    if(!response.ok) throw new Error('读取记忆失败');
    const page:Memory[]=await response.json();all.push(...page);
    if(page.length<500)return all;
  }
}

export async function updateMemory(memory:Memory):Promise<Memory>{
  const response=await apiFetch(`${API_BASE}/api/memories/${memory.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({layer:memory.layer,content:memory.content,summary:memory.summary,importance:memory.importance,confidence:memory.confidence,tags:memory.tags})});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'记忆修改失败');
  return response.json();
}

export async function setMemoryStatus(id:string,status:Memory['status']):Promise<Memory>{
  const response=await apiFetch(`${API_BASE}/api/memories/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  if(!response.ok)throw new Error('记忆状态修改失败');
  return response.json();
}

export async function reinforceMemory(id:string):Promise<Memory>{
  const response=await apiFetch(`${API_BASE}/api/memories/${id}/reinforce`,{method:'POST'});
  if(!response.ok)throw new Error('记忆加强失败');
  return response.json();
}

export interface MemoryEvidence{id:string;memory_id:string;conversation_id?:string;message_start_id?:string;message_end_id?:string;raw_text:string;sha256:string;created_at:string}
export async function loadMemoryEvidence(id:string):Promise<MemoryEvidence[]>{
  const response=await apiFetch(`${API_BASE}/api/memories/${id}/evidence`);
  if(!response.ok)throw new Error('读取原文证据失败');
  return response.json();
}
export async function deleteMemory(id:string):Promise<void>{
  const response=await apiFetch(`${API_BASE}/api/memories/${id}`,{method:'DELETE'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'永久删除失败');
}

export async function uploadChatHistory(file:File):Promise<ImportBatch> {
  const body=new FormData();body.append('file',file);
  const response=await apiFetch(`${API_BASE}/api/history-imports/chatgpt`,{method:'POST',body});
  if(!response.ok) throw new Error((await response.json().catch(()=>null))?.detail||'读取聊天文件失败');
  return response.json();
}

export async function createLocalCandidates(batchId:string):Promise<{created:number;counts:Record<string,number>}> {
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/local-candidates`,{method:'POST'});
  if(!response.ok) throw new Error((await response.json().catch(()=>null))?.detail||'本地初筛失败');
  return response.json();
}

export async function loadCandidates(batchId:string,offset=0):Promise<{total:number;items:MemoryCandidate[]}> {
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/candidates?offset=${offset}&limit=20`);
  if(!response.ok) throw new Error('读取候选记忆失败');
  return response.json();
}

export async function acceptCandidates(batchId:string,ids:string[]):Promise<{accepted:number;skippedDuplicates:number;blockedConflicts:string[]}> {
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/candidates/accept`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
  if(!response.ok) throw new Error('写入长期记忆失败');
  return response.json();
}

export async function analyzeCandidates(batchId:string):Promise<{analyzed:number;created:number;counts:Record<string,number>}>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/candidates/analyze`,{method:'POST'});
  if(!response.ok)throw new Error('相似与冲突检查失败');
  return response.json();
}

export async function updateCandidate(batchId:string,id:string,layer:MemoryCandidate['layer'],summary:string):Promise<MemoryCandidate>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/candidates/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({layer,summary})});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'候选修改失败');
  return response.json();
}

export async function rejectCandidates(batchId:string,ids:string[]):Promise<{rejected:number}>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/candidates/reject`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
  if(!response.ok)throw new Error('忽略候选失败');
  return response.json();
}

export async function loadIntegrityReport(batchId:string):Promise<IntegrityReport>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/integrity-report`);
  if(!response.ok)throw new Error('生成迁移报告失败');
  return response.json();
}

export async function downloadBackup():Promise<void>{
  const response=await apiFetch(`${API_BASE}/api/backups/export`);
  if(!response.ok)throw new Error('备份生成失败');
  const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
  const disposition=response.headers.get('Content-Disposition')||'';
  link.href=url;link.download=disposition.match(/filename="([^"]+)"/)?.[1]||'my-little-phone-v2-backup.json';
  document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
}

export async function previewRestore(file:File):Promise<RestorePreview>{
  const body=new FormData();body.append('file',file);
  const response=await apiFetch(`${API_BASE}/api/backups/restore-preview`,{method:'POST',body});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'备份检查失败');
  return response.json();
}

export async function confirmRestore(token:string):Promise<{restored:boolean;inserted:Record<string,number>}>{
  const response=await apiFetch(`${API_BASE}/api/backups/restore-confirm`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,mode:'merge'})});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'恢复失败');
  return response.json();
}

export async function createExtractionJob(batchId:string):Promise<ExtractionJob>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/extraction-jobs`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'创建精提取任务失败');
  return response.json();
}

export async function controlExtractionJob(batchId:string,jobId:string,action:'pause'|'resume'|'retry'):Promise<ExtractionJob>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/extraction-jobs/${jobId}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});
  if(!response.ok)throw new Error('任务操作失败');
  return response.json();
}

export async function runExtractionStep(batchId:string,jobId:string):Promise<{job:ExtractionJob;created:number;failed:number;complete:boolean}>{
  const response=await apiFetch(`${API_BASE}/api/history-imports/${batchId}/deepseek-candidates?max_conversations=3&job_id=${jobId}`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'精提取暂停');
  return response.json();
}

export async function startCall(direction:'incoming'|'outgoing'='outgoing'):Promise<CallRecord>{
  const response=await apiFetch(`${API_BASE}/api/calls`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({direction})});
  if(!response.ok)throw new Error('通话建立失败');
  return response.json();
}

export async function endCall(id:string,status:'answered'|'missed'|'declined'='answered'):Promise<CallRecord>{
  const response=await apiFetch(`${API_BASE}/api/calls/${id}/end`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  if(!response.ok)throw new Error('挂断失败');
  return response.json();
}

export async function loadCalls():Promise<CallRecord[]>{
  const response=await apiFetch(`${API_BASE}/api/calls`);
  if(!response.ok)throw new Error('读取通话记录失败');
  return response.json();
}

export async function answerCall(id:string):Promise<CallRecord>{
  const response=await apiFetch(`${API_BASE}/api/calls/${id}/answer`,{method:'POST'});
  if(!response.ok)throw new Error('接听失败');
  return response.json();
}
export async function openOutgoingCall(id:string):Promise<{assistant:{messageId:string;text:string};cached:boolean}>{
  const response=await apiFetch(`${API_BASE}/api/calls/${id}/opening`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'电话接通失败');
  return response.json();
}
export async function replyInCall(id:string,text:string,signal?:AbortSignal):Promise<{user:{messageId:string;text:string};assistant:{messageId:string;text:string}}>{
  const response=await apiFetch(`${API_BASE}/api/calls/${id}/reply`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'通话回复中断');
  return response.json();
}

export async function extractCallMemories(id:string):Promise<{created:number;items:Memory[];cached:boolean}>{
  const response=await apiFetch(`${API_BASE}/api/calls/${id}/memory-candidates`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'通话记忆整理失败');
  return response.json();
}
export async function extractRecentChatMemories():Promise<{created:number;items:Memory[];processed:number;waiting:number;reason?:string}>{
  const response=await apiFetch(`${API_BASE}/api/memories/extract-recent`,{method:'POST'});
  if(!response.ok)throw new Error((await response.json().catch(()=>null))?.detail||'最近聊天记忆整理失败');
  return response.json();
}

export interface CompanionSettings {enabled:boolean;allow_calls:boolean;dnd_enabled:boolean;dnd_start:string;dnd_end:string;timezone:string}
export async function loadCompanionSettings():Promise<CompanionSettings>{
  const response=await apiFetch(`${API_BASE}/api/companion/settings`);if(!response.ok)throw new Error('读取主动陪伴设置失败');return response.json();
}
export async function saveCompanionSettings(settings:CompanionSettings):Promise<CompanionSettings>{
  const response=await apiFetch(`${API_BASE}/api/companion/settings`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});if(!response.ok)throw new Error('保存主动陪伴设置失败');return response.json();
}
export interface ProactiveEvent{id:string;event_type:'message'|'call';status:string;reason:string;text:string;created_at:string;answered_at?:string}
export async function loadProactiveEvents():Promise<ProactiveEvent[]>{const response=await apiFetch(`${API_BASE}/api/companion/events`);if(!response.ok)throw new Error('读取主动陪伴动态失败');return response.json();}
export interface NotificationStatus{activeSubscriptions:number;counts:Record<string,number>;latest:{status:string;attempts:number;last_error?:string;created_at:string;updated_at:string}|null}
export async function loadNotificationStatus():Promise<NotificationStatus>{const response=await apiFetch(`${API_BASE}/api/notifications/status`);if(!response.ok)throw new Error('读取通知状态失败');return response.json();}
export async function retryFailedNotifications():Promise<{queued:number}>{const response=await apiFetch(`${API_BASE}/api/notifications/retry-failed`,{method:'POST'});if(!response.ok)throw new Error('通知重试失败');return response.json();}

function decodeApplicationKey(value:string):ArrayBuffer{
  const padded=(value+'='.repeat((4-value.length%4)%4)).replace(/-/g,'+').replace(/_/g,'/');
  return Uint8Array.from(atob(padded),character=>character.charCodeAt(0)).buffer as ArrayBuffer;
}

export async function subscribeToPush():Promise<void>{
  if(!('serviceWorker' in navigator)||!('PushManager' in window))throw new Error('当前浏览器不支持网页推送，请先把小手叽添加到主屏幕');
  const permission=await Notification.requestPermission();
  if(permission!=='granted')throw new Error('通知权限没有开启');
  const registration=await navigator.serviceWorker.ready;
  const keyResponse=await apiFetch(`${API_BASE}/api/notifications/vapid-public-key`);
  if(!keyResponse.ok)throw new Error((await keyResponse.json().catch(()=>null))?.detail||'推送服务尚未配置');
  const {publicKey}=await keyResponse.json();
  const current=await registration.pushManager.getSubscription();
  const subscription=current||await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:decodeApplicationKey(publicKey)});
  const response=await apiFetch(`${API_BASE}/api/notifications/subscribe`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(subscription.toJSON())});
  if(!response.ok)throw new Error('保存通知订阅失败');
}
