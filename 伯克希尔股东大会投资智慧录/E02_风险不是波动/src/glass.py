"""玻璃质感三维渲染器：GLSL 光线步进（moderngl + Mesa llvmpipe，无需 GPU；需在 xvfb-run 下运行）。

每个场景只写一段 GLSL：map()（距离场与材质）、inner()（玻璃内部光脉冲）、floorGlow()（地面焦散光环）、
solid()（非玻璃材质着色）。公共部分负责：相机、条形灯环境光、菲涅尔反射、穿过玻璃厚度的折射、
RGB 三通道不同折射率的棱镜色散、按光程的冰蓝吸收、地面反射与接触阴影、文字贴图平面。
输出 float32 RGBA：RGB 为线性 HDR 颜色，A 为相机距离（给景深用）。
"""
import numpy as np

HEAD = r'''
#version 330
in vec2 uv; out vec4 fragColor;
uniform vec2 uRes; uniform float uT;
uniform vec3 uCam; uniform vec3 uTgt; uniform float uFov; uniform float uRoll;
uniform float uP[48];
uniform float uSweep;          // 条形灯扫过的方位角（弧度）
uniform float uSweepI;         // 扫光强度
uniform float uFloorY;
uniform float uIOR;            // 中间（绿）通道折射率
uniform float uDisp;           // 色散强度：R/B 通道折射率偏移
uniform vec3 uAbsorb;          // 吸收系数（冰蓝）
uniform float uFrost;          // 磨砂程度 0..1
uniform float uEnvI;           // 环境亮度
uniform float uGrid;           // 地面网格亮度
uniform float uGlowStep;       // 玻璃内部发光的积分步长上限
uniform float uSpec;           // 掠射角光谱色强度
uniform sampler2D uTex0; uniform vec3 uT0o; uniform vec3 uT0u; uniform vec3 uT0v; uniform float uT0a; uniform vec3 uT0c;
uniform sampler2D uTex1; uniform vec3 uT1o; uniform vec3 uT1u; uniform vec3 uT1v; uniform float uT1a; uniform vec3 uT1c;

#define PI 3.14159265
#define MAT_GLASS 1.0
#define MAT_GOLD 2.0
#define MAT_DARK 3.0
#define MAT_EMIT 4.0

float hash(vec3 p){ p = fract(p*0.3183099+.1); p*=17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
float noise(vec3 x){ vec3 i=floor(x), f=fract(x); f=f*f*(3.0-2.0*f);
  return mix(mix(mix(hash(i+vec3(0,0,0)),hash(i+vec3(1,0,0)),f.x), mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x), mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z); }
mat2 rot(float a){ float c=cos(a), s=sin(a); return mat2(c,-s,s,c); }
float sdBox(vec3 p, vec3 b, float r){ vec3 q=abs(p)-b+r; return length(max(q,0.0))+min(max(q.x,max(q.y,q.z)),0.0)-r; }
float sdSphere(vec3 p, float r){ return length(p)-r; }
float sdTorus(vec3 p, vec2 t){ vec2 q=vec2(length(p.xz)-t.x,p.y); return length(q)-t.y; }
float sdCyl(vec3 p, float r, float h, float rr){ vec2 d=vec2(length(p.xz)-r+rr, abs(p.y)-h+rr); return min(max(d.x,d.y),0.0)+length(max(d,0.0))-rr; }
float sdCapsule(vec3 p, vec3 a, vec3 b, float r){ vec3 pa=p-a, ba=b-a; float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.); return length(pa-ba*h)-r; }
float sdOcta(vec3 p, float s){ p=abs(p); return (p.x+p.y+p.z-s)*0.57735027; }
float smin(float a, float b, float k){ float h=clamp(0.5+0.5*(b-a)/k,0.,1.); return mix(b,a,h)-k*h*(1.-h); }
vec2 U(vec2 a, vec2 b){ return a.x<b.x?a:b; }
vec3 envS(vec3 d, float soft);
float mapG(vec3 p);
float mapSolid(vec3 p);
vec3 solid(vec3 p, vec3 n, vec3 rd, float id);
vec3 nrm(vec3 p);
'''

