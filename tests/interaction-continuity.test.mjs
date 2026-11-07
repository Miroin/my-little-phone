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

const rejectedSource=sourceBetween('function feedbackIssues','function currentInteractionGuide');
const guideSource=sourceBetween('function currentInteractionGuide','function promptSystem');
const guideData={responseFeedback:[{verdict:'dislike',scene:'冲突修复',userText:'你根本不像沈砚',yanText:'那你说说我哪里不像。'}]};
const currentInteractionGuide=Function('data','interactionScene',`${rejectedSource}${guideSource}; return currentInteractionGuide;`)(guideData,interactionScene);
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
assert.match(html,/x\.feedbackApproved\?\.08:\.18/,'历史样本必须达到相关度门槛，用户认可只能适度降低门槛');

console.log(`通过：${cases.length} 个固定场景、按轮上下文、记忆污染、规则注入、返回层级和滚动位置检查`);
