"""第二集的玻璃三维场景（GLSL 片段）。每个场景只定义 map / inner / floorGlow / solid，公共部分见 glass.py。

参数统一走 uP[0..47]（含义写在各场景注释里），由 render.py 按时间计算后传入。
"""

# ------------------------------------------------------------------ 玻璃海与悬浮玻璃球（投资启示主场景）
# uP: 0 浪高  1 浪速  2 球x  3 球z  4 球半径  5 金核亮度  6 金核半径比  7 裂纹进度 0..1  8 碎裂进度 0..1
#     9 锁链 0/1  10 锁链拉力（球被拉下的深度）  11 海面可见 0/1  12 球阵 0/1（收尾：多个球）  13 海水深度
#     14 金核颜色 0=金 1=冷蓝  15 球悬浮高度  16 涟漪中心 x  17 涟漪中心 z  18 涟漪时间  19 金核脉动
SEA = r'''
float waveH(vec2 x){
  float A = uP[0], s = uP[1]*uT;
  float h = 0.0;
  h += sin(dot(x, vec2(0.90, 0.30))*1.1 + s*1.3) * 0.55;
  h += sin(dot(x, vec2(-0.40, 0.95))*1.7 + s*1.7 + 1.3) * 0.30;
  h += sin(dot(x, vec2(0.70,-0.70))*2.9 + s*2.3 + 2.1) * 0.12;
  h += sin(dot(x, vec2(0.20, 1.00))*4.7 + s*3.1 + 0.4) * 0.05;
  h *= A;
  // 涟漪
  float r = length(x - vec2(uP[16], uP[17])); float rt = uP[18];
  if(rt > 0.0) h += 0.06*sin(r*9.0 - rt*7.0)*exp(-abs(r - rt*0.8)*2.5)*exp(-rt*0.5);
  return h;
}
vec3 orbPos(){
  vec2 c = vec2(uP[2], uP[3]);
  float y = waveH(c)*uP[11] + uP[15] + uP[4] - uP[10];
  return vec3(c.x, y, c.y);
}
// 四个过球心的切割面 → 16 块碎片
vec3 PL[4] = vec3[4](normalize(vec3(0.8,0.35,0.2)), normalize(vec3(-0.25,0.9,0.4)), normalize(vec3(0.3,-0.2,0.95)), normalize(vec3(0.6,0.6,-0.5)));
float shardSD(vec3 q, float R, float s){
  // s: 碎裂进度；每块碎片沿其方向飞散并下落、旋转
  float d = 1e9;
  for(int k=0;k<16;k++){
    vec3 sg = vec3(((k&1)==0)?1.0:-1.0, ((k&2)==0)?1.0:-1.0, ((k&4)==0)?1.0:-1.0);
    float s4 = ((k&8)==0)?1.0:-1.0;
    vec3 dir = normalize(PL[0]*sg.x + PL[1]*sg.y + PL[2]*sg.z + PL[3]*s4*0.7);
    float fk = float(k);
    vec3 off = dir*s*(0.45 + 0.35*fract(fk*0.37)); off.y -= min(1.6*s*s, 0.55 + uP[15] + uP[4] + off.y*0.0);
    vec3 qq = q - off;
    float ang = s*(1.5 + fract(fk*0.71)*2.0);
    qq.xy = rot(ang*0.6)*qq.xy; qq.yz = rot(ang*0.4)*qq.yz;
    float c = length(qq) - R;
    c = max(c, -sg.x*dot(qq, PL[0]) - 0.004);
    c = max(c, -sg.y*dot(qq, PL[1]) - 0.004);
    c = max(c, -sg.z*dot(qq, PL[2]) - 0.004);
    c = max(c, -s4*dot(qq, PL[3]) - 0.004);
    d = min(d, c);
  }
  return d;
}
float chainSD(vec3 p, vec3 top){
  float d = 1e9;
  vec3 a = top - vec3(0.0, uP[4]*0.95, 0.0);
  for(int k=0;k<12;k++){
    vec3 c = a - vec3(0.0, 0.17*float(k), 0.0);
    vec3 q = p - c;
    if((k&1)==1) q.xz = q.zx;
    float tr = length(vec2(length(vec2(q.x, max(abs(q.y)-0.06,0.0))) - 0.05, q.z)) - 0.016;
    d = min(d, tr);
  }
  return d;
}
vec2 map(vec3 p){
  vec2 res = vec2(1e9, 0.0);
  if(uP[11] > 0.5){
    float sea = (p.y - waveH(p.xz))*0.62;
    sea = max(sea, -(p.y + uP[13]));
    res = vec2(sea, MAT_GLASS);
  }
  vec3 o = orbPos(); float R = uP[4];
  if(uP[12] > 0.5){
    // 收尾：远处一片悬浮的玻璃球
    vec3 q = p; vec2 id = floor((q.xz + 0.7)/1.4); q.xz = mod(q.xz + 0.7, 1.4) - 0.7;
    float hy = waveH(id*1.4)*uP[11] + 0.35;
    float dd = length(q - vec3(0.0, hy, 0.0)) - 0.2;
    if(abs(id.x) + abs(id.y) > 0.5) res = U(res, vec2(dd, MAT_GLASS));
  }
  if(R > 0.001){
    float orb = length(p - o) - R;
    if(uP[8] > 0.001){
      float bound = length(p - o) - R*(1.0 + uP[8]*2.2) - 2.2*uP[8]*uP[8];
      orb = bound > 0.1 ? bound : shardSD(p - o, R, uP[8]);
    }
    res = U(res, vec2(orb, MAT_GLASS));
  }
  if(uP[9] > 0.5){
    float cb = sdBox(p - (o - vec3(0.0, uP[4] + 1.0, 0.0)), vec3(0.12, 1.1, 0.12), 0.0);
    res = U(res, vec2(cb > 0.05 ? cb : chainSD(p, o), MAT_DARK));
  }
  return res;
}
// 3D 胞状噪声的边：裂纹
float crackLines(vec3 q){
  vec3 i = floor(q), f = fract(q); float d1 = 9.0, d2 = 9.0;
  for(int x=-1;x<=1;x++) for(int y=-1;y<=1;y++) for(int z=-1;z<=1;z++){
    vec3 g = vec3(x,y,z); vec3 o = vec3(hash(i+g), hash(i+g+19.1), hash(i+g+47.3));
    float d = length(g + o - f); if(d<d1){ d2=d1; d1=d; } else if(d<d2) d2=d;
  }
  return d2 - d1;
}
vec3 inner(vec3 p){
  vec3 o = orbPos(); float R = uP[4];
  if(uP[12] > 0.5){
    vec2 id = floor((p.xz + 0.7)/1.4); vec2 c = id*1.4;
    float hy = waveH(c)*uP[11] + 0.35;
    float r2 = length(p - vec3(c.x, hy, c.y));
    if(abs(id.x) + abs(id.y) > 0.5 && r2 < 0.22) return vec3(1.0,0.52,0.14)*(exp(-r2*r2*400.0)*2.2 + exp(-r2*30.0)*0.5);
  }
  if(R < 0.001) return vec3(0);
  vec3 q = p - o;
  float r = length(q);
  if(r > R*1.05) return vec3(0);
  vec3 gold = mix(vec3(1.0,0.52,0.14), vec3(0.35,0.6,1.0), uP[14]);
  float cr = R*uP[6];
  float pulse = 1.0 + 0.25*sin(uT*3.0)*uP[19];
  vec3 e = gold * uP[5] * pulse * (exp(-pow(r/cr, 2.0)*3.0)*1.6 + exp(-r/(cr*0.35))*0.5);
  // 裂纹：从球心向外扩展的发光裂缝，同时金核变暗
  if(uP[7] > 0.001){
    // 裂纹从球体左下方的一点开始，向整个球扩展
    float reach = uP[7]*R*2.4;
    float rc = length(q - normalize(vec3(-0.6,-0.5,0.6))*R);
    float c = crackLines(q*1.9/R + 3.0);
    float m = smoothstep(0.022, 0.0, c) * smoothstep(reach, reach - 0.35*R, rc);
    e = e*(1.0 - 0.85*uP[7]) + vec3(1.0,0.36,0.14)*m*6.0*(1.0 - 0.5*uP[8]);
  }
  return e;
}
float mapSolid(vec3 p){
  if(uP[9] < 0.5) return 1e9;
  vec3 o = orbPos();
  float cb = sdBox(p - (o - vec3(0.0, uP[4] + 1.0, 0.0)), vec3(0.12, 1.1, 0.12), 0.0);
  return cb > 0.05 ? cb : chainSD(p, o);
}
float mapG(vec3 p){
  float d = 1e9;
  if(uP[11] > 0.5) d = max((p.y - waveH(p.xz))*0.62, -(p.y + uP[13]));
  if(uP[12] > 0.5){
    vec3 q = p; vec2 id = floor((q.xz + 0.7)/1.4); q.xz = mod(q.xz + 0.7, 1.4) - 0.7;
    float hy = waveH(id*1.4)*uP[11] + 0.35;
    if(abs(id.x) + abs(id.y) > 0.5) d = min(d, length(q - vec3(0.0, hy, 0.0)) - 0.2);
  }
  vec3 o = orbPos(); float R = uP[4];
  if(R > 0.001){
    float orb = length(p - o) - R;
    if(uP[8] > 0.001){ float bound = orb - R*uP[8]*2.2 - 2.2*uP[8]*uP[8]; orb = bound > 0.1 ? bound : shardSD(p - o, R, uP[8]); }
    d = min(d, orb);
  }
  return d;
}
vec3 floorGlow(vec3 p){
  vec3 o = orbPos();
  float r = length(p.xz - o.xz);
  float rings = 0.0;
  for(int k=0;k<3;k++){ float rr = fract(uT*0.18 + float(k)/3.0)*3.5; rings += exp(-pow((r-rr)*14.0,2.0))*(1.0-rr/3.5); }
  vec3 gold = mix(vec3(1.0,0.62,0.22), vec3(0.35,0.6,1.0), uP[14]);
  return vec3(0.22,0.5,1.0)*rings*0.35 + gold*exp(-r*r*1.5)*0.05*uP[5];
}
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){
  // 深色金属锁链：冷色高光 + 一点暖色反光
  vec3 r = reflect(rd, n);
  float f = 0.25 + 0.75*pow(1.0 - max(dot(-rd, n), 0.0), 3.0);
  // 锁链带一点暗红自发光，隔着海水也能看清（借来的钱 = 风险）
  return envS(r, 1.5)*0.6*f + vec3(0.02,0.022,0.028) + vec3(1.0,0.42,0.16)*(0.45 + 1.5*uP[10]);
}
'''

