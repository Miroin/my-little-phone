import {FormEvent,useEffect,useState} from 'react';
import {loadMessages,sendMessage} from './api';
import type {Message} from './types';

type Page='chat'|'calls'|'memories'|'settings';

export function App(){
  const [page,setPage]=useState<Page>('chat');
  const [messages,setMessages]=useState<Message[]>([]);
  const [input,setInput]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');

  useEffect(()=>{loadMessages().then(setMessages).catch(()=>setError('后端尚未启动，界面可以继续预览。'));},[]);

  async function submit(event:FormEvent){
    event.preventDefault();const text=input.trim();if(!text||busy)return;setBusy(true);setError('');setInput('');
    try{const result=await sendMessage(text);setMessages(current=>[...current,result.user,result.assistant]);}
    catch(reason){setInput(text);setError(reason instanceof Error?reason.message:'发送失败');}
    finally{setBusy(false);}
  }

  return <main className="phone-shell">
    <header><div><strong>沈砚</strong><small>关系与记忆连续</small></div><span className="status">● 在线</span></header>
    {page==='chat'&&<section className="chat-page">
      <div className="messages">{messages.length?messages.map(message=><article key={message.id} className={message.speaker==='user'?'mine':''}>{message.text}</article>):<p className="empty">聊天、通话和记忆会从同一个后端读取。</p>}</div>
      {error&&<p className="error">{error}</p>}
      <form onSubmit={submit}><input value={input} onChange={event=>setInput(event.target.value)} placeholder="说点什么…"/><button disabled={busy}>{busy?'回复中':'发送'}</button></form>
    </section>}
    {page==='calls'&&<section className="placeholder"><h2>实时通话</h2><p>下一阶段接入流式语音、打断、来电记录和通话记忆。</p></section>}
    {page==='memories'&&<section className="placeholder"><h2>多层记忆</h2><p>人格、关系、用户、事件与反馈分层保存并按当前话题检索。</p></section>}
    {page==='settings'&&<section className="placeholder"><h2>设置</h2><p>模型与语音密钥只保存在服务端。</p></section>}
    <nav>{(['chat','calls','memories','settings'] as Page[]).map(item=><button key={item} className={page===item?'active':''} onClick={()=>setPage(item)}>{({chat:'聊天',calls:'通话',memories:'记忆',settings:'设置'} as const)[item]}</button>)}</nav>
  </main>;
}