TAIL = r'''
// ------------------------------------------------------------------ 环境：深色无限空间 + 条形灯
vec3 envL(vec3 d){ return envS(d, 1.0); }
vec3 envS(vec3 d, float soft){
  vec3 c = vec3(0.0012,0.0018,0.0032) + vec3(0.004,0.007,0.013)*smoothstep(-0.2,0.9,d.y);   // 冷色天光渐变
  float az = atan(d.x, d.z);
  // 主扫光：竖直细长条形灯，绕场景缓慢转动
  float da = abs(mod(az - uSweep + PI, 2.0*PI) - PI);
  c += vec3(0.75,0.88,1.0) * uSweepI * smoothstep(0.045*soft,0.0,da)/soft * smoothstep(0.95,0.25,abs(d.y-0.15)) * 6.0;
  // 两条固定的侧面条灯（冷白），一条暖金轮廓灯
  float a2 = abs(mod(az - 2.1 + PI, 2.0*PI) - PI), a3 = abs(mod(az + 2.2 + PI, 2.0*PI) - PI);
  c += vec3(0.55,0.72,1.0) * smoothstep(0.03*soft,0.0,a2)/soft * smoothstep(0.7,0.2,abs(d.y-0.25)) * 2.2;
  c += vec3(1.0,0.74,0.36) * smoothstep(0.035*soft,0.0,a3)/soft * smoothstep(0.6,0.15,abs(d.y-0.1)) * 1.4;
  // 前上方大面积柔光箱：让平整的玻璃面上有柔和的渐变反光
  c += vec3(0.55,0.68,0.9)*0.10*smoothstep(0.05,0.75,d.y)*smoothstep(1.0,0.1,abs(d.x))*smoothstep(-0.6,0.4,d.z);
  // 顶部条形柔光
  c += vec3(0.7,0.82,1.0) * smoothstep(0.86,0.97,d.y) * smoothstep(0.08,0.0,abs(d.x)) * 1.6;
  return c * uEnvI;
}

vec2 mapAll(vec3 p){ return map(p); }
vec3 nrmG(vec3 p){ vec2 e=vec2(1.2e-3,0.0);
  return normalize(vec3(mapG(p+e.xyy)-mapG(p-e.xyy), mapG(p+e.yxy)-mapG(p-e.yxy), mapG(p+e.yyx)-mapG(p-e.yyx))); }
vec2 traceFrom(vec3 ro, vec3 rd, float t0, float tmax, int steps){
  float t=t0; vec2 h=vec2(1e9,0.0);
  for(int i=0;i<steps;i++){ h=mapAll(ro+rd*t); if(abs(h.x)<4e-4*(1.0+t)) return vec2(t,h.y); t+=abs(h.x)*0.92; if(t>tmax) break; }
  return vec2(-1.0,0.0);
}
vec3 nrm(vec3 p){ vec2 e=vec2(1.2e-3,0.0);
  return normalize(vec3(mapAll(p+e.xyy).x-mapAll(p-e.xyy).x, mapAll(p+e.yxy).x-mapAll(p-e.yxy).x, mapAll(p+e.yyx).x-mapAll(p-e.yyx).x)); }

vec2 trace(vec3 ro, vec3 rd, float tmax, int steps){ return traceFrom(ro, rd, 0.0, tmax, steps); }

// 文字 / 图片贴图平面：o 原点、u/v 半轴；返回 rgb 与覆盖度
vec4 texPlane(vec3 ro, vec3 rd, sampler2D tx, vec3 o, vec3 u, vec3 v, vec3 col, float a, float tmax){
  if(a<=0.001) return vec4(0);
  vec3 n = normalize(cross(u,v)); float dn = dot(rd,n); if(abs(dn)<1e-4) return vec4(0);
  float t = dot(o-ro,n)/dn; if(t<0.0||t>tmax) return vec4(0);
  vec3 q = ro+rd*t-o; vec2 st = vec2(dot(q,u)/dot(u,u), dot(q,v)/dot(v,v));
  if(abs(st.x)>1.0||abs(st.y)>1.0) return vec4(0);
  vec4 s = texture(tx, st*0.5+0.5);
  return vec4(col*s.rgb, s.a*a);
}

// 地面（深色微光泽）+ 焦散光环 + 接触阴影
vec3 shadeFloor(vec3 p, vec3 rd, bool cheap){
  vec3 c = vec3(0.0025,0.0032,0.0048);
  float ao = clamp(mapAll(p+vec3(0,0.35,0)).x/0.35, 0.0, 1.0);
  c *= 0.35+0.65*ao;
  c += floorGlow(p);
  // 地面上很淡的网格反光线（精密仪器感）
  vec2 g = abs(fract(p.xz*0.5)-0.5);
  c += vec3(0.04,0.07,0.12)*smoothstep(0.010,0.0,min(g.x,g.y))*exp(-0.12*length(p.xz))*0.18*uGrid;
  if(!cheap){
    vec3 rr = reflect(rd, vec3(0,1,0));
    vec2 h = trace(p+vec3(0,1e-3,0), rr, 12.0, 48);
    vec3 refl = envL(rr)*0.25;
    if(h.x>0.0){ vec3 q=p+rr*h.x; vec3 n=nrm(q);
      if(h.y==MAT_GLASS){ float f=pow(1.0-max(dot(-rr,n),0.0),3.0); refl = envL(reflect(rr,n))*(0.15+0.85*f) + inner(q)*0.15 + vec3(0.02,0.04,0.07); }
      else refl = solid(q,n,rr,h.y);
      refl *= exp(-0.35*h.x);
    }
    float fres = 0.04+0.5*pow(1.0-max(-rd.y,0.0),4.0);
    c += refl*fres*1.6;
  }
  return c;
}

// 穿过玻璃之后看到的东西（贴图平面、地面、非玻璃物体、环境）
vec3 behind(vec3 ro, vec3 rd){
  float tf = (uFloorY-ro.y)/rd.y; if(rd.y>=0.0) tf=1e9;
  vec2 h = traceFrom(ro, rd, 0.03, 14.0, 40);
  float th = h.x>0.0 ? h.x : 1e9;
  vec3 c;
  if(th<tf && th<1e8){ vec3 q=ro+rd*th; vec3 n=nrm(q);
    if(h.y==MAT_GLASS){ float f=pow(1.0-max(dot(-rd,n),0.0),3.0); c = envS(reflect(rd,n),2.5)*(0.2+0.8*f)*0.7 + envS(rd,2.5)*0.5 + inner(q)*0.8; }
    else c = solid(q,n,rd,h.y);
  } else if(tf<1e8){ c = shadeFloor(ro+rd*tf, rd, true); }
  else c = envS(rd, 2.2);
  float tm = min(th,tf);
  vec4 a = texPlane(ro,rd,uTex0,uT0o,uT0u,uT0v,uT0c,uT0a,tm); c = mix(c, a.rgb, clamp(a.a,0.,1.));
  vec4 b = texPlane(ro,rd,uTex1,uT1o,uT1u,uT1v,uT1c,uT1a,tm); c = mix(c, b.rgb, clamp(b.a,0.,1.));
  return c;
}

vec3 shadeGlass(vec3 p, vec3 rd, vec3 n){
  float cosi = max(dot(-rd,n),0.0);
  float F = 0.04 + 0.96*pow(1.0-cosi,5.0);
  vec3 jit = (vec3(noise(p*9.0),noise(p*9.0+7.1),noise(p*9.0+3.3))-0.5)*uFrost*0.6 + (vec3(noise(p*41.0),noise(p*41.0+2.7),noise(p*41.0+5.3))-0.5)*uFrost*0.12;
  vec3 nf = normalize(n+jit);
  vec3 refl = envL(reflect(rd,nf));
  // 进入玻璃：内部步进到出射面；全反射时在内部继续反弹（最多 3 次）
  vec3 rdi = refract(rd, nf, 1.0/uIOR);
  vec3 q = p - n*2e-3; float L=0.0; vec3 glow=vec3(0);
  vec3 n2; vec3 col = vec3(0); bool done=false;
  for(int b=0;b<4;b++){
    for(int i=0;i<72;i++){
      float d = -mapG(q); if(d<3e-4) break;
      float ds = mapSolid(q);
      if(ds < 2e-3){                       // 玻璃里的非玻璃物体（锁链）：直接着色，按光程衰减
        vec3 sc = solid(q, nrm(q), rdi, MAT_DARK);
        return refl*F + (1.0-F)*sc*exp(-uAbsorb*L) + glow;
      }
      float s=clamp(min(d, max(ds, 0.0025)),0.0025,uGlowStep); glow += inner(q)*s; q += rdi*s; L += s; if(L>8.0) break; }
    vec3 qa = q - rdi*0.0025, qb = q;
    for(int i=0;i<5;i++){ vec3 qm=(qa+qb)*0.5; if(mapG(qm)<0.0) qa=qm; else qb=qm; }
    q = qa; n2 = -nrmG(q);
    vec3 tg = refract(rdi, n2, uIOR);
    if(dot(tg,tg)>1e-6 || b==3) break;
    rdi = reflect(rdi, n2); q += rdi*0.004;
  }
  vec3 qo = q - n2*3e-3;
  float iors[3] = float[3](uIOR-uDisp, uIOR, uIOR+uDisp);
  vec3 dirs[3]; bool tir = false;
  for(int k=0;k<3;k++){ dirs[k] = refract(rdi, n2, iors[k]); if(dot(dirs[k],dirs[k])<1e-6) tir = true; }
  if(tir){
    // 接近临界角时不做色散（避免大片彩虹色带）：整体按绿通道处理，绿通道也全反射时取柔化的环境反射
    vec3 g = dirs[1];
    col = dot(g,g)<1e-6 ? envS(reflect(rdi,n2), 3.0)*0.35 : behind(qo, normalize(g + jit*0.6*uFrost));
  } else {
    for(int k=0;k<3;k++){
      vec3 ro2 = dirs[k]; if(uFrost>0.01) ro2 = normalize(ro2 + jit*0.6);
      col[k] = behind(qo, ro2)[k];
    }
  }
  vec3 trans = col * exp(-uAbsorb*L);
  vec3 c = refl*F + trans*(1.0-F) + glow;
  // 棱镜边缘：掠射角处加一点光谱色
  float edge = pow(1.0-cosi, 3.0);
  vec3 spec = 0.5+0.5*cos(6.2831*(vec3(0.0,0.33,0.67)+edge*1.3+p.y*0.4));
  c += spec*edge*0.08*uEnvI*uSpec;
  return c;
}

void main(){
  vec2 frag = (uv-0.5)*vec2(uRes.x/uRes.y,1.0);
  vec3 fw = normalize(uTgt-uCam); vec3 rt = normalize(cross(fw, vec3(0,1,0))); vec3 up = cross(rt,fw);
  frag = rot(uRoll)*frag;
  vec3 rd = normalize(fw + (frag.x*rt + frag.y*up)*tan(uFov*0.5)*2.0);
  vec3 ro = uCam;
  float tf = (uFloorY-ro.y)/rd.y; if(rd.y>=0.0) tf=1e9;
  vec2 h = trace(ro, rd, 30.0, 110);
  float th = h.x>0.0?h.x:1e9;
  vec3 c; float depth;
  if(th<tf && th<1e8){
    vec3 p=ro+rd*th; vec3 n=nrm(p); depth=th;
    if(h.y==MAT_GLASS) c = shadeGlass(p,rd,n); else c = solid(p,n,rd,h.y);
  } else if(tf<1e8){ c = shadeFloor(ro+rd*tf, rd, false); depth=tf; }
  else { c = envL(rd); depth=60.0; }
  float tm = min(th,tf);
  vec4 a = texPlane(ro,rd,uTex0,uT0o,uT0u,uT0v,uT0c,uT0a,tm); c = mix(c, a.rgb, clamp(a.a,0.,1.));
  vec4 b = texPlane(ro,rd,uTex1,uT1o,uT1u,uT1v,uT1c,uT1a,tm); c = mix(c, b.rgb, clamp(b.a,0.,1.));
  // 体积雾：很淡的冷色空气透视
  c = mix(c, vec3(0.010,0.016,0.026)*uEnvI, 1.0-exp(-0.012*min(depth,40.0)));
  fragColor = vec4(c, depth);
}
'''

