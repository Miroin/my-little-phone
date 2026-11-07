import assert from 'node:assert/strict';
import fs from 'node:fs';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
const cases=JSON.parse(fs.readFileSync(new URL('./interaction-cases.json',import.meta.url),'utf8'));

function sourceBetween(start,end){
  const from=html.indexOf(start),to=html.indexOf(end,from);
  assert.ok(from>=0&&to>from,`找不到源码边界：${start}`);
  return html.slice(from,to);
}

const sceneSource=sourceBetween('function interactionScene','function interactionWords');
const interactionScene=Function(`${sceneSource}; return interactionScene;`)();
for(const item of cases)assert.equal(interactionScene(item.input),item.scene,`场景 ${item.id} 分类错误`);

const datasetSource=sourceBetween("const SHENYAN_DATASET_VERSION",'function interactionScene');
const dataset=Function(`${datasetSource}; return {SHENYAN_DATASET_VERSION,SHENYAN_DECISIONS,SHENYAN_CURATED_SAMPLES};`)();
assert.equal(dataset.SHENYAN_DATASET_VERSION,'1.0','互动判断数据集版本错误');
assert.equal(dataset.SHENYAN_CURATED_SAMPLES.length,18,'整理版互动样本数量错误');
assert.ok(dataset.SHENYAN_CURATED_SAMPLES.every(x=>x.sourceType==='reconstructed'),'重写样本必须明确标记，不能冒充历史原话');
assert.deepEqual(dataset.SHENYAN_DECISIONS['情绪支持'].priority,['回应具体感受','留下来陪她','等她主动决定要不要讨论办法'],'情绪支持必须先陪伴再讨论办法');

const rejectedSource=sourceBetween('function feedbackIssues','function currentInteractionGuide');
const guideSource=sourceBetween('function currentInteractionGuide','function promptSystem');
const guideData={responseFeedback:[{verdict:'dislike',scene:'冲突修复',userText:'你根本不像沈砚',yanText:'那你说说我哪里不像。'}]};
const currentInteractionGuide=Function('data','interactionScene','SHENYAN_DECISIONS',`${rejectedSource}${guideSource}; return currentInteractionGuide;`)(guideData,interactionScene,dataset.SHENYAN_DECISIONS);
assert.match(currentInteractionGuide('我想要亲亲，补偿我'),/亲密本身/,'亲密请求必须得到当下的亲密回应');
const repairGuide=currentInteractionGuide('你根本不像沈砚');
assert.match(repairGuide,/回避主动修复/,'相同场景的负面反馈必须抽象成问题类型');
assert.doesNotMatch(repairGuide,/那你说说我哪里不像/,'负面回复原文不能再次注入模型');

const contextSource=sourceBetween('function recentConversationMessages','const lastMsgs');
const messages=[
  {role:'user',text:'第一轮'},
  {role:'assistant',text:'第一句'},
  {role:'assistant',text:'第二句'},
  {role:'user',text:'第二轮'},
  {role:'assistant',text:'第三句'},
  {role:'assistant',text:'第四句'}
];
const recentConversationMessages=Function('data',`${contextSource}; return recentConversationMessages;`)({messages,settings:{context:2}});
assert.deepEqual(recentConversationMessages(2).map(x=>x.text),messages.map(x=>x.text),'上下文必须按用户轮次保留，不能按气泡截断');

assert.match(html,/if\(source!=='user'\)return \[\];/,'模型回复不应自动写入长期事实');
assert.match(html,/filter\(x=>x\.m\.pinned\|\|x\.matches>0\)/,'无关键词命中的普通记忆不应注入');
assert.doesNotMatch(sourceBetween('function attachRelationshipRule','function memoryClean'),/role!=='user'/,'互动规则不应再追加到用户原话');
assert.match(html,/function goBack\(\)/,'页面必须有上一级返回栈');
assert.match(html,/\.back\[data-home\],\.back\[data-go\]/,'所有左上角返回键必须使用上一级返回');
assert.match(html,/chat\(\{preserveScroll:true\}\)/,'消息工具操作必须保留当前阅读位置');
assert.match(html,/feedbackIssues/,'负面反馈必须归纳为问题类型');
assert.match(html,/x\.feedbackApproved\?\.08:x\.curated\?\.12:\.18/,'历史、认可和整理版样本必须使用不同相关度门槛');
assert.match(html,/sourceType=historical_exact 才是历史原话/,'提示词必须区分历史原话与重写参考');

const voiceParserSource=sourceBetween('function parseVoiceDirective','async function refreshVoiceUi');
const parseVoiceDirective=Function(`${voiceParserSource}; return parseVoiceDirective;`)();
for(const marker of ['[[voice]]你好','[voice]你好','【voice】你好','［VOICE］ 你好']){
  const parsed=parseVoiceDirective(marker);assert.equal(parsed.requested,true,`未识别语音标记：${marker}`);assert.equal(parsed.text,'你好','语音标记不应显示在正文');
}
assert.match(html,/for\(const message of created\)if\(message\.voiceRequested\)generateVoiceForMessage/,'主动语音必须实际生成音频');
assert.match(html,/callHandsFree=Boolean\(window\.SpeechRecognition\|\|window\.webkitSpeechRecognition\)/,'接通后应默认进入自动接话模式');
assert.match(html,/已打断，现在听你说/,'通话中点击麦克风必须可以打断回复');

console.log(`通过：${cases.length} 个固定场景、按轮上下文、记忆污染、规则注入、返回层级和滚动位置检查`);