# ------------------------------------------------------------------ 价格玻璃管（开场：一年跌掉 25%）
# uP: 0 管子显示比例（沿路径从左到右长出来）  1 光脉冲位置 0..1  2 下跌部分高亮 0..1  3..26 路径 12 个点（x,y）
RIBBON = r'''
vec3 P(int i){ return vec3(uP[3+2*i], uP[4+2*i], 0.0); }
vec2 map(vec3 p){
  float d = 1e9; float grow = uP[0]*11.0;
  for(int i=0;i<11;i++){
    if(float(i) > grow) break;
    vec3 a = P(i), b = P(i+1);
    float g = clamp(grow - float(i), 0.0, 1.0);
    b = mix(a, b, g);
    d = min(d, sdCapsule(p, a, b, 0.062));
  }
  // 底座：一块薄玻璃板（刻度面板）
  float base = sdBox(p - vec3(0.0, -1.38, 0.0), vec3(0.95, 0.03, 0.42), 0.02);
  return U(vec2(d, MAT_GLASS), vec2(base, MAT_GLASS));
}
vec3 inner(vec3 p){
  // 沿管子流动的光脉冲；下跌段染成暖红
  float best = 1e9; float tpar = 0.0; float acc = 0.0; float total = 0.0;
  for(int i=0;i<11;i++){ total += length(P(i+1)-P(i)); }
  for(int i=0;i<11;i++){
    vec3 a=P(i), b=P(i+1); vec3 pa=p-a, ba=b-a; float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);
    float d = length(pa-ba*h);
    if(d < best){ best = d; tpar = (acc + h*length(ba))/total; }
    acc += length(ba);
  }
  if(best > 0.075) return vec3(0);
  float core = exp(-best*best*900.0);
  float pul = exp(-pow((tpar - uP[1])*28.0, 2.0));
  vec3 cold = vec3(0.35,0.7,1.0), warm = vec3(1.0,0.35,0.18);
  float drop = smoothstep(0.78, 0.84, tpar)*uP[2];
  vec3 c = mix(cold, warm, drop);
  return c*core*(0.25 + 6.0*pul) * step(tpar, uP[0] + 0.001);
}
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){ return vec3(0); }
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

# ------------------------------------------------------------------ 拼合的玻璃铭牌（片名）
# uP: 0 拼合进度 0..1（1 = 合拢）  1 铭牌宽  2 铭牌高  3 厚度  4 内部光脉冲  5 合拢后的微转角
PLAQUE = r'''
vec2 map(vec3 p){
  float s = 1.0 - uP[0];
  float W2 = uP[1], H2 = uP[2], T2 = uP[3];
  float d = 1e9;
  for(int k=0;k<5;k++){
    float fk = float(k);
    float x0 = -W2 + (fk + 0.5)*(2.0*W2/5.0);
    vec3 off = vec3((fk - 2.0)*0.45*s, sin(fk*2.3 + 0.5)*1.1*s, cos(fk*1.7)*1.3*s - s*0.5);
    vec3 q = p - vec3(x0, 0.0, 0.0) - off;
    q.xy = rot(s*(fk - 2.0)*0.45)*q.xy; q.yz = rot(s*sin(fk + 0.7)*0.9)*q.yz;
    float slab = sdBox(q, vec3(W2/5.0 - 0.004, H2, T2), 0.025);
    d = min(d, slab);
  }
  if(uP[0] > 0.999) d = sdBox(p, vec3(W2, H2, T2), 0.03);     // 合拢后是一整块玻璃（没有拼缝，片名清晰）
  return vec2(d, MAT_GLASS);
}
vec3 inner(vec3 p){
  float e = exp(-pow(p.y*3.0, 2.0))*smoothstep(1.2, 0.0, abs(p.x - (fract(uT*0.3)*4.0 - 2.0)));
  return vec3(0.4,0.7,1.0)*e*uP[4]*0.6;
}
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){
  float r = length(p.xz);
  float burst = uP[6];
  float ring = exp(-pow((r - burst*4.0)*6.0, 2.0))*(1.0 - burst);
  return vec3(0.3,0.6,1.0)*ring*1.2 + vec3(1.0,0.75,0.4)*exp(-r*r*0.8)*0.04;
}
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

