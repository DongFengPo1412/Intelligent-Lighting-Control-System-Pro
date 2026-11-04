"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const {nativeExchange,nativeDeviceApi}=require("../pc-agent-vision/web_app/arcade_transport.js");
function device(){
  const sent=[],state={mode:17,brightness:20,volume:70,countdown_active:false,countdown_remaining:0};
  const exchange=async cmd=>{
    sent.push(cmd);
    if(cmd.cmd==="mode")state.mode=cmd.val;
    if(cmd.cmd==="brightness")state.brightness=cmd.val;
    if(cmd.cmd==="volume")state.volume=cmd.val;
    if(cmd.cmd==="countdown"){state.mode=25;state.countdown_active=true;state.countdown_remaining=cmd.seconds;}
    if(cmd.cmd==="stop_countdown"){state.countdown_active=false;state.countdown_remaining=0;}
    if(cmd.cmd==="pet")state.mode=17;
    return {status:"ok",...state,...(cmd.cmd==="frame"?{hex:"ab".repeat(768),frame_id:7}:{})};
  };return {sent,state,api:nativeDeviceApi(exchange)};
}
test("APK basic routes use paired commands and authoritative status/frame without PC",async()=>{
  const {api,sent}=device();
  await api("/api/mode",{mode:7});await api("/api/cmd",{cmd:"brightness",val:35});
  await api("/api/volume",{volume:60});await api("/api/cmd",{cmd:"countdown",seconds:60});
  let s=await api("/api/status",undefined,"GET");assert.equal(s.mode,25);assert.equal(s.countdown_remaining,60);
  assert.equal(s.wifi.last_command.brightness,35);assert.equal(s.volume,60);
  await api("/api/cmd",{cmd:"stop_countdown"});await api("/api/cmd",{cmd:"pet"});
  const f=await api("/api/pro/frame",undefined,"GET");assert.equal(f.pixels.length,1536);assert.equal(f.frame_source,"hardware_pwm");
  assert.equal(f.mode,17);assert.deepEqual(sent.slice(0,3),[{cmd:"mode",val:7},{cmd:"brightness",val:35},{cmd:"volume",val:60}]);
});
test("APK rejects unsupported commands, types, ranges and unknown fields before sending",async()=>{
  const {api,sent}=device();
  for(const mode of [18,25,32,-1,1.5,"7",true])await assert.rejects(api("/api/mode",{mode}));
  for(const val of [-1,61,1.2,"20",true])await assert.rejects(api("/api/cmd",{cmd:"brightness",val}));
  for(const seconds of [0,86401,2.5,"60"])await assert.rejects(api("/api/cmd",{cmd:"countdown",seconds}));
  for(const path of ["/api/chat","/api/pro/vision","/api/pro/music","/api/pro/memory"])await assert.rejects(api(path,{}));
  await assert.rejects(api("/api/mode",{mode:7,token:"injected"}));
  await assert.rejects(api("/api/cmd",{cmd:"pair"}));await assert.rejects(api("/api/cmd",{cmd:"mic",enable:true}));
  assert.equal(sent.length,0);
});
test("invalid/incomplete or unconfirmed state never produces successful basic control",async()=>{
  for(const reply of [{status:"ok"},{status:"error",mode:7},{status:"ok",mode:7,brightness:20,volume:70,countdown_active:false,countdown_remaining:0}]){
    const api=nativeDeviceApi(async()=>reply);await assert.rejects(api("/api/mode",{mode:1}));
  }
  const {api,state}=device();state.mode=32;
  assert.equal((await api("/api/status",undefined,"GET")).mode,32);
});
test("native bridge preserves device status while retaining correlated ACK and full-frame checks",async()=>{
  const b={sendUdpAsync:(raw,to,retries,id)=>globalThis.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id,status:"ok",mode:7,brightness:33,volume:65,countdown_active:false,countdown_remaining:0}))};
  const s=await nativeDeviceApi(nativeExchange(b))("/api/status",undefined,"GET");
  assert.equal(s.brightness,33);assert.equal(s.volume,65);assert.equal(s.countdown_active,false);
});
test("basic writes stay ordered and failed telemetry does not disable controls",async()=>{
  const base=device();let release;
  const api=nativeDeviceApi(cmd=>cmd.cmd==="frame"?new Promise((_,reject)=>release=reject):base.api("/api/mode",{mode:cmd.val}).then(r=>({...r,status:"ok"})));
  const read=api("/api/pro/frame",undefined,"GET").catch(e=>e.message);
  const result=await api("/api/mode",{mode:7});assert.equal(result.mode,7);
  release(Error("lost_frame"));assert.equal(await read,"lost_frame");
  await api("/api/mode",{mode:10});assert.deepEqual(base.sent.map(c=>c.val),[7,10]);
});
