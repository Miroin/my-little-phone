import fs from 'node:fs';
import assert from 'node:assert/strict';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');

assert.match(html,/data-theme="luxury"/,'缺少高级感主题入口');
assert.match(html,/data-theme="y2k"/,'缺少 Y2K 主题入口');
assert.match(html,/const colors=\{luxury:/,'缺少高级感主题色令牌');
assert.match(html,/,y2k:\[/,'缺少 Y2K 主题色令牌');
assert.match(html,/document\.documentElement\.dataset\.theme=data\.settings\.theme\|\|'pink'/,'主题没有应用到页面根节点');
assert.match(html,/data\.settings\.customColors=\{\};\s*save\(\);\s*theme\(\);/,'主题切换没有沿用安全的外观配置流程');
assert.match(html,/切换只改变外观，不覆盖聊天、记忆、角色资料、世界书、相册、语音或密钥/,'界面缺少数据边界说明');
assert.match(html,/markActiveBeautyTheme\(\)/,'主题选择状态没有同步');

console.log('通过：高级感、Y2K、基础回退和主题数据边界检查');