# ------------------------------------------------------------------ 冷开场：历史影像平面 + 缓缓滑过的玻璃棱柱
# uP: 0 棱柱横移位置  1 棱柱旋转  2 第二根棱柱位置
PRISM = r'''
float sdTriPrism(vec3 p, vec2 h){ vec3 q = abs(p); return max(q.z - h.y, max(q.x*0.866025 + p.y*0.5, -p.y) - h.x*0.5); }
vec2 map(vec3 p){
  vec3 q = p - vec3(uP[0], 0.0, 0.9); q.xz = rot(0.2)*q.xz; q.xy = rot(uP[1])*q.xy;
  float pr = sdTriPrism(q.zyx, vec2(0.55, 3.0)) - 0.02;
  vec3 q2 = p - vec3(uP[2], -0.2, 1.4); q2.xy = rot(-uP[1]*0.7 + 1.2)*q2.xy;
  float pr2 = sdBox(q2, vec3(0.09, 3.0, 0.09), 0.03);
  return vec2(min(pr, pr2), MAT_GLASS);
}
vec3 inner(vec3 p){ return vec3(0); }
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){ return vec3(0); }
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

# ------------------------------------------------------------------ 两种定义：两块玻璃碑（左：波动 β；右：损失的可能性）
# uP: 0 升起进度  1 左碑内波形振幅  2 右碑金核亮度  3 右碑裂纹（不用）  4 左右分开距离
MONO = r'''
vec2 map(vec3 p){
  float rise = uP[0];
  vec3 a = p - vec3(-uP[4], -1.0 + 1.25*rise, 0.0);
  vec3 b = p - vec3( uP[4], -1.0 + 1.25*rise, 0.0);
  float m1 = sdBox(a, vec3(0.34, 1.1, 0.24), 0.07);
  float m2 = sdBox(b, vec3(0.34, 1.1, 0.24), 0.07);
  return vec2(min(m1, m2), MAT_GLASS);
}
vec3 inner(vec3 p){
  vec3 a = p - vec3(-uP[4], -1.0 + 1.25*uP[0], 0.0);
  vec3 b = p - vec3( uP[4], -1.0 + 1.25*uP[0], 0.0);
  vec3 c = vec3(0);
  if(abs(a.x) < 0.4 && abs(a.y) < 1.15){
    // 剧烈抖动的价格波形（冷蓝）
    float x = a.x*9.0;
    float w = uP[1]*(0.5*sin(x*2.1 + uT*5.0) + 0.3*sin(x*5.3 - uT*7.0) + 0.2*sin(x*11.0 + uT*11.0));
    float d = abs(a.y - w*0.55);
    c += vec3(0.35,0.7,1.0)*exp(-d*d*1400.0)*2.5*smoothstep(0.26, 0.0, abs(a.z));
  }
  if(abs(b.x) < 0.4 && abs(b.y) < 1.15){
    float r = length(b - vec3(0.0, 0.05, 0.0));
    c += vec3(1.0,0.55,0.16)*uP[2]*(exp(-r*r*30.0)*2.2 + exp(-r*10.0)*0.5);
  }
  return c;
}
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){
  float r1 = length(p.xz - vec2(-uP[4], 0.0)), r2 = length(p.xz - vec2(uP[4], 0.0));
  return vec3(0.25,0.55,1.0)*exp(-pow((r1-0.55)*10.0,2.0))*0.4*uP[0] + vec3(1.0,0.62,0.22)*exp(-pow((r2-0.55)*10.0,2.0))*0.3*uP[0];
}
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

