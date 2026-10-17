"""“流光诗意纪录片”渲染风格的程序化画面（GLSL 全屏着色器，moderngl + Mesa llvmpipe，需在 xvfb-run 下运行）。

三类画面：
- OCEAN：写实空镜——金色时刻的海面（程序化天空、体积云、海浪、太阳反光），镜头极慢推进。
- FLOW：流动可视化——线积分卷积（LIC）流线纹理：层流 / 湍流 / 一冷一暖两个光源的辐射流线 / 汇点（永久损失）。
- GRID：变形网格曲面——透视发光网格（或点阵地面），可加涟漪、行波、深坑、撕裂。
输出线性 RGB float32（由 s4post 统一做柔光泛光、颗粒与暗角）。
"""
import numpy as np

VERT = '''#version 330
in vec2 p; out vec2 uv; void main(){ uv=p*0.5+0.5; gl_Position=vec4(p,0.0,1.0); }'''

COMMON = r'''
#version 330
in vec2 uv; out vec4 fragColor;
uniform vec2 uRes; uniform float uT; uniform float uP[32];
#define PI 3.14159265
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*0.1031); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float vnoise(vec2 x){ vec2 i=floor(x), f=fract(x); f=f*f*(3.0-2.0*f);
  return mix(mix(hash12(i),hash12(i+vec2(1,0)),f.x), mix(hash12(i+vec2(0,1)),hash12(i+vec2(1,1)),f.x), f.y); }
float fbm(vec2 p){ float a=0.5, s=0.0; for(int i=0;i<6;i++){ s+=a*vnoise(p); p=p*2.03+vec2(1.7,9.2); a*=0.5; } return s; }
mat2 rot(float a){ float c=cos(a), s=sin(a); return mat2(c,-s,s,c); }
'''

# ------------------------------------------------------------------ 金色时刻的海面
# uP: 0 浪高  1 浪速  2 太阳高度  3 太阳方位  4 相机高度  5 相机前推  6 云量  7 色调（0 金色时刻 → 1 暮色深蓝）  8 曝光
OCEAN = COMMON + r'''
float sea(vec2 p, float A, float t){
  float h = 0.0, a = A, f = 0.16;
  vec2 d = vec2(1.0, 0.25);
  for(int i=0;i<5;i++){
    float ph = dot(p, d)*f + t*(0.55 + 0.25*float(i));
    float w = 1.0 - abs(sin(ph));                      // 尖峰波
    w = mix(w, 1.0 - abs(sin(ph*1.3 + 1.7)), 0.35);
    h += pow(w, 2.2)*a;
    d = rot(1.1)*d; f *= 1.95; a *= 0.42;
  }
  return h + (fbm(p*0.6 + t*0.15) - 0.5)*A*0.25;
}
vec3 sky(vec3 rd, vec3 sun, float dusk, float clouds){
  float sd = max(dot(rd, sun), 0.0);
  float y = max(rd.y, 0.0);
  vec3 deep = vec3(0.016, 0.022, 0.058), mid = vec3(0.055, 0.035, 0.05), hz = vec3(0.55, 0.21, 0.055);
  vec3 c = mix(hz, mid, smoothstep(0.0, 0.035, y));
  c = mix(c, deep, smoothstep(0.03, 0.24, y));
  c = mix(c, mix(c, vec3(0.05,0.07,0.14), 0.8), dusk);
  c += vec3(1.0,0.62,0.26)*pow(sd, 40.0)*0.30 + vec3(1.0,0.88,0.66)*pow(sd, 2200.0)*12.0 + vec3(1.0,0.58,0.24)*pow(sd, 220.0)*0.9;
  // 云：拉长的条状云，暗色剪影 + 背光处的金边
  if(rd.y > 0.0){
    vec2 cp = rd.xz/(rd.y + 0.06);
    float n = fbm(cp*vec2(0.22, 0.9) + vec2(uT*0.006, 0.0));
    float cl = smoothstep(0.52, 0.80, n)*clouds;
    float rim = smoothstep(0.52, 0.60, n) - smoothstep(0.62, 0.80, n);
    vec3 cc = vec3(0.018,0.015,0.028) + vec3(1.0,0.60,0.28)*(pow(sd, 90.0)*1.4 + rim*pow(sd, 25.0)*0.7);
    c = mix(c, cc, cl*smoothstep(0.0, 0.05, rd.y)*0.9);
  }
  return c;
}
void main(){
  vec2 q = (uv - 0.5)*vec2(uRes.x/uRes.y, 1.0);
  float A = uP[0], t = uT*uP[1];
  vec3 sun = normalize(vec3(sin(uP[3]), uP[2], -cos(uP[3])));
  vec3 ro = vec3(0.0, uP[4], -uP[5]);
  vec3 rd = normalize(vec3(q.x, q.y - 0.12, -1.25));
  vec3 col;
  if(rd.y > 0.0){ col = sky(rd, sun, uP[7], uP[6]); }
  else{
    // 海面：沿视线步进求交
    float tt = 0.0, hit = -1.0;
    float dt = 0.4;
    vec3 p;
    for(int i=0;i<90;i++){
      p = ro + rd*tt;
      float h = sea(p.xz, A, t);
      if(p.y < h){ hit = tt; break; }
      dt = max(0.02, (p.y - h)*0.6); tt += dt; if(tt > 220.0) break;
    }
    if(hit < 0.0){ col = sky(vec3(rd.x, 0.001, rd.z), sun, uP[7], uP[6]); }
    else{
      // 二分细化
      float a = hit - dt, b = hit;
      for(int i=0;i<6;i++){ float m=(a+b)*0.5; vec3 pm=ro+rd*m; if(pm.y < sea(pm.xz,A,t)) b=m; else a=m; }
      tt = b; p = ro + rd*tt;
      vec2 e = vec2(0.02 + tt*0.002, 0.0);
      vec3 n = normalize(vec3(sea(p.xz - e.xy,A,t) - sea(p.xz + e.xy,A,t), 2.0*e.x, sea(p.xz - e.yx,A,t) - sea(p.xz + e.yx,A,t)));
      vec3 rr = reflect(rd, n);
      float fres = 0.02 + 0.98*pow(1.0 - max(dot(n, -rd), 0.0), 5.0);
      vec3 refl = sky(vec3(rr.x, abs(rr.y), rr.z), sun, uP[7], uP[6]);
      vec3 body = vec3(0.006,0.008,0.016)*(0.6 + 0.4*max(dot(n, sun), 0.0));
      col = mix(body, refl*0.55, fres);
      // 太阳在浪尖上的碎金
      col += vec3(1.0,0.78,0.45)*pow(max(dot(rr, sun), 0.0), 220.0)*3.0;
      // 远处的空气透视
      float fog = 1.0 - exp(-tt*0.006);
      col = mix(col, sky(vec3(rd.x, 0.02, rd.z), sun, uP[7], uP[6]), fog);
    }
  }
  fragColor = vec4(col*uP[8], 1.0);
}
'''

