/* Retry only explicit 401 rejections from the pre-handler auth middleware. */
"use strict";
(function(root) {
  function createPairedHttp({fetch,storage,prompt}) {
    let pairing=null, prompted=false;
    const token=()=>storage.getItem("kurisu_access_token")||"";
    async function exchange(path,options,signal) {
      return await fetch(path,{...options,signal,cache:"no-store"});
    }
    async function pair() {
      if(pairing)return pairing;
      if(prompted)throw Error("配对尚未成功，请在连接设置中重试");
      prompted=true;
      pairing=Promise.resolve().then(async()=>{
        const value=((await prompt())||"").trim();
        if(!value)throw Error("配对已取消");
        const abort=new AbortController(), timer=setTimeout(()=>abort.abort(),5000);
        try {
          const reply=await exchange("/api/pair",{method:"POST",headers:{Authorization:"Bearer "+value}},abort.signal);
          if(!reply.ok)throw Error("配对令牌无效或配对失败");
          storage.setItem("kurisu_access_token",value);
        } finally {
          clearTimeout(timer);
        }
      }).finally(()=>{pairing=null;});
      return pairing;
    }
    const headers=(options,value)=>({...options.headers,...(value?{Authorization:"Bearer "+value}:{})});
    async function request(path,options={},timeout=15000) {
      const used=token();
      const abort=new AbortController();
      const timer=timeout>0?setTimeout(()=>abort.abort(),timeout):null;
      try {
        let reply=await exchange(path,{...options,headers:headers(options,used)},abort.signal);
        if(reply.status===401 && path!=="/api/pair") {
          // An explicit rejection means no business handler ran. A concurrent
          // request may already have paired while this rejection was in flight.
          if(!token() || token()===used)await pair();
          reply=await exchange(path,{...options,headers:headers(options,token())},abort.signal);
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
            const probeAbort=new AbortController(), probeTimer=setTimeout(()=>probeAbort.abort(),1500);
            try {
              const reply=await exchange("/api/status",{method:"GET",headers:headers({},token())},probeAbort.signal);
              if(reply.ok)observed=await reply.json();
            } finally {
              clearTimeout(probeTimer);
            }
          } catch(_) {}
          const uncertain=Error("等待回执失败；操作可能已执行，已尝试查询状态，请确认后再操作");
          uncertain.observedStatus=observed;
          throw uncertain;
        }
        throw error;
      } finally {
        if(timer)clearTimeout(timer);
      }
    }
    request.resetPairing=()=>{if(!pairing)prompted=false;};
    return request;
  }
  root.createPairedHttp=createPairedHttp;
  if(typeof module!=="undefined")module.exports={createPairedHttp};
})(typeof window!=="undefined"?window:globalThis);
