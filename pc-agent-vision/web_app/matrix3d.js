/* WebGL 3D LED matrix; frame bytes are supplied by the API, never invented here. */
class Matrix3D {
  constructor(canvas) {
    this.gl=canvas.getContext('webgl',{antialias:true});this.pixels=new Uint8Array(768);this.angle=.22;this.exposure=3;
    if(!this.gl)throw Error('浏览器不支持 WebGL');
    const g=this.gl;
    const shader=(type,source)=>{const s=g.createShader(type);g.shaderSource(s,source);g.compileShader(s);if(!g.getShaderParameter(s,g.COMPILE_STATUS))throw Error(g.getShaderInfoLog(s));return s;};
    const vertex=`attribute vec3 a;uniform vec3 offset;uniform vec3 size;uniform float angle;uniform float aspect;varying float light;void main(){vec3 v=a*size+offset;float c=cos(angle),s=sin(angle);vec3 r=vec3(c*v.x+s*v.z,v.y,-s*v.x+c*v.z);float y=.96*r.y-.28*r.z;float z=.28*r.y+.96*r.z+19.;gl_Position=vec4(r.x*1.85/aspect,y*1.85,z*.8-2.,z);gl_PointSize=28.*19./z;light=.8+a.y*.2;}`;
    const p=g.createProgram();g.attachShader(p,shader(g.VERTEX_SHADER,vertex));
    g.attachShader(p,shader(g.FRAGMENT_SHADER,`precision mediump float;uniform vec3 color;varying float light;void main(){gl_FragColor=vec4(color*light,1.);}`));g.linkProgram(p);
    if(!g.getProgramParameter(p,g.LINK_STATUS))throw Error(g.getProgramInfoLog(p));this.program=p;
    this.locations={};for(const n of ['offset','size','angle','aspect','color'])this.locations[n]=g.getUniformLocation(p,n);
    const vertices=[];const faces=[[[0,0,1],[1,0,1],[1,1,1],[0,1,1]],[[1,0,0],[0,0,0],[0,1,0],[1,1,0]],[[0,1,1],[1,1,1],[1,1,0],[0,1,0]],[[0,0,0],[1,0,0],[1,0,1],[0,0,1]],[[1,0,1],[1,0,0],[1,1,0],[1,1,1]],[[0,0,0],[0,0,1],[0,1,1],[0,1,0]]];
    for(const f of faces)for(const i of [0,1,2,0,2,3])vertices.push((f[i][0]-.5)*.8,(f[i][1]-.5)*.8,(f[i][2]-.5)*.25);
    const b=g.createBuffer();this.cubeBuffer=b;g.bindBuffer(g.ARRAY_BUFFER,b);g.bufferData(g.ARRAY_BUFFER,new Float32Array(vertices),g.STATIC_DRAW);
    const loc=g.getAttribLocation(p,'a');this.cubeLocation=loc;g.enableVertexAttribArray(loc);g.vertexAttribPointer(loc,3,g.FLOAT,false,0,0);
    const glow=g.createProgram();g.attachShader(glow,shader(g.VERTEX_SHADER,vertex));g.attachShader(glow,shader(g.FRAGMENT_SHADER,`precision mediump float;uniform vec3 color;void main(){vec2 p=gl_PointCoord-.5;float a=exp(-dot(p,p)*24.)*.2;gl_FragColor=vec4(color*a,a);}`));g.linkProgram(glow);if(!g.getProgramParameter(glow,g.LINK_STATUS))throw Error(g.getProgramInfoLog(glow));this.glow=glow;this.glowLocations={};for(const n of ['offset','size','angle','aspect','color'])this.glowLocations[n]=g.getUniformLocation(glow,n);this.pointBuffer=g.createBuffer();g.bindBuffer(g.ARRAY_BUFFER,this.pointBuffer);g.bufferData(g.ARRAY_BUFFER,new Float32Array([0,0,0]),g.STATIC_DRAW);this.pointLocation=g.getAttribLocation(glow,'a');
    let dragging=false,last=0;canvas.onpointerdown=e=>{dragging=true;last=e.clientX;canvas.setPointerCapture(e.pointerId);};canvas.onpointerup=()=>dragging=false;canvas.onpointermove=e=>{if(dragging){this.angle+=(e.clientX-last)*.01;last=e.clientX;this.draw();}};
    this.draw();
  }
  update(hex) {if(!/^[a-f0-9]{1536}$/i.test(hex))throw Error('无效帧数据');for(let i=0;i<768;i++)this.pixels[i]=parseInt(hex.slice(i*2,i*2+2),16);this.draw();}
  draw() {
    const g=this.gl,c=g.canvas;g.viewport(0,0,c.width,c.height);g.enable(g.DEPTH_TEST);g.clearColor(.025,.03,.045,1);g.clear(g.COLOR_BUFFER_BIT|g.DEPTH_BUFFER_BIT);g.useProgram(this.program);
    g.uniform1f(this.locations.angle,this.angle);g.uniform1f(this.locations.aspect,c.width/c.height);
    g.bindBuffer(g.ARRAY_BUFFER,this.cubeBuffer);g.enableVertexAttribArray(this.cubeLocation);g.vertexAttribPointer(this.cubeLocation,3,g.FLOAT,false,0,0);
    g.uniform3f(this.locations.size,20,20,2);g.uniform3f(this.locations.offset,0,0,.4);g.uniform3f(this.locations.color,.035,.04,.05);g.drawArrays(g.TRIANGLES,0,36);g.uniform3f(this.locations.size,1,1,1);
    const color=i=>[0,1,2].map(k=>Math.min(1,Math.pow(this.pixels[i*3+k]/255,1/2.2)*this.exposure));
    for(let i=0;i<256;i++){g.uniform3f(this.locations.offset,i%16-7.5,7.5-Math.floor(i/16),0);g.uniform3f(this.locations.color,...color(i).map(v=>.025+v));g.drawArrays(g.TRIANGLES,0,36);}
    g.useProgram(this.glow);g.bindBuffer(g.ARRAY_BUFFER,this.pointBuffer);g.enableVertexAttribArray(this.pointLocation);g.vertexAttribPointer(this.pointLocation,3,g.FLOAT,false,0,0);const l=this.glowLocations;g.uniform3f(l.size,1,1,1);g.uniform1f(l.angle,this.angle);g.uniform1f(l.aspect,c.width/c.height);g.enable(g.BLEND);g.blendFunc(g.ONE,g.ONE);g.depthMask(false);
    for(let i=0;i<256;i++){g.uniform3f(l.offset,i%16-7.5,7.5-Math.floor(i/16),-.3);g.uniform3f(l.color,...color(i));g.drawArrays(g.POINTS,0,1);}g.depthMask(true);g.disable(g.BLEND);
  }
}
window.Matrix3D=Matrix3D;