# ------------------------------------------------------------------ 线积分卷积流线
# uP: 0 场类型（0 层流 1 湍流 2 一冷一暖双光源 3 汇点 4 单个暖光源）  1 流速  2 亮度  3 冷暖混合（0 钢蓝 → 1 香槟金）
#     4,5 冷光源位置（屏幕 0..1）  6,7 暖光源位置  8 冷光源强度  9 暖光源强度  10 湍流强度  11 汇点强度  12 流线密度  13 冷光源抖动
FLOW = COMMON + r'''
vec2 A_(){ return vec2(uP[4], uP[5]) + vec2(sin(uT*7.3), cos(uT*5.1))*0.012*uP[13]; }
vec2 field(vec2 p){
  int ty = int(uP[0] + 0.5);
  vec2 asp = vec2(uRes.x/uRes.y, 1.0);
  vec2 v = vec2(1.0, 0.0);
  if(ty == 0){ v = vec2(1.0, 0.25*sin(p.x*4.0 + uT*0.4)); }
  if(ty == 1 || uP[10] > 0.0){
    float e = 0.01; vec2 s = p*2.2 + vec2(uT*0.05, 0.0);
    float n1 = fbm(s + vec2(0.0, e)), n2 = fbm(s - vec2(0.0, e)), n3 = fbm(s + vec2(e, 0.0)), n4 = fbm(s - vec2(e, 0.0));
    vec2 curl = vec2(n1 - n2, -(n3 - n4))/(2.0*e);
    v = (ty == 1) ? curl : normalize(v)*(1.0 - uP[10]) + curl*uP[10]*0.4;
  }
  if(ty == 2 || ty == 4){
    vec2 a = (p - A_())*asp, b = (p - vec2(uP[6], uP[7]))*asp;
    vec2 va = a/(dot(a,a) + 0.002)*uP[8], vb = b/(dot(b,b) + 0.002)*uP[9];
    vec2 sw = vec2(-b.y, b.x)/(dot(b,b) + 0.01)*uP[9]*0.35;
    v = (ty == 4) ? vb + sw : va + vb + sw;
  }
  if(ty == 3){
    vec2 c = (p - vec2(uP[6], uP[7]))*asp;
    v = -c/(dot(c,c) + 0.004)*uP[11] + vec2(-c.y, c.x)/(dot(c,c) + 0.02)*0.4;
  }
  return normalize(v + 1e-5);
}
float white(vec2 p, float ph){ float h = hash12(floor(p*uRes*uP[12])); return step(0.86, h)*(0.5 + 0.5*sin(6.2831*(h*7.0 + ph))); }
void main(){
  vec2 p = uv;
  float step_ = 1.6/uRes.y;
  float acc = 0.0, wsum = 0.0;
  vec2 f = p, b = p;
  float ph = uT*uP[1];
  for(int i=0;i<32;i++){
    float k = float(i)/32.0;
    float w = 0.5 + 0.5*cos(PI*k);                       // 汉宁核：流线平滑
    acc += (white(f, ph) + white(b, ph))*w;
    wsum += 2.0*w;
    f += field(f)*step_; b -= field(b)*step_;
  }
  float l = acc/wsum;
  l = pow(clamp(l*5.0, 0.0, 1.0), 1.8);
  vec3 cold = vec3(0.42,0.63,0.75), warm = vec3(0.97,0.85,0.60);
  float mixw = uP[3];
  int ty = int(uP[0] + 0.5);
  vec2 asp = vec2(uRes.x/uRes.y, 1.0);
  if(ty == 2){
    float da = length((p - A_())*asp), db = length((p - vec2(uP[6],uP[7]))*asp);
    mixw = clamp(da/(da + db), 0.0, 1.0);
    l *= 0.35 + 0.65*(exp(-da*3.0)*uP[8] + exp(-db*3.0)*uP[9]);
  }
  if(ty == 4){ float db = length((p - vec2(uP[6],uP[7]))*asp); l *= 0.25 + exp(-db*2.5)*uP[9]; mixw = 1.0; }
  if(ty == 3){ float dc = length((p - vec2(uP[6],uP[7]))*asp); l *= 0.3 + 0.9*exp(-dc*2.0); }
  vec3 col = mix(cold, warm, mixw)*l*uP[2];
  // 光源本体：柔和的发光点
  if(ty == 2 || ty == 4){
    float da = length((p - A_())*asp), db = length((p - vec2(uP[6],uP[7]))*asp);
    if(ty == 2) col += cold*exp(-da*da*900.0)*2.5*uP[8] + cold*exp(-da*28.0)*0.25*uP[8];
    col += warm*exp(-db*db*900.0)*2.5*uP[9] + warm*exp(-db*28.0)*0.3*uP[9];
  }
  fragColor = vec4(col, 1.0);
}
'''

