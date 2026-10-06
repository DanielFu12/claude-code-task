import numpy as np, soundfile as sf, sys, librosa
S=sys.argv[1]
y,sr=sf.read(f"{S}/bgm.wav")  # stereo 44100
bt=np.load(f"{S}/beats.npy")
# splices: (play until src time a) -> (resume at src time b)
B=lambda i: bt[i]
segs=[(0.0,B(79)),(B(63),B(200)),(B(112),len(y)/sr)]
xf=int(0.06*sr)
out=np.zeros((0,2))
for k,(s,e) in enumerate(segs):
    si,ei=int(s*sr),int(e*sr)
    pre=y[max(0,si-xf//2):si+0] ; seg=y[si:ei+xf//2] if k<len(segs)-1 else y[si:]
    if len(out)==0: out=seg.copy(); continue
    # equal-power crossfade: out tail (xf//2 past splice) with incoming (xf//2 before start)
    inc=np.concatenate([y[si-xf//2:si],seg])
    n=xf
    t=np.linspace(0,1,n)[:,None]
    tail=out[-n:]
    mix=tail*np.cos(t*np.pi/2)+inc[:n]*np.sin(t*np.pi/2)
    out=np.concatenate([out[:-n],mix,inc[n:]])
print('len',len(out)/sr, 'splice times', B(79), B(79)+B(200)-B(63))
T=180.0
out=out[:int(T*sr)]
if len(out)<int(T*sr): out=np.concatenate([out,np.zeros((int(T*sr)-len(out),2))])
f=int(2.5*sr); out[-f:]*=np.linspace(1,0,f)[:,None]**1.5
sf.write(f"{S}/bgm180.wav",out,sr)
# analysis for sync
m=librosa.to_mono(out.T).astype(np.float32)
r=librosa.feature.rms(y=m,hop_length=sr//2)[0]
print(' '.join(f'{i*0.5:.0f}:{20*np.log10(v+1e-9):.0f}' for i,v in enumerate(r) if i%2==0))
tempo,beats=librosa.beat.beat_track(y=m,sr=sr,hop_length=512)
np.save(f"{S}/beats180.npy",librosa.frames_to_time(beats,sr=sr,hop_length=512))
on=librosa.onset.onset_strength(y=m,sr=sr,hop_length=512)
np.save(f"{S}/onset180.npy",on/on.max())
