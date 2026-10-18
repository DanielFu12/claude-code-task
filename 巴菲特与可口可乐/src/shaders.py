"""GLSL 片元着色器（三维光线步进 + 光效背景）。全部原创。"""

# ------------------------------------------------------------------ 背景：暗场 + 缓慢流动的体积光雾
BG = """
uniform vec3 c1; uniform vec3 c2; uniform float amt; uniform vec2 focus; uniform float rays;
void main(){
  vec2 p = uv*res; vec2 q = (p - focus*res)/res.y;
  float r = length(q);
  float n = fbm(q*2.2 + vec2(t*0.03, -t*0.05));
  float n2 = fbm(q*5.0 - vec2(t*0.02, t*0.04) + n);
  vec3 col = vec3(0.012,0.011,0.016);
  col += c1 * amt * exp(-r*r*2.2) * (0.55+0.6*n);
  col += c2 * amt * 0.55 * exp(-pow(length(q-vec2(0.35,-0.45)),2.)*3.0) * n2;
  // 体积光束（从上方斜射）
  float a = atan(q.x+0.15, q.y+1.2);
  float beam = pow(max(0., 1.-abs(a-0.08)*7.), 3.) * rays;
  col += c1 * beam * 0.25 * (0.6+0.4*n2) * smoothstep(1.6,0.2,r);
  o = vec4(col,1);
}
"""

