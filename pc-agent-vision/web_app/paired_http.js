/* Retry only explicit 401 rejections from the pre-handler auth middleware. */
"use strict";
(function(root) {
  function createPairedHttp({fetch,storage,prompt}) {
    let pairing=null, prompted=false;
    const token=()=>storage.getItem("kurisu_access_token")||"";
    async function exchange(path,options,timeout) {
      const abort=new AbortController(), timer=setTimeout(()=>abort.abort(),timeout);
      try { return await fetch(path,{...options,signal:abort.signal,cache:"no-store"}); }
      finally {clearTimeout(timer);}
    }
    async function pair() {
      if(pairing)return pairing;
      if(prompted)throw Error("配对尚未成功，请在连接设置中重试");
      prompted=true;
      pairing=Promise.resolve().then(async()=>{
        const value=((await prompt())||"").trim();
        if(!value)throw Error("配对已取消");
        const reply=await exchange("/api/pair",{method:"POST",headers:{Authorization:"Bearer "+value}},5000);
        if(!reply.ok)throw Error("配对令牌无效或配对失败");
        storage.setItem("kurisu_access_token",value);
      }).finally(()=>{pairing=null;});
      return pairing;
    }
    const headers=(options,value)=>({...options.headers,...(value?{Authorization:"Bearer "+value}:{})});
    async function request(path,options={},timeout=15000) {
      const used=token();
      try {
        let reply=await exchange(path,{...options,headers:headers(options,used)},timeout);
        if(reply.status===401 && path!=="/api/pair") {
          // An explicit rejection means no business handler ran. A concurrent
          // request may already have paired while this rejection was in flight.
          if(!token() || token()===used)await pair();
          reply=await exchange(path,{...options,headers:headers(options,token())},timeout);
        }
        const body=await reply.json();
        if(!reply.ok || body.status==="error")throw Error(body.error||body.message||`请求失败 (${reply.status})`);
        return body;
      } catch(error) {
        if(error.name==="AbortError" || error instanceof TypeError) {
          if((options.method||"GET")==="GET")throw Error("连接超时或中断，请检查电脑服务");
          // No automatic mutation retry after an uncertain transport result.
          // Read status first, and leave any further action to the user.
          let observed;
          try {
            const reply=await exchange("/api/status",{method:"GET",headers:headers({},token())},1500);
            if(reply.ok)observed=await reply.json();
          } catch(_) {}
          const uncertain=Error("等待回执失败；操作可能已执行，已尝试查询状态，请确认后再操作");
          uncertain.observedStatus=observed;
          throw uncertain;
        }
        throw error;
      }
    }
    request.resetPairing=()=>{if(!pairing)prompted=false;};
    return request;
  }
  root.createPairedHttp=createPairedHttp;
  if(typeof module!=="undefined")module.exports={createPairedHttp};
})(typeof window!=="undefined"?window:globalThis);