# ------------------------------------------------------------------ 变形网格曲面 / 点阵地面
# uP: 0 涟漪幅度  1 行波幅度  2 行波速度  3 深坑深度  4 深坑 x  5 深坑 z  6 深坑宽度  7 相机高度  8 相机前移  9 俯仰
#     10 网格密度  11 点阵模式 0/1  12 亮度  13 冷暖（0 钢蓝 → 1 香槟金）  14 光点 x  15 光点 y  16 光点 z  17 光点亮度
#     18 撕裂（永久的坑，行波过后留下）  19 相机横移  20 色调：紫蓝网格 0/1
GRID = COMMON + r'''
float H(vec2 p){
  float h = 0.0;
  h += uP[0]*(sin(p.x*1.3 + uT*0.9)*0.5 + sin(p.y*1.7 - uT*0.7)*0.35 + sin((p.x + p.y)*2.3 + uT*1.3)*0.15);
  // 行波：一道道起伏从远处推来
  h += uP[1]*sin(p.y*0.9 - uT*uP[2])*(0.6 + 0.4*sin(p.x*0.5));
  // 深坑（永久损失）
  vec2 c = vec2(uP[4], uP[5]);
  float r2 = dot(p - c, p - c);
  h -= uP[3]*exp(-r2/(uP[6]*uP[6]));
  h -= uP[18]*exp(-r2/(uP[6]*uP[6]*0.6));
  return h;
}
void main(){
  vec2 q = (uv - 0.5)*vec2(uRes.x/uRes.y, 1.0);
  vec3 ro = vec3(uP[19], uP[7], uP[8]);
  float pitch = uP[9];
  vec3 rd = normalize(vec3(q.x, q.y, -1.1));
  rd.yz = rot(-pitch)*rd.yz;          // pitch < 0 为俯视
  vec3 col = vec3(0.0);
  float tt = 0.0, hit = -1.0; vec3 p;
  for(int i=0;i<120;i++){
    p = ro + rd*tt;
    float h = H(p.xz);
    if(p.y < h){ hit = tt; break; }
    tt += max(0.01, (p.y - h)*0.45); if(tt > 60.0) break;
  }
  vec3 cold = mix(vec3(0.42,0.63,0.75), vec3(0.56,0.66,1.0), uP[20]), warm = vec3(0.97,0.85,0.60);
  vec3 lc = mix(cold, warm, uP[13]);
  if(hit > 0.0){
    float a = tt - 0.02, b = tt;
    for(int i=0;i<5;i++){ float m=(a+b)*0.5; vec3 pm=ro+rd*m; if(pm.y < H(pm.xz)) b=m; else a=m; }
    p = ro + rd*b; tt = b;
    vec2 g = p.xz*uP[10];
    // 像素在地面上的覆盖宽度（解析估计；分支里不能用 fwidth）
    float px = tt*(1.0/uRes.y)/1.1;
    vec2 fw = vec2(px*uP[10]/max(abs(rd.y), 0.04), px*uP[10]/max(abs(rd.y), 0.04));
    fw.x = px*uP[10]*1.2;
    float line;
    if(uP[11] > 0.5){
      vec2 d = abs(fract(g) - 0.5);
      float r = length(d);
      line = smoothstep(0.08 + fw.x, 0.08 - fw.x*0.5, r)*1.6;
    } else {
      vec2 d = abs(fract(g - 0.5) - 0.5);
      vec2 ww = vec2(0.006) + fw*0.5;
      vec2 l2 = smoothstep(ww + fw, ww - fw*0.5, d);
      line = max(l2.x, l2.y);
      // 远处线条密集处淡出（避免摩尔纹）
      line *= smoothstep(0.9, 0.25, max(fw.x, fw.y));
    }
    float depth = H(p.xz);
    float glowLow = smoothstep(0.0, -1.2, depth);               // 坑里更暗、偏暖
    vec3 c = lc*line*(1.0 - 0.6*glowLow) + warm*line*glowLow*0.6;
    float fog = exp(-tt*0.07);
    col = c*fog*uP[12];
    // 光点在网格上的倒影光晕
    vec3 L = vec3(uP[14], uP[15], uP[16]);
    float dl = length(p.xz - L.xz);
    col += warm*uP[17]*0.35*exp(-dl*dl*0.5)*fog*line;
  }
  // 光点本体
  vec3 L = vec3(uP[14], uP[15], uP[16]);
  vec3 toL = L - ro; float tl = dot(toL, rd);
  if(tl > 0.0 && uP[17] > 0.0){
    float dd = length(toL - rd*tl);
    col += warm*uP[17]*(exp(-dd*dd*800.0/max(tl*0.05,0.2))*2.2 + exp(-dd*9.0)*0.25);
  }
  // 地平线处很淡的冷色辉光
  col += cold*0.025*exp(-abs(rd.y + 0.02)*30.0)*uP[12];
  fragColor = vec4(col, 1.0);
}
'''