# ------------------------------------------------------------------ 玻璃弧形瓶（光线步进 + 折射/反射 + 液体 + 气泡）
BOTTLE = """
uniform float rot; uniform float camy; uniform float camd; uniform float fill;   // 液面高度 0..1
uniform float glass_a; uniform vec3 key; uniform float ex; uniform float bub; uniform vec2 shift;
uniform float tilt; uniform float gold; uniform float ripple; uniform float floorr;

const float HB = 2.4;
float prof(float y){            // y: 0..1 → 半径（经典弧形瓶轮廓，原创近似）
  float ys[12] = float[12](0.0,0.04,0.18,0.30,0.36,0.47,0.58,0.66,0.74,0.84,0.95,1.0);
  float rs[12] = float[12](0.30,0.335,0.34,0.30,0.295,0.345,0.335,0.29,0.21,0.135,0.125,0.118);
  if(y<=0.) return rs[0];
  for(int i=0;i<11;i++){ if(y<=ys[i+1]){ float f=(y-ys[i])/(ys[i+1]-ys[i]); f=f*f*(3.-2.*f); return mix(rs[i],rs[i+1],f);} }
  return rs[11];
}
float flute(vec3 p, float y){   // 中段竖向凹槽
  float a = atan(p.z,p.x);
  float w = smoothstep(0.30,0.40,y)*(1.-smoothstep(0.58,0.68,y));
  return -0.012*w*pow(abs(cos(a*6.)),3.);
}
float sdB(vec3 p){
  float y = p.y/HB;
  float r = prof(clamp(y,0.,1.))*0.95 + flute(p,y);
  float d = length(p.xz) - r;
  d = max(d, -p.y); d = max(d, p.y-HB);
  return d*0.8;
}
vec3 nrm(vec3 p){ vec2 e=vec2(0.0015,0); return normalize(vec3(sdB(p+e.xyy)-sdB(p-e.xyy),sdB(p+e.yxy)-sdB(p-e.yxy),sdB(p+e.yyx)-sdB(p-e.yyx))); }

vec3 envc(vec3 d){              // 暗棚：两块柔光箱 + 红色轮廓光 + 金色底光
  vec3 c = vec3(0.004,0.004,0.006);
  float sb1 = smoothstep(0.30,0.0,length(vec2(d.x+0.62,d.y-0.35)*vec2(1.,0.45)));
  float sb2 = smoothstep(0.22,0.0,length(vec2(d.x-0.75,d.y-0.1)*vec2(1.,0.35)));
  c += key*sb1*3.2 + vec3(1.0,0.86,0.62)*sb2*1.6*ex;
  c += vec3(0.9,0.12,0.10)*pow(max(0.,-d.z),6.)*0.25;
  c += vec3(1.0,0.75,0.35)*smoothstep(-0.2,-0.9,d.y)*0.18*gold;
  return c;
}
void main(){
  vec2 q = (uv*res - 0.5*res)/res.y - shift;
  float cr=cos(rot), sr=sin(rot);
  vec3 ro = vec3(0., camy, camd);
  vec3 ta = vec3(0., HB*0.48, 0.);
  vec3 ww = normalize(ta-ro), uu = normalize(cross(ww, vec3(0,1,0))), vv = cross(uu,ww);
  vec3 rd = normalize(q.x*uu + q.y*vv + 1.9*ww);
  // 旋转瓶子（等价于旋转射线）
  mat2 R = mat2(cr,-sr,sr,cr);
  ro.xz = R*ro.xz; rd.xz = R*rd.xz;
  float tt=0., d; bool hit=false;
  for(int i=0;i<140;i++){ vec3 p=ro+rd*tt; d=sdB(p); if(d<0.0007){hit=true;break;} tt+=d; if(tt>12.) break; }
  vec3 col = vec3(0.); float alpha = 0.;
  // 地面反射（暗色镜面）
  if(!hit){
    if(rd.y<0.){
      float tp = -ro.y/rd.y; vec3 fp = ro+rd*tp;
      float rr = length(fp.xz);
      float rip = ripple*0.5*(0.5+0.5*sin(rr*18.-t*2.5))*exp(-rr*0.6);
      col += vec3(0.9,0.18,0.12)*0.06*exp(-rr*1.3)*floorr + vec3(1.,0.8,0.4)*rip*0.12*smoothstep(3.5,0.4,rr);
      alpha = clamp(0.25*exp(-rr*0.9)*floorr + rip*0.4,0.,1.);
    }
    o = vec4(col, alpha); return;
  }
  vec3 p = ro+rd*tt; vec3 n = nrm(p);
  float fres = 0.04 + 0.96*pow(1.-max(dot(-rd,n),0.),5.);
  vec3 refl = envc(reflect(rd,n));
  // 折射进入液体：近似体积吸收（可乐的深琥珀色）
  vec3 rdi = refract(rd, n, 1./1.5);
  float y = p.y/HB;
  float inside = 0.;
  // 粗略估算穿过厚度
  float th = 0.; vec3 pi = p - n*0.01;
  for(int i=0;i<40;i++){ float di = -sdB(pi); if(di<0.002) break; pi += rdi*max(di,0.01); th += max(di,0.01); }
  float liquid = step(y, fill) ;
  vec3 cola = vec3(0.42,0.12,0.04);
  vec3 trans = envc(rdi)*0.9;
  vec3 absorb = exp(-th*vec3(2.2,6.5,11.0)*1.6);
  vec3 body = mix(trans*0.5 + vec3(0.03,0.03,0.035), trans*absorb*1.6 + cola*0.05, liquid);
  // 内部光（背光穿透液体的暖红辉光）
  body += liquid * vec3(0.9,0.22,0.05) * pow(max(0.,1.-abs(dot(n,rd))),2.)*0.35*ex;
  // 气泡
  if(bub>0. && liquid>0.){
    vec3 bp = p*vec3(28.,10.,28.); bp.y -= t*3.2;
    vec3 cid = floor(bp); vec3 f = fract(bp)-0.5;
    float h = hash3(cid);
    float b = smoothstep(0.12,0.0,length(f*vec3(1.,1.4,1.)) - 0.05*h) * step(0.82,h);
    body += vec3(1.,0.85,0.6)*b*bub*0.9;
  }
  col = mix(body, refl, fres) * glass_a;
  // 空瓶部分是透明玻璃：只保留反射与边缘，背景可见
  float edge = pow(1.-max(dot(-rd,n),0.),2.5);
  alpha = mix(clamp(fres*1.6 + edge*0.55 + 0.06, 0., 1.), 1., liquid);
  // 高光条
  vec3 h = normalize(normalize(vec3(-0.6,0.5,0.8)) - rd);
  col += pow(max(dot(n,h),0.),120.)*vec3(1.,0.95,0.85)*1.8*ex;
  // 液面线
  col += vec3(1.,0.7,0.4)*smoothstep(0.012,0.0,abs(y-fill))*0.35*step(0.02,fill);
  // 背后红色轮廓光，勾勒剪影
  col += vec3(0.95,0.16,0.10)*pow(edge,2.)*0.55*ex;
  o = vec4(col*alpha + col*(1.-alpha)*0.0, alpha);
}
"""

