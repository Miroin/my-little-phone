import fs from 'node:fs';
import assert from 'node:assert/strict';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');

assert.match(html,/id="themePackImport"/,'缺少主题包导入入口');
assert.match(html,/id="themePackLibrary"/,'缺少主题库');
assert.match(html,/my-little-phone-theme-v1/,'缺少主题包格式校验');
assert.match(html,/async function importThemePack/,'缺少主题包保存逻辑');
assert.match(html,/kind:'theme-wallpaper'/,'主题壁纸没有存入媒体库');
assert.match(html,/document\.documentElement\.dataset\.theme=data\.settings\.theme\|\|'pink'/,'主题没有应用到页面根节点');
assert.match(html,/document\.documentElement\.dataset\.packStyle=pack\?\.style\|\|''/,'主题包样式没有应用到页面根节点');
assert.match(html,/(?:切换|应用)主题?只改变外观，不覆盖聊天、记忆、角色资料、世界书、相册、语音或密钥/,'界面缺少数据边界说明');
assert.match(html,/markActiveBeautyTheme\(\)/,'主题选择状态没有同步');

console.log('通过：主题包导入、设备保存、应用、基础回退和数据边界检查');
