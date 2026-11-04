/* Real Chromium UI integration against an explicitly simulated local service.
   No installed Android or physical LED acceptance is implied. Node >= 22. */
"use strict";
const fs=require("node:fs"),path=require("node:path"),cp=require("node:child_process"),net=require("node:net");
const {parseArgs}=require("node:util");
const {values}=parseArgs({options:{url:{type:"string"},"work-dir":{type:"string"},chrome:{type:"string"}}});
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function main() {
  if(!values.url||!values["work-dir"])throw Error("Supply --url and --work-dir (outside repository)");
  const base=values.url.replace(/\/$/,""),work=path.resolve(values["work-dir"]),repo=path.resolve(__dirname,"..");
  if(work===repo||work.startsWith(repo+path.sep))throw Error("Use an external task cache");
  const status=await(await fetch(base+"/api/status")).json();
  if(status.simulated!==true)throw Error("Refusing a service not explicitly marked simulated");
  fs.mkdirSync(work,{recursive:true});
  const probe=net.createServer();await new Promise(resolve=>probe.listen(0,"127.0.0.1",resolve));
  const port=probe.address().port;await new Promise(resolve=>probe.close(resolve));
  const chrome=cp.spawn(values.chrome||"C:/Program Files/Google/Chrome/Application/chrome.exe",[
    "--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
    "--remote-debugging-port="+port,"--user-data-dir="+path.join(work,"profile"),"about:blank"
  ],{stdio:"ignore"});
  let socket;
  try {
    let tabs;
    for(let i=0;i<60;i++) {try {tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();break;}catch(_){await sleep(100);}}
    if(!tabs)throw Error("Chromium debugging endpoint unavailable");
    socket=new WebSocket(tabs.find(tab=>tab.type==="page").webSocketDebuggerUrl);
    await new Promise(resolve=>socket.addEventListener("open",resolve,{once:true}));
    let sequence=0;const pending=new Map(),exceptions=[];
    socket.onmessage=event=>{
      const message=JSON.parse(event.data);
      if(message.id) {
        const handler=pending.get(message.id);pending.delete(message.id);
        message.error?handler.reject(Error(JSON.stringify(message.error))):handler.resolve(message.result);
      } else if(message.method==="Runtime.exceptionThrown")exceptions.push(message.params);
    };
    const call=(method,params={})=>new Promise((resolve,reject)=>{
      const id=++sequence;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));
    });
    const evaluate=async expression=>{
      const reply=await call("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
      if(reply.exceptionDetails)throw Error(JSON.stringify(reply.exceptionDetails));
      return reply.result.value;
    };
    const until=async expression=>{
      for(let i=0;i<80;i++){if(await evaluate(expression))return;await sleep(100);}
      const debug=await evaluate('({calls:window.__calls?.slice(-12),replies:window.__replies?.slice(-3),label:document.getElementById("pongAiToggleBtn").textContent})');
      fs.writeFileSync(path.join(work,"failure.json"),JSON.stringify({expression,debug,exceptions},null,2));
      throw Error("UI timeout: "+expression+" "+JSON.stringify(debug));
    };
    await call("Runtime.enable");await call("Page.enable");
    await call("Network.enable");await call("Network.setCacheDisabled",{cacheDisabled:true});
    await call("Emulation.setDeviceMetricsOverride",{width:430,height:932,deviceScaleFactor:1,mobile:true});
    await call("Emulation.setTouchEmulationEnabled",{enabled:true,maxTouchPoints:5});
    await call("Page.navigate",{url:base+"/"});
    await until('typeof ArcadeTransport!=="undefined"&&document.querySelectorAll("[data-available]").length===100');
    await evaluate(`window.__calls=[];window.__replies=[];window.__fetch=window.fetch;window.fetch=(url,options)=>{
      try{if(url==="/api/arcade")window.__calls.push(JSON.parse(options.body));}catch(_){}
      return window.__fetch(url,options).then(reply=>{if(url==="/api/arcade")reply.clone().json().then(v=>window.__replies.push(v));return reply;});
    };document.querySelector('[data-arcade-id="020"]').click()`);
    await until('document.getElementById("pongAiToggleBtn").textContent.includes("单人 AI")');
    await evaluate('document.getElementById("marioStartBtn").click()');
    await until('document.getElementById("marioStateTag").textContent.includes("PLAYING")');
    await evaluate('document.getElementById("pongAiToggleBtn").click()');
    await until('document.getElementById("pongAiToggleBtn").textContent.includes("本地双人")');
    // Allow ordinary frame polling to run: it must not hide the arcade panel.
    await sleep(1200);
    await evaluate('document.getElementById("arcadeVersusStage").scrollIntoView({block:"center",behavior:"instant"})');
    await sleep(150);
    const points=await evaluate(`["pongP1Up","pongP2Down"].map((id,i)=>{
      const r=document.getElementById(id).getBoundingClientRect();
      return {id:i+1,x:r.x+r.width/2,y:r.y+r.height/2,radiusX:1,radiusY:1,force:1};
    })`);
    if(points.some(p=>p.x<=0||p.y<70||p.y>850))throw Error("Controls hidden or outside viewport: "+JSON.stringify(points));
    await call("Input.dispatchTouchEvent",{type:"touchStart",touchPoints:points});
    await until('window.__calls.some(c=>c.action==="input"&&c.down===36)');
    // CDP touchEnd lists the contacts ending, rather than the ones remaining.
    await call("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:[points[1]]});
    await until('window.__calls.some(c=>c.action==="input"&&c.down===4&&c.pressed===0)');
    await call("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:[]});
    await until('window.__calls.filter(c=>c.action==="input").at(-1)?.down===0');
    const result=await evaluate(`({registered:ArcadeTransport.registeredIds.length,
      planned:document.querySelectorAll("[data-available=false]").length,
      label:document.getElementById("pongAiToggleBtn").textContent,
      visible:!document.getElementById("page-interaction").hidden,calls:window.__calls})`);
    if(!result.visible||result.registered+result.planned!==100)throw Error("Incorrect catalogue/page state");
    const png=await call("Page.captureScreenshot",{format:"png"});
    fs.writeFileSync(path.join(work,"pong.png"),Buffer.from(png.data,"base64"));
    await evaluate('document.getElementById("btnArcade017").click()');
    await until('document.getElementById("marioStateTag").textContent.includes("TITLE")&&!document.getElementById("arcadeDifficulty").disabled');
    await evaluate(`document.getElementById("arcadeDifficulty").value="2";
      document.getElementById("arcadeSoundVolume").value="18";
      document.getElementById("arcadeSoundEnabled").checked=true;
      document.getElementById("arcadeDifficulty").dispatchEvent(new Event("input"));
      document.getElementById("arcadeApplySettings").click()`);
    await until('window.__replies.some(r=>r.game_status?.game_id===17&&r.game_status.difficulty===2&&r.game_status.sound_volume===18)');
    const configuration=await evaluate('(async()=>await(await fetch("/api/arcade",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"status"})})).json())()');
    if(configuration.game_status.difficulty!==2||configuration.game_status.sound_volume!==18||!configuration.game_status.sound_enabled)throw Error("Unconfirmed configuration");
    await evaluate('document.getElementById("arcadeApplySettings").scrollIntoView({block:"center",behavior:"instant"})');
    const settingsPng=await call("Page.captureScreenshot",{format:"png"});
    fs.writeFileSync(path.join(work,"settings.png"),Buffer.from(settingsPng.data,"base64"));
    await evaluate('document.getElementById("marioStartBtn").click()');
    await until('document.getElementById("marioStateTag").textContent.includes("PLAYING")');
    if(!await evaluate('document.getElementById("arcadeDifficulty").disabled'))throw Error("Difficulty was editable during a round");
    fs.writeFileSync(path.join(work,"result.json"),JSON.stringify({result,configuration,exceptions},null,2));
    if(exceptions.length)throw Error(JSON.stringify(exceptions));
    console.log(`Chromium UI passed: ${result.registered} registered/${result.planned} planned; Pong two-touch masks 36->4->0; authoritative rhythm Hard/volume18 settings, in-round difficulty locked. Physical hardware NOT_TESTED.`);
  } finally {if(socket)socket.close();chrome.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