# ------------------------------------------------------------------ 持有期：横向玻璃时间管 + 终点玻璃环
# uP: 0 脉冲位置 0..1  1 波动幅度  2 终点环亮度  3 管子长出进度
TUBE = r'''
vec2 map(vec3 p){
  float L = 2.3*uP[3];
  float tube = sdCapsule(p, vec3(0.0, -1.25, 0.0), vec3(0.0, -1.25 + L, 0.0), 0.2);
  vec3 q = p - vec3(0.0, 1.2, 0.0);
  float ring = sdTorus(q.xzy, vec2(0.42, 0.06));
  ring = sdTorus(q, vec2(0.42, 0.06));
  return vec2(min(tube, ring), MAT_GLASS);
}
vec3 inner(vec3 p){
  float y = (p.y + 1.25)/2.45;
  float wob = uP[1]*(0.5*sin(y*31.0 + uT*4.0) + 0.3*sin(y*67.0 - uT*6.0))*0.13;
  float d = length(vec2(p.x - wob, p.z));
  float trail = smoothstep(uP[0] - 0.45, uP[0], y)*step(y, uP[0]);
  float head = exp(-pow((y - uP[0])*40.0, 2.0));
  vec3 c = vec3(0.35,0.7,1.0)*exp(-d*d*900.0)*(trail*1.5 + head*8.0);
  vec3 q = p - vec3(0.0, 1.2, 0.0);
  float r = length(vec2(length(q.xz) - 0.42, q.y));
  c += vec3(1.0,0.6,0.2)*exp(-r*r*500.0)*uP[2]*3.0;
  return c;
}
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){ return vec3(1.0,0.62,0.22)*exp(-length(p.xz)*2.0)*0.06*uP[2] + vec3(0.25,0.55,1.0)*exp(-pow((length(p.xz)-0.5)*8.0,2.0))*0.2; }
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

# ------------------------------------------------------------------ 透镜组（一句话总结：碎片合拢成透镜，光线聚焦）
# uP: 0 合拢进度  1 光束亮度
LENS = r'''
float lensSD(vec3 p, float R, float th){ return max(length(p - vec3(0,0,R-th)) - R, length(p + vec3(0,0,R-th)) - R); }
vec2 map(vec3 p){
  float s = 1.0 - uP[0];
  float d = 1e9;
  for(int k=0;k<3;k++){
    float fk = float(k);
    vec3 q = p - vec3(0.0, 0.0, (fk - 1.0)*0.55 + (fk - 1.0)*2.2*s) - vec3(sin(fk*2.0)*1.6*s, cos(fk*1.3)*1.2*s, 0.0);
    q.xz = rot(s*(fk - 1.0)*0.8)*q.xz;
    d = min(d, lensSD(q, 2.2 - fk*0.25, 0.16 - fk*0.02));
  }
  return vec2(d, MAT_GLASS);
}
vec3 inner(vec3 p){
  float r = length(p.xy);
  return vec3(1.0,0.72,0.35)*exp(-r*r*20.0)*uP[1]*0.8;
}
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){ return vec3(1.0,0.7,0.35)*exp(-length(p.xz)*1.4)*0.06*uP[1]; }
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

