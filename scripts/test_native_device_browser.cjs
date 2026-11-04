/* Production file: UI with an explicitly fake native boundary, no device traffic. */
"use strict";
const fs=require("node:fs"),path=require("node:path"),cp=require("node:child_process"),net=require("node:net");
const {pathToFileURL}=require("node:url");
const {values}=require("node:util").parseArgs({options:{"work-dir":{type:"string"},chrome:{type:"string"}}});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function main(){
  const root=path.resolve(__dirname,".."),work=path.resolve(values["work-dir"]||root);
  if(work===root||work.startsWith(root+path.sep))throw Error("Supply an external --work-dir");
  fs.mkdirSync(work,{recursive:true});
  const probe=net.createServer();await new Promise(r=>probe.listen(0,"127.0.0.1",r));const port=probe.address().port;await new Promise(r=>probe.close(r));
  const chrome=cp.spawn(values.chrome||"C:/Program Files/Google/Chrome/Application/chrome.exe",["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--remote-debugging-port="+port,"--user-data-dir="+path.join(work,"profile"),"about:blank"],{stdio:"ignore"});
  let socket;
  try{
    let tabs;for(let n=0;n<80;n++){try{tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();break;}catch(_){await sleep(100);}}
    if(!tabs)throw Error("No Chromium debugging endpoint");
    socket=new WebSocket(tabs.find(t=>t.type==="page").webSocketDebuggerUrl);await new Promise(r=>socket.addEventListener("open",r,{once:true}));
    let seq=0;const pending=new Map(),exceptions=[];
    socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==="Runtime.exceptionThrown")exceptions.push(m.params);};
    const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
    const evaluate=async expression=>{if(expression.includes("const "))expression=`{${expression}}`;const r=await call("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
    const until=async expression=>{for(let n=0;n<100;n++){if(await evaluate(expression))return;await sleep(100);}throw Error("Timeout: "+expression+" "+await evaluate('JSON.stringify({seen:window.__seen,toast:document.getElementById("toast")?.textContent})'));};
    await call("Runtime.enable");await call("Page.enable");
    await call("Page.addScriptToEvaluateOnNewDocument",{source:`
      window.__seen=[];window.__device={mode:17,brightness:20,volume:70,countdown_active:false,countdown_remaining:0};
      window.AmadeusNative={sendUdpAsync:(wire,timeout,retries,id)=>{
        const c=JSON.parse(JSON.parse(wire).command),d=window.__device;window.__seen.push(c);
        if(c.cmd==='frame'&&window.__dropFrames){window.__amadeusUdpCallbacks[id](JSON.stringify({request_id:id,status:'error',error:'dropped_frame'}));return;}
        if(c.cmd==='mode')d.mode=c.val;if(c.cmd==='brightness')d.brightness=c.val;
        if(c.cmd==='volume'&&!window.__mismatch)d.volume=c.val;
        if(c.cmd==='countdown'){d.mode=25;d.countdown_active=true;d.countdown_remaining=c.seconds;}
        if(c.cmd==='stop_countdown'){d.countdown_active=false;d.countdown_remaining=0;}
        setTimeout(()=>window.__amadeusUdpCallbacks[id]?.(JSON.stringify({status:'ok',request_id:id,...d,...(c.cmd==='frame'?{pixels:'101010'.repeat(256),frame_id:1,frame_source:'hardware_pwm'}:{})})),10);
      }};`});
    await call("Page.navigate",{url:pathToFileURL(path.join(root,"pc-agent-vision/web_app/index.html")).href});
    await until('document.getElementById("connectionText")?.textContent==="设备已连接"');
    await evaluate('document.querySelector(\'[data-page="lights"]\').click()');
    await evaluate('document.querySelector(\'[data-mode="7"]\').click()');await until('window.__device.mode===7');
    await evaluate('const b=document.getElementById("brightness");b.value=30;b.dispatchEvent(new Event("change"))');await until('window.__device.brightness===30');
    await evaluate('const v=document.getElementById("volume");v.value=45;v.dispatchEvent(new Event("change"))');await until('window.__device.volume===45');
    await evaluate('document.getElementById("seconds").value=60;document.getElementById("timerForm").dispatchEvent(new Event("submit",{cancelable:true}))');await until('window.__device.countdown_active&&window.__device.countdown_remaining===60');
    await evaluate('document.getElementById("stopTimer").click()');await until('!window.__device.countdown_active');
    await until('document.getElementById("frameTag").textContent==="实时回读"');
    await evaluate('window.__dropFrames=true');await sleep(1700);
    await evaluate('const b=document.getElementById("brightness");b.value=31;b.dispatchEvent(new Event("change"))');await until('window.__device.brightness===31');
    await until('document.getElementById("connectionText").textContent==="设备已连接"');
    await evaluate('window.__mismatch=true;const v=document.getElementById("volume");v.value=60;v.dispatchEvent(new Event("change"))');await until('document.getElementById("toast").textContent.includes("未确认目标状态")');
    if(exceptions.length)throw Error(JSON.stringify(exceptions));
    const result=await evaluate('({commands:window.__seen,state:window.__device,source:document.getElementById("status").textContent,chatDisabled:document.getElementById("sendChat").disabled})');
    if(!result.chatDisabled)throw Error("PC-only chat should be unavailable in direct mode");
    fs.writeFileSync(path.join(work,"result.json"),JSON.stringify(result,null,2));
    console.log("Production file UI passed: basic controls, countdown/stop, frame readback, telemetry failure isolation and unconfirmed ACK rejection. Native boundary FAKE; physical phone/ESP32 NOT_TESTED.");
  }finally{socket?.close();chrome.kill();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
