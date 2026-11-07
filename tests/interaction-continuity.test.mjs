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

console.log(`通过：${cases.length} 个固定场景、按轮上下文、记忆污染、规则注入、返回层级和滚动位置检查`);
