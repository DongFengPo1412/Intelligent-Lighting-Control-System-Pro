"use strict";
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {DeviceHealth,nativeExchange}=require('../pc-agent-vision/web_app/arcade_transport.js');
test('old Mario URLs redirect to the same formal card on both HTTP and APK file paths',()=>{
  const vm=require('node:vm'),fs=require('node:fs');
  const script=fs.readFileSync(require('node:path').join(__dirname,'../pc-agent-vision/web_app/pro.js'),'utf8');
  for(const url of ['http://127.0.0.1:8081/mario_controller.html','file:///android_asset/www/mario_controller.html','file:///android_asset/www/pro.html#mario']) {
    const at=new URL(url);let redirect;
    vm.runInNewContext(script,{location:{pathname:at.pathname,hash:at.hash,replace:value=>redirect=new URL(value,at).href}});
    assert.ok(redirect.endsWith('/index.html#mario'),redirect);
  }
});
test('only consecutive control failures can mark a known device offline; recovery is explicit health',()=>{
  const h=new DeviceHealth(),ok={is_connected:true,simulated:false};
  assert.equal(h.observe(ok,1000),ok);
  assert.equal(h.observe(null,5000).control_retrying,true);
  assert.equal(h.observe({is_connected:false},9000).is_connected,true);
  assert.equal(h.observe({is_connected:false},13000).is_connected,false);
  assert.equal(h.observe(ok,15000).is_connected,true);
  assert.equal(h.failures,0);
});
test('compact native frames preserve all 768 RGB bytes and require exact encoding',async()=>{
  const data=Buffer.from(Array.from({length:768},(_,i)=>i%256));let command;
  const bridge={sendUdpAsync:(raw,to,retries,id)=>{
    command=JSON.parse(JSON.parse(raw).command);
    globalThis.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id,status:'ok',mode:32,pixels_b64:data.toString('base64')}));
  }};
  const r=await nativeExchange(bridge)({cmd:'frame'},'test_compact',{timeout:450,retries:0});
  assert.equal(command.encoding,'base64');assert.equal(r.pixels,data.toString('hex'));
  bridge.sendUdpAsync=(_,to,retries,id)=>globalThis.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id,status:'ok',pixels_b64:'A'.repeat(1023)+'!'}));
  await assert.rejects(nativeExchange(bridge)({cmd:'frame'},'bad_frame',{timeout:450,retries:0}),/不完整/);
});
