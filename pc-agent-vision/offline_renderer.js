'use strict';
// Node worker for real C++ engines compiled to WASM. No devices or networking.
const fs=require('fs'),readline=require('readline');
async function main(){
 const module=await WebAssembly.compile(fs.readFileSync(process.argv[2]));
 let memory;
 const round=x=>x<0?-Math.round(-x):Math.round(x);
 const functions={sinf:Math.sin,cosf:Math.cos,expf:Math.exp,powf:Math.pow,sqrtf:Math.sqrt,fabsf:Math.abs,
  fmod:(x,y)=>x%y,fmodf:(x,y)=>x%y,fminf:(x,y)=>Number.isNaN(x)?y:Number.isNaN(y)?x:Math.min(x,y),
  fmaxf:(x,y)=>Number.isNaN(x)?y:Number.isNaN(y)?x:Math.max(x,y),floorf:Math.floor,ceilf:Math.ceil,roundf:round,lroundf:round,
  memmove:(d,s,n)=>{new Uint8Array(memory.buffer).copyWithin(d,s,s+n);return d;}};
 const env={};for(const item of WebAssembly.Module.imports(module)){if(!functions[item.name])throw Error(`Unsupported C++ import: ${item.name}`);env[item.name]=functions[item.name];}
 const instance=await WebAssembly.instantiate(module,{env});const e=instance.exports;memory=e.memory;e.__wasm_call_ctors();
 if(process.argv.includes('--test')){const failed=e.run_tests();console.log(JSON.stringify({cases:14,failedCase:failed}));process.exitCode=failed;return;}
 let last=1000,currentMode=17;
 const advance=(mode,now)=>{for(let t=Math.max(last+16,now-2000);t<now;t+=16)e.render(mode,t);last=now;currentMode=mode;return e.render(mode,now);};
 for await(const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})){
  try{const r=JSON.parse(line);if(r.command){advance(currentMode,r.now);e.set_clock(r.now);const c=r.command,v=(kind,a=0,b=0,d=0,f=0,g=0)=>e.input(kind,a,b,d,f,g);
   if(c.cmd==='track')v(1,c.x,c.y,+c.visible,c.conf===undefined?1:c.conf);
   if(c.cmd==='track_cal'){v(11,c.x0||0,c.y0||0,c.x1===undefined?1:c.x1,c.y1===undefined?1:c.y1);v(12,+c.invert_x,+c.invert_y);}
   if(c.cmd==='hand')v(2,c.x,c.y,c.z,+c.pinch,+c.visible);
   if(c.cmd==='mir')v(3,c.energy,c.flux,+c.onset,c.tempo,c.phase||0);
   if(c.cmd==='canvas')for(let i=0;i<256;i++)v(4,i,...[0,2,4].map(k=>parseInt(c.hex.slice(i*6+k,i*6+k+2),16)));
   if(c.cmd==='pet_context')v(7,c.hour,c.gaze,+c.present,+c.tired);
   if(c.cmd==='difficulty')v(8,c.level,+c.adaptive);
   if(c.cmd==='performance')v(9,c.reaction_ms,c.frustration,+c.success);
   if(c.cmd==='celebrate')v(10);
   if(c.cmd==='snake')v(5,c.dx,c.dy);
   if(c.cmd==='tetris')v(6,['left','right','rot','drop'].indexOf(c.action));
   if(c.bands)for(let i=0;i<16;i++)e.band(i,c.bands[i],c.beat||0);
  }
  let pixels='';if(r.mode!==undefined){const address=advance(r.mode,r.now);pixels=Buffer.from(new Uint8Array(e.memory.buffer,address,768)).toString('hex');}
  process.stdout.write(JSON.stringify({pixels})+'\n');
  }catch(error){process.stdout.write(JSON.stringify({error:error.message})+'\n');}
 }
}
main().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
