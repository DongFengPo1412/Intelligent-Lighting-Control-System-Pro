/* Shared Web/APK content contract. This does not certify gameplay or hardware. */
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,".."),web=path.join(root,"pc-agent-vision/web_app"),context={window:{}};
vm.createContext(context);
for(const name of ["arcade_b3_rules.js","arcade_game_guides.js"])
  vm.runInContext(fs.readFileSync(path.join(web,name),"utf8"),context,{filename:name});
const guides=context.window.ARCADE_GAME_GUIDES;
assert.equal(Object.keys(guides).length,100);
assert.equal(new Set(Object.values(guides).map(g=>g.help)).size,100);
for(let id=1;id<=100;id++) {
  assert.ok(guides[id]?.help.length>=30,`Missing actual play introduction: ${id}`);
  assert.ok(!guides[id].help.includes("按当前卡带"),`Generic placeholder: ${id}`);
}
assert.match(guides[33].help,/撞到墙壁/);
assert.match(guides[27].help,/A 推进，B 射击/);
assert.match(guides[41].help,/B 加速下落/);
const html=fs.readFileSync(path.join(web,"index.html"),"utf8");
assert.ok(html.indexOf('src="arcade_b3_rules.js"')<html.indexOf('src="arcade_game_guides.js"'));
assert.ok(html.indexOf('src="arcade_game_guides.js"')<html.indexOf('src="app.js'));
console.log("100 unique game introductions loaded in the actual Web/APK script order; Snake and action mappings checked.");