# ------------------------------------------------------------------ 糖浆滴落（金属球融合 + 液面涟漪）
DROP = """
uniform float ph; uniform vec3 tint;
float smin(float a,float b,float k){ float h=clamp(.5+.5*(b-a)/k,0.,1.); return mix(b,a,h)-k*h*(1.-h); }
float sdf(vec3 p){
  float yd = mix(1.6, -0.15, ph*ph);
  float drop = length((p-vec3(0.,yd,0.))*vec3(1.,0.85,1.)) - 0.22;
  float wave = 0.05*exp(-length(p.xz)*1.5)*sin(length(p.xz)*14.-ph*30.)*smoothstep(0.85,1.0,ph);
  float pool = p.y + 0.35 - wave;
  float tail = length(p.xz) - 0.05*smoothstep(yd, yd+1.4, p.y)*(1.-ph);
  float st = max(tail, -(p.y-yd)); st = max(st, p.y-(yd+1.5));
  return smin(smin(drop, pool, 0.25*ph*ph), st, 0.12);
}
vec3 nr(vec3 p){ vec2 e=vec2(0.002,0); return normalize(vec3(sdf(p+e.xyy)-sdf(p-e.xyy),sdf(p+e.yxy)-sdf(p-e.yxy),sdf(p+e.yyx)-sdf(p-e.yyx))); }
void main(){
  vec2 q=(uv*res-0.5*res)/res.y;
  vec3 ro=vec3(0.,0.15,3.4); vec3 rd=normalize(vec3(q+vec2(0.,0.22), -1.7));
  float tt=0.; bool hit=false; vec3 p;
  for(int i=0;i<120;i++){ p=ro+rd*tt; float d=sdf(p); if(d<0.001){hit=true;break;} tt+=d*0.8; if(tt>9.)break; }
  vec3 col=vec3(0.); float al=0.;
  if(hit){
    vec3 n=nr(p); float fr=0.04+0.96*pow(1.-max(dot(-rd,n),0.),5.);
    vec3 r=reflect(rd,n);
    vec3 envr = vec3(1.,0.85,0.6)*smoothstep(0.25,0.,length(vec2(r.x+0.5,r.y-0.5)*vec2(1.,0.5)))*3.
              + vec3(1.,0.4,0.2)*smoothstep(0.3,0.,length(vec2(r.x-0.7,r.y-0.1)*vec2(1.,0.4)))*1.2;
    vec3 base = tint*0.35*(0.4+0.6*max(dot(n,normalize(vec3(-0.4,0.8,0.5))),0.));
    col = mix(base, envr, fr) + tint*pow(max(0.,1.-abs(dot(n,rd))),3.)*0.4;
    col += pow(max(dot(n,normalize(normalize(vec3(-0.5,0.6,0.7))-rd)),0.),90.)*1.5;
    al = 1.;
    al *= smoothstep(4.5,2.5,length(p.xz))*(p.y>-0.3?1.:smoothstep(3.0,0.5,length(p.xz)));
  }
  o=vec4(col,al);
}
"""

# ------------------------------------------------------------------ 光芒（片尾、高潮）
RAYS = """
uniform vec2 c; uniform vec3 col; uniform float k; uniform float spin;
void main(){
  vec2 p=uv*res; vec2 d=(p-c*res)/res.y; float r=length(d); float a=atan(d.y,d.x)+spin;
  float s = 0.5+0.5*sin(a*14.+fbm(vec2(a*3.,t*0.2))*4.);
  float rays = pow(s,6.)*exp(-r*1.6) + exp(-r*r*18.)*1.5;
  o = vec4(col*rays*k, 1.);
}
"""