# ------------------------------------------------------------------ 磨砂玻璃屏（今天：账户回撤）
# uP: 0 屏幕位置 z  1 屏幕倾角  2 屏幕可见 0/1
SCREEN = r'''
vec2 map(vec3 p){
  vec3 q = p - vec3(0.0, 0.1, uP[0]); q.yz = rot(uP[1])*q.yz;
  float s = sdBox(q, vec3(0.6, 1.08, 0.05), 0.1);
  if(uP[2] < 0.5) s = 1e9;
  float orb = length(p - vec3(0.0, 0.2, -1.6)) - 0.55;
  return vec2(min(s, orb), MAT_GLASS);
}
vec3 inner(vec3 p){
  float r = length(p - vec3(0.0, 0.2, -1.6));
  if(r > 0.6) return vec3(0);
  return vec3(1.0,0.52,0.14)*uP[3]*(exp(-r*r*40.0)*1.6 + exp(-r*12.0)*0.5);
}
float mapG(vec3 p){ return map(p).x; }
float mapSolid(vec3 p){ return 1e9; }
vec3 floorGlow(vec3 p){ return vec3(1.0,0.6,0.2)*exp(-length(p.xz - vec2(0.0,-1.6))*1.6)*0.06*uP[3]; }
vec3 solid(vec3 p, vec3 n, vec3 rd, float id){ return vec3(0); }
'''

SCENES = dict(sea=SEA, ribbon=RIBBON, plaque=PLAQUE, prism=PRISM, mono=MONO, tube=TUBE, lens=LENS, screen=SCREEN)
