"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const {ArcadeTransport,nativeExchange}=require("../pc-agent-vision/web_app/arcade_transport.js");
const ok={status:"ok",game_status:{active:true,game_id:1,state:1}};
const turn=()=>new Promise(resolve=>setImmediate(resolve));

test("Mario right+jump keeps both bits and releasing A keeps right",async()=>{
  const sent=[];const t=new ArcadeTransport(async c=>{sent.push(c);return ok;});
  await t.call("/api/arcade",{action:"key",key:"right",down:true});
  await t.call("/api/arcade",{action:"key",key:"a",down:true});
  await t.call("/api/arcade",{action:"key",key:"a",down:false});
  assert.deepEqual(sent.map(c=>[c.down,c.pressed]),[[2,2],[18,16],[2,0]]);
  await t.call("/api/arcade",{action:"heartbeat"});
  assert.deepEqual(sent.at(-1),{cmd:"arcade",action:"input",down:2,pressed:0});
});
test("rapid taps retain all press edges in send order",async()=>{
  const sent=[];const t=new ArcadeTransport(async c=>{sent.push(c);return ok;});const pending=[];
  for(let i=0;i<20;i++) {
    pending.push(t.call("/api/arcade",{action:"key",key:"a",down:true}));
    pending.push(t.call("/api/arcade",{action:"key",key:"a",down:false}));
  }
  await Promise.all(pending);assert.equal(sent.length,40);
  assert.equal(sent.filter(c=>c.pressed===16).length,20);assert.equal(t.down,0);
});
test("NACK blocks queued input/heartbeat until explicit resume",async()=>{
  let fail=true;const sent=[];
  const t=new ArcadeTransport(async c=>{sent.push(c);if(fail)throw Error("offline");return ok;});
  const a=t.call("/api/arcade",{action:"key",key:"right",down:true});
  const b=t.call("/api/arcade",{action:"key",key:"a",down:true});
  await Promise.allSettled([a,b]);assert.equal(t.down,0);assert.equal(sent.length,1);
  await assert.rejects(t.call("/api/arcade",{action:"heartbeat"}));
  fail=false;await t.call("/api/arcade",{action:"resume"});
  await t.call("/api/arcade",{action:"key",key:"a",down:true});assert.equal(sent.at(-1).down,16);
});
test("switch discards stale input/replies and clears held keys",async()=>{
  let release;const sent=[];
  const t=new ArcadeTransport(c=>{sent.push(c);return sent.length===1?new Promise(r=>release=r):Promise.resolve(ok);});
  const old=t.call("/api/arcade",{action:"key",key:"right",down:true});
  const oldOutcome=old.catch(e=>e.message);await turn();
  const select=t.call("/api/arcade",{action:"select",game_id:33});
  release(ok);assert.equal(await oldOutcome,"stale_reply");await select;assert.equal(t.down,0);
});
test("background suspend explicitly releases then pauses",async()=>{
  const sent=[];const t=new ArcadeTransport(async c=>{sent.push(c);return ok;});
  await t.call("/api/arcade",{action:"key",key:"right",down:true});await t.suspend();
  assert.deepEqual(sent.slice(-2),[{cmd:"arcade",action:"input",down:0,pressed:0},{cmd:"arcade",action:"pause"}]);
  assert.equal(t.blocked,true);assert.equal(t.down,0);
});
test("native contract accepts action paths, validates IDs/status and full frames",async()=>{
  let seen;
  const bridge={sendUdpAsync:(raw,timeout,retries,id)=>{
    seen=JSON.parse(raw);const cmd=JSON.parse(seen.command);
    globalThis.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id,status:"ok",
      arcade:{game_id:9,state:0},...(cmd.cmd==="frame"?{pixels:"a".repeat(1536),frame_id:4}:{})}));
  }};
  const t=new ArcadeTransport(nativeExchange(bridge));
  const select=await t.call("/api/arcade/select",{game_id:9});assert.equal(select.game_status.game_id,9);assert.equal(select.source,"esp32_hardware");
  assert.equal(JSON.parse(seen.command).action,"select");
  const frame=await t.call("/api/arcade/frame");assert.equal(frame.hex.length,1536);assert.equal(frame.source,"hardware_pwm");
  const wrong={sendUdpAsync:(raw,to,r,id)=>globalThis.__amadeusUdpCallbacks[id](JSON.stringify({status:"ok",request_id:"wrong"}))};
  await assert.rejects(nativeExchange(wrong)({cmd:"status"},"test_wrong",{timeout:10,retries:0}),/编号/);
  const invalid={sendUdpAsync:(raw,to,r,id)=>globalThis.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id}))};
  await assert.rejects(nativeExchange(invalid)({cmd:"status"},"test_invalid",{timeout:10,retries:0}));
  const incomplete={sendUdpAsync:(raw,to,r,id)=>globalThis.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id,status:"ok",pixels:"ff"}))};
  await assert.rejects(nativeExchange(incomplete)({cmd:"frame"},"test_frame",{timeout:10,retries:0}),/不完整/);
  assert.equal(Object.keys(globalThis.__amadeusUdpCallbacks).length,0);
});
test("no synchronous bridge or implicit simulator fallback; validate actions/IDs",async()=>{
  await assert.rejects(nativeExchange({sendUdp:()=>"{}"})({cmd:"status"},"legacy",{timeout:10,retries:0}),/新版/);
  const t=new ArcadeTransport(async()=>{throw Error("must not send");});
  for(const game_id of [257,-255,1.5,"1",true])await assert.rejects(t.call("/api/arcade",{action:"select",game_id}));
  await assert.rejects(t.call("/api/arcade",{action:"unknown"}));
});
