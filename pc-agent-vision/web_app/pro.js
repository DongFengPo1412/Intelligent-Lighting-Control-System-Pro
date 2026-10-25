'use strict';
const $=id=>document.getElementById(id);
const notice=text=>$('notice').textContent=text;
async function api(path,data,method='POST'){const r=await fetch(path,{method,headers:data===undefined?{}:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});const v=await r.json();if(!r.ok||v.status==='error')throw Error(v.error||v.message||'操作未确认');return v;}
function bind(id,fn){$(id).onclick=()=>Promise.resolve().then(fn).catch(e=>notice(e.message));}
const modes={0:'关灯',1:'红',2:'蓝',3:'绿',4:'彩虹',5:'极光',6:'流星',7:'繁星',8:'变色',9:'雨滴',10:'波纹',11:'笑脸',12:'哭脸',13:'平静',14:'表情轮换',15:'频谱',16:'AI反馈',17:'红莉栖',19:'贪吃蛇',20:'蛇结算',21:'俄罗斯方块',22:'方块结算',23:'火焰',24:'代码雨',26:'指尖',27:'光球沙盒',28:'世界线仪表',29:'像素画布',30:'音乐光环',31:'环境微光'};
for(const [value,text] of Object.entries(modes)){$('mode').add(new Option(`${value} · ${text}`,value));}$('mode').value='17';
let modePending=false;$('mode').onchange=()=>modePending=true;
bind('applyMode',async()=>{await api('/api/mode',{mode:Number($('mode').value)});modePending=false;notice('模式已确认');});
bind('applyBrightness',async()=>{await api('/api/cmd',{cmd:'brightness',val:Number($('brightness').value)});notice('亮度已确认');});
bind('applyVolume',async()=>{await api('/api/volume',{volume:Number($('volume').value)});notice('音量已确认');});
bind('timer',async()=>{await api('/api/cmd',{cmd:'countdown',seconds:Number($('seconds').value)});notice('计时已确认');});
let matrix;try{matrix=new Matrix3D($('view'));}catch(e){notice(e.message);}
$('previewExposure').oninput=()=>{if(matrix){matrix.exposure=Number($('previewExposure').value);matrix.draw();}};
const pixels=new Uint8Array(768),editor=$('editor'),ctx=editor.getContext('2d');let drawing=false;
function renderEditor(){for(let i=0;i<256;i++){ctx.fillStyle=`rgb(${pixels.slice(i*3,i*3+3).join(',')})`;ctx.fillRect(i%16*20,Math.floor(i/16)*20,19,19);}}
function paint(e){const r=editor.getBoundingClientRect(),x=Math.floor((e.clientX-r.left)/r.width*16),y=Math.floor((e.clientY-r.top)/r.height*16);if(x<0||x>15||y<0||y>15)return;const c=$('color').value;for(let k=0;k<3;k++)pixels[(y*16+x)*3+k]=parseInt(c.slice(1+k*2,3+k*2),16);renderEditor();}
editor.onpointerdown=e=>{drawing=true;editor.setPointerCapture(e.pointerId);paint(e);};editor.onpointermove=e=>{if(drawing)paint(e);};editor.onpointerup=()=>drawing=false;editor.onpointercancel=()=>drawing=false;
const hex=()=>Array.from(pixels,v=>v.toString(16).padStart(2,'0')).join('');
bind('clearCanvas',()=>{pixels.fill(0);renderEditor();});bind('sendCanvas',async()=>{await api('/api/pro/canvas',{hex:hex()});notice('画布已确认');});
bind('saveCanvas',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({width:16,height:16,hex:hex()})],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='kurisu-canvas.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('loadCanvas').onchange=async e=>{try{const d=JSON.parse(await e.target.files[0].text());if(!/^[0-9a-f]{1536}$/i.test(d.hex))throw Error('画布格式错误');for(let i=0;i<768;i++)pixels[i]=parseInt(d.hex.slice(i*2,i*2+2),16);renderEditor();}catch(error){notice(error.message);}};
bind('sendChat',async()=>{$('reply').textContent=(await api('/api/chat',{message:$('chat').value})).reply;});
bind('addMemory',async()=>{await api('/api/pro/memory',{text:$('memoryText').value});await listMemory();});bind('addDocument',async()=>{const r=await api('/api/pro/documents',{text:$('memoryText').value});notice(`已保存 ${r.chunks} 段参考资料`);});
async function listMemory(){const list=await api('/api/pro/memory',undefined,'GET');$('memories').replaceChildren();for(const item of list){const p=document.createElement('p');p.textContent=item.text;const b=document.createElement('button');b.textContent='删除';b.onclick=async()=>{try{await api('/api/pro/memory',{id:item.id},'DELETE');await listMemory();}catch(e){notice(e.message);}};p.append(b);$('memories').append(p);}}bind('listMemory',listMemory);
bind('visionStart',async()=>{await api('/api/pro/vision',{enabled:true,mode:$('visionMode').value,camera:Number($('camera').value)});notice('视觉启动请求已提交，请查看运行状态');});bind('visionStop',()=>api('/api/pro/vision',{enabled:false}));bind('enroll',()=>api('/api/pro/enroll',{name:$('identity').value}));
const targets=[[.1,.1],[.5,.1],[.9,.1],[.1,.5],[.5,.5],[.9,.5],[.1,.9],[.5,.9],[.9,.9]];let samples=[];
let targetDot;
function calibrationText(){const t=targets[samples.length];$('calibration').textContent=t?`请注视屏幕上的橙色圆点，按空格采样（${samples.length}/9）。头部保持自然稳定。`:'校准已完成';if(targetDot)targetDot.remove();if(t){targetDot=document.createElement('div');targetDot.setAttribute('aria-label','当前视线校准点');Object.assign(targetDot.style,{position:'fixed',zIndex:'9',left:`${t[0]*100}%`,top:`${t[1]*100}%`,width:'18px',height:'18px',borderRadius:'50%',background:'#ffad64',boxShadow:'0 0 0 8px #101319',transform:'translate(-50%,-50%)',pointerEvents:'none'});document.body.append(targetDot);}}
document.addEventListener('keydown',e=>{if(e.code==='Space'&&targetDot&&targetDot.isConnected&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('sampleGaze').click();}});
bind('calibrate',()=>{samples=[];calibrationText();});bind('sampleGaze',async()=>{if(samples.length>=9)return;const s=await api('/api/pro/status',undefined,'GET'),o=s.vision.observation;if(!o.present||o.iris_x===undefined)throw Error('当前没有可用的人脸／虹膜观测');samples.push([o.iris_x,o.iris_y,...targets[samples.length]]);if(samples.length===9){const r=await api('/api/pro/calibrate',{samples});notice(`校准拟合误差 ${r.rms_training_error.toFixed(4)}；尚未测量独立定位精度`);}calibrationText();});
$('musicFile').onchange=async e=>{try{const r=await fetch('/api/pro/music-upload?visual='+encodeURIComponent($('musicVisual').value),{method:'POST',body:e.target.files[0]});const v=await r.json();if(!r.ok)throw Error(v.error);notice(v.simulated?'模拟音乐流程已启动，没有实际音频输出':'音乐流程已启动');}catch(error){notice(error.message);}};
bind('playUrl',()=>api('/api/pro/music',{url:$('musicUrl').value,visual:$('musicVisual').value}));bind('stopMusic',()=>api('/api/pro/music',{stop:true}));bind('setDifficulty',()=>api('/api/pro/difficulty',{level:Number($('difficulty').value),adaptive:$('adaptive').checked}));
let libraryOffset=0,libraryTotal=0,libraryQuery='',libraryLoaded=false,libraryLoading=false;
const trackLabel=t=>`${t.artist?t.artist+' — ':''}${t.title}`;
const musicTime=s=>`${Math.floor(Math.max(0,s)/60).toString().padStart(2,'0')}:${Math.floor(Math.max(0,s)%60).toString().padStart(2,'0')}`;
async function loadLibrary(){
 if(libraryLoading)return;libraryLoading=true;
 try{
  const p=new URLSearchParams({q:libraryQuery,offset:String(libraryOffset),limit:'30'});
  const r=await api('/api/pro/library?'+p,undefined,'GET');libraryTotal=r.total;libraryLoaded=!r.scanning;
  if(r.scanning)setTimeout(()=>loadLibrary().catch(e=>notice(e.message)),1000);
  if(document.activeElement!==$('libraryRoot'))$('libraryRoot').value=r.root||'';
  $('libraryState').textContent=r.error|| (r.scanning?'曲库正在扫描…':r.root?`曲库共 ${r.count} 首，原文件保持不变。`:'请先填写电脑上的音乐文件夹并扫描。');
  $('libraryPageState').textContent=`匹配 ${r.total} 首${r.total?' · '+(libraryOffset+1)+'–'+(libraryOffset+r.items.length):''}；按当前搜索结果建立播放列表。`;
  $('libraryTracks').replaceChildren();
  for(const t of r.items){const row=document.createElement('div');row.style.cssText='display:flex;align-items:center;gap:12px;border-top:1px solid #394250;padding:6px 0';const name=document.createElement('span');name.style.flex='1';name.textContent=trackLabel(t);const b=document.createElement('button');b.textContent='播放';b.setAttribute('aria-label','播放 '+trackLabel(t));b.onclick=async()=>{b.disabled=true;try{await api('/api/pro/music',{track_id:t.id,visual:$('musicVisual').value,scope:libraryQuery});notice('开始播放：'+trackLabel(t));}catch(e){notice(e.message);}finally{b.disabled=false;}};row.append(name,b);$('libraryTracks').append(row);}
  $('libraryPreviousPage').disabled=libraryOffset===0;$('libraryNextPage').disabled=libraryOffset+30>=libraryTotal;
 }finally{libraryLoading=false;}
}
bind('configureLibrary',async()=>{notice('正在扫描曲库…');const r=await api('/api/pro/library',{action:'configure',root:$('libraryRoot').value.trim()});if(r.error)throw Error(r.error);libraryOffset=0;await loadLibrary();notice(`曲库已就绪，共 ${r.count} 首。`);});
bind('rescanLibrary',async()=>{const r=await api('/api/pro/library',{action:'scan'});if(r.error)throw Error(r.error);libraryOffset=0;await loadLibrary();});
$('librarySearchForm').onsubmit=e=>{e.preventDefault();libraryOffset=0;libraryQuery=$('libraryQuery').value.trim();loadLibrary().catch(e=>notice(e.message));};
bind('clearLibrarySearch',()=>{libraryQuery='';libraryOffset=0;$('libraryQuery').value='';return loadLibrary();});
bind('libraryPreviousPage',()=>{libraryOffset=Math.max(0,libraryOffset-30);return loadLibrary();});bind('libraryNextPage',()=>{libraryOffset+=30;return loadLibrary();});
bind('previousMusic',()=>api('/api/pro/music',{action:'previous'}));bind('nextMusic',()=>api('/api/pro/music',{action:'next'}));
for(const id of ['musicOrder','musicRepeat'])$(id).onchange=()=>api('/api/pro/music',{action:'options',order:$('musicOrder').value,repeat:$('musicRepeat').value}).catch(e=>notice(e.message));
$('musicVisual').onchange=async()=>{try{const s=await api('/api/pro/status',undefined,'GET');if(s.music.running)await api('/api/mode',{mode:$('musicVisual').value==='fluid'?30:15});}catch(e){notice(e.message);}};
function updateMusic(m){
 const current=m.current; $('nowPlaying').textContent=(m.running?'正在播放：':current?'已停止：':'')+(current?trackLabel(current):m.running?'临时音源':'尚未播放歌曲');
 $('musicProgress').max=Math.max(1,m.duration||0);$('musicProgress').value=m.position||0;$('musicTime').textContent=musicTime(m.position||0)+' / '+musicTime(m.duration||0);
 for(const [id,value] of [['musicOrder',m.order],['musicRepeat',m.repeat]])if(value&&document.activeElement!==$(id))$(id).value=value;
 $('previousMusic').disabled=$('nextMusic').disabled=!m.queue_count;
 $('musicVoiceHint').textContent=m.running?(m.voice_wake?'播放中先说“助手”，音乐停止后可继续点歌或说“下一首”。':'播放中可使用网页切歌；当前未启用音乐唤醒监听。'):'语音示例：“播放＋歌名”“播放艾伦沃克的歌”“下一首”“单曲循环”。';
 if(m.error)notice(m.error);
 if(!libraryLoaded&&!m.library?.scanning)loadLibrary().catch(e=>notice(e.message));
}
async function poll(){try{const f=await api('/api/pro/frame',undefined,'GET');if(matrix)matrix.update(f.pixels);if(!modePending&&modes[f.mode])$('mode').value=String(f.mode);$('frameSource').textContent=`帧来源：${f.frame_source} · ${f.frame_id} · 模式 ${f.mode}`;const s=await api('/api/pro/status',undefined,'GET');$('status').textContent=JSON.stringify(s,null,2);$('visionStatus').textContent=JSON.stringify(s.vision,null,2);updateMusic(s.music);$('connectionState').textContent=s.simulated?'离线模拟模式：没有连接开发板或模型':'服务在线；显示来源与各功能状态见下方回读。';}catch(e){$('connectionState').textContent=e.message;}finally{setTimeout(poll,500);}}
renderEditor();loadLibrary().catch(e=>notice(e.message));poll();
