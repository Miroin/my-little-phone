import fs from 'node:fs';
import assert from 'node:assert/strict';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');

assert.match(html,/function recentCallContext\(limit=2,maxChars=5000\)/,'缺少最近通话上下文构造');
assert.match(html,/最近语音通话原文｜与文字聊天属于同一段关系/,'通话原文没有注入聊天提示词');
assert.match(html,/line\.role==='user'\?'陈钰：'/,'通话原文没有保留双方身份');
assert.match(html,/function storeCallRecord\(record/,'缺少统一通话记录入口');
assert.match(html,/if\(record\.status==='answered'\).*detectMemory/s,'已接通话没有参与记忆提取');
assert.match(html,/storeCallRecord\(\{[^}]*status:'missed'/s,'未接来电没有写入统一记录');
assert.match(html,/storeCallRecord\(\{[^}]*status:'declined'/s,'拒接来电没有写入统一记录');
assert.match(html,/endedAt:Date\.now\(\),seconds:n/,'已接通话没有保存结束时间和时长');
assert.match(html,/☎ '\+callStatusText\(record\)/,'聊天通话卡片没有区分通话状态');

console.log('通过：通话身份、时长、聊天事件、记忆提取和后续上下文检查');
