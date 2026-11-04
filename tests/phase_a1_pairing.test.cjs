"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const {createPairedHttp}=require("../pc-agent-vision/web_app/paired_http.js");
const reply=(status,body={status:"ok"})=>({status,ok:status>=200&&status<300,json:async()=>body});
function fixture(fetch) {
  let value="",prompts=0;
  const api=createPairedHttp({fetch,storage:{getItem:()=>value,setItem:(k,v)=>value=v},prompt:()=>{prompts++;return "a".repeat(43);}});
  return {api,prompts:()=>prompts};
}
test("concurrent explicit 401s pair once and retry previously rejected operations once",async()=>{
  let paired=false,pairs=0,mutations=0;
  const f=fixture(async(path,options)=>{
    if(path==="/api/pair"){pairs++;paired=true;return reply(200);}
    if(!paired || !options.headers.Authorization)return reply(401,{error:"pairing_required"});
    mutations++;return reply(200);
  });
  await Promise.all([f.api('/api/control',{method:'POST',body:'{}'}),f.api('/api/control',{method:'POST',body:'{}'})]);
  assert.equal(f.prompts(),1);assert.equal(pairs,1);assert.equal(mutations,2);
});
test("wrong token never retries the original handler or starts an endless prompt loop",async()=>{
  const paths=[];const f=fixture(async p=>{paths.push(p);return reply(401,{error:'unauthorized'});});
  await assert.rejects(f.api('/api/control',{method:'POST'}),/令牌/);
  await assert.rejects(f.api('/api/control',{method:'POST'}));
  assert.equal(f.prompts(),1);assert.equal(paths.filter(p=>p==='/api/pair').length,1);
});
test("uncertain side effect is never retried; status is queried instead",async()=>{
  const paths=[];const f=fixture(async p=>{paths.push(p);if(p==='/api/status')return reply(200,{mode:32});const e=Error('lost');e.name='AbortError';throw e;});
  await assert.rejects(f.api('/api/control',{method:'POST'}),e=>e.observedStatus.mode===32);
  assert.deepEqual(paths,['/api/control','/api/status']);assert.equal(f.prompts(),0);
});
test("business NACK is not mistaken for a pairing challenge",async()=>{
  const f=fixture(async()=>reply(503,{status:'error',error:'device_offline'}));
  await assert.rejects(f.api('/api/control',{method:'POST'}),/device_offline/);assert.equal(f.prompts(),0);
});