SHADERS = dict(ocean=OCEAN, flow=FLOW, grid=GRID)


class GL:
    def __init__(self):
        import moderngl
        self.mgl = moderngl
        self.ctx = moderngl.create_standalone_context()
        self.vbo = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
        self.progs, self.fbos = {}, {}

    def render(self, name, t, params, w, h):
        if name not in self.progs:
            prog = self.ctx.program(vertex_shader=VERT, fragment_shader=SHADERS[name])
            self.progs[name] = (prog, self.ctx.simple_vertex_array(prog, self.vbo, 'p'))
        prog, vao = self.progs[name]
        if (w, h) not in self.fbos:
            self.fbos[(w, h)] = self.ctx.framebuffer(color_attachments=[self.ctx.texture((w, h), 4, dtype='f4')])
        fb = self.fbos[(w, h)]; fb.use()
        if 'uRes' in prog: prog['uRes'].value = (float(w), float(h))
        if 'uT' in prog: prog['uT'].value = float(t)
        if 'uP' in prog:
            P = list(params) + [0.0] * (32 - len(params))
            prog['uP'].write(np.array(P[:prog['uP'].array_length], 'f4').tobytes())
        vao.render(self.mgl.TRIANGLE_STRIP)
        a = np.frombuffer(fb.read(components=4, dtype='f4'), np.float32).reshape(h, w, 4)[::-1, :, :3]
        return np.ascontiguousarray(a)
