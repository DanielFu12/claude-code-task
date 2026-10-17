"""成片自检：规格、黑屏、静音/中断、旁白与字幕同步（语音识别比对）。

用法：python3 src/check.py VIDEO WORK ASR_DIR
ASR_DIR 下需要 sherpa-onnx 的 whisper-base（英文）和 paraformer-zh-2024-03-09（中文）模型。
"""
import json, re, subprocess, sys
import numpy as np, sherpa_onnx

video, work, asr = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/') + '/'


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stderr + p.stdout


info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', video],
                                 capture_output=True, text=True).stdout)
v = [s for s in info['streams'] if s['codec_type'] == 'video'][0]
a = [s for s in info['streams'] if s['codec_type'] == 'audio'][0]
dur = float(info['format']['duration'])
print('视频 %sx%s %s %s，音频 %s %sHz，时长 %.2fs，%.1fMB' % (v['width'], v['height'], v['r_frame_rate'], v['codec_name'],
      a['codec_name'], a['sample_rate'], dur, int(info['format']['size']) / 1e6))

# 黑屏（像素 < 0.08 且持续 ≥ 0.2s）
bd = run(['ffmpeg', '-hide_banner', '-i', video, '-vf', 'blackdetect=d=0.2:pix_th=0.08', '-an', '-f', 'null', '-'])
print('黑屏片段:', re.findall(r'black_start:\S+ black_end:\S+', bd) or '无')
# 音频静音（< -45dB 且 ≥ 0.4s）
sd = run(['ffmpeg', '-hide_banner', '-i', video, '-af', 'silencedetect=n=-45dB:d=0.4', '-vn', '-f', 'null', '-'])
print('静音片段:', re.findall(r'silence_(?:start|end): \S+', sd) or '无')
ln = run(['ffmpeg', '-hide_banner', '-i', video, '-af', 'ebur128=peak=true', '-vn', '-f', 'null', '-'])
print('响度:', ' '.join(re.findall(r'(I:\s+\S+ LUFS|Peak:\s+\S+ dBFS)', ln)[-2:]))

# 旁白—字幕同步：把成片音轨按每条字幕的起止切开识别，和字幕文本比对
sr = 16000
y = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                                 capture_output=True).stdout, np.float32)
d = asr + 'sherpa-onnx-whisper-base/'
en = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=d + 'base-encoder.int8.onnx', decoder=d + 'base-decoder.int8.onnx',
                                                tokens=d + 'base-tokens.txt', language='en', task='transcribe', num_threads=4)
d = asr + 'sherpa-onnx-paraformer-zh-2024-03-09/'
zh = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=d + 'model.int8.onnx', tokens=d + 'tokens.txt', num_threads=4)


def score(ref, hyp, lang):
    if lang == 'en':
        r = re.findall(r"[a-z']+", ref.lower().replace('’', "'")); h = set(re.findall(r"[a-z']+", hyp.lower()))
    else:
        r = [c for c in ref if '\u4e00' <= c <= '\u9fff']; h = set(hyp)
    return sum(w in h for w in r) / max(len(r), 1)


items = json.load(open(work + '/timeline.json'))['items']
bad = 0
for it in items:
    seg = y[int((it['start'] - 0.05) * sr):int((it['end'] + 0.05) * sr)]
    rec = en if it['lang'] == 'en' else zh
    s = rec.create_stream(); s.accept_waveform(sr, seg); rec.decode_stream(s)
    ref = it['en'] if it['lang'] == 'en' else it['zh']
    sc = score(ref, s.result.text, it['lang'])
    flag = 'OK ' if sc >= 0.7 else 'LOW'
    bad += sc < 0.7
    print('%s %5.1f-%5.1f %3.0f%%  %s  ||  %s' % (flag, it['start'], it['end'], sc * 100, ref[:40], s.result.text[:50]))
print('同步比对：%d 条字幕，%d 条低于 70%%' % (len(items), bad))