VERT = '''#version 330
in vec2 p; out vec2 uv; void main(){ uv=p*0.5+0.5; gl_Position=vec4(p,0.0,1.0); }'''

DEFAULTS = dict(uFov=0.75, uRoll=0.0, uSweep=0.6, uSweepI=1.0, uFloorY=-1.0, uIOR=1.5, uDisp=0.011,
                uAbsorb=(0.55, 0.22, 0.08), uFrost=0.0, uEnvI=1.0, uGrid=1.0, uGlowStep=0.03, uSpec=1.0, uT0a=0.0, uT1a=0.0,
                uT0o=(0, 0, 0), uT0u=(1, 0, 0), uT0v=(0, 1, 0), uT0c=(1, 1, 1),
                uT1o=(0, 0, 0), uT1u=(1, 0, 0), uT1v=(0, 1, 0), uT1c=(1, 1, 1))


class Renderer:
    def __init__(self, w=1080, h=1920):
        import moderngl
        self.mgl = moderngl
        self.ctx = moderngl.create_standalone_context()
        self.w, self.h = w, h
        self.progs = {}
        self.vbo = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
        self.fbos = {}
        self.blank = self.ctx.texture((4, 4), 4, np.zeros((4, 4, 4), np.uint8).tobytes())
        self.texcache = {}

    def program(self, name, src):
        if name not in self.progs:
            prog = self.ctx.program(vertex_shader=VERT, fragment_shader=HEAD + src + TAIL)
            self.progs[name] = (prog, self.ctx.simple_vertex_array(prog, self.vbo, 'p'))
        return self.progs[name]

    def fbo(self, w, h):
        if (w, h) not in self.fbos:
            tex = self.ctx.texture((w, h), 4, dtype='f4')
            self.fbos[(w, h)] = self.ctx.framebuffer(color_attachments=[tex])
        return self.fbos[(w, h)]

    def texture(self, key, rgba):
        """rgba: uint8 HxWx4（第 0 行在图片顶端）；按 key 缓存"""
        if key not in self.texcache:
            if len(self.texcache) > 24:
                for k in list(self.texcache)[:12]:
                    self.texcache.pop(k).release()
            img = np.ascontiguousarray(rgba[::-1])
            t = self.ctx.texture((img.shape[1], img.shape[0]), 4, img.tobytes())
            t.build_mipmaps(); t.filter = (self.mgl.LINEAR_MIPMAP_LINEAR, self.mgl.LINEAR); t.anisotropy = 4.0
            self.texcache[key] = t
        return self.texcache[key]

    def render(self, name, src, t, cam, tgt, params=(), scale=1.0, tex0=None, tex1=None, **u):
        prog, vao = self.program(name, src)
        w, h = int(self.w * scale) // 2 * 2, int(self.h * scale) // 2 * 2
        fb = self.fbo(w, h); fb.use()
        vals = dict(DEFAULTS); vals.update(u)
        P = list(params) + [0.0] * (48 - len(params))
        if 'uP' in prog: prog['uP'].write(np.array(P[:prog['uP'].array_length], 'f4').tobytes())
        for k, v in [('uRes', (float(w), float(h))), ('uT', float(t)), ('uCam', tuple(map(float, cam))), ('uTgt', tuple(map(float, tgt)))] + list(vals.items()):
            if k in prog:
                prog[k].value = tuple(map(float, v)) if isinstance(v, (tuple, list, np.ndarray)) else float(v)
        for unit, (key, tex) in enumerate([('uTex0', tex0), ('uTex1', tex1)]):
            (tex if tex is not None else self.blank).use(unit)
            if key in prog: prog[key].value = unit
        vao.render(self.mgl.TRIANGLE_STRIP)
        a = np.frombuffer(fb.read(components=4, dtype='f4'), np.float32).reshape(h, w, 4)[::-1]
        return np.ascontiguousarray(a)
