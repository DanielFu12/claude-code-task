"""英文原声转写（离线：sherpa-onnx silero VAD + whisper small.en），供原声切点与逐句核对。
模型放在 ASR_DIR（默认 work/asr）：silero_vad.onnx、sherpa-onnx-whisper-small.en/（k2-fsa/sherpa-onnx releases 的 asr-models）。
python3 src/asr_en.py 媒体文件 [起-止秒]      # 逐段输出“起-止 | 文本”
"""
import sys, os, subprocess
import numpy as np, sherpa_onnx
A = os.environ.get('ASR_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'asr'))
src = sys.argv[1]
a, b = map(float, sys.argv[2].split('-')) if len(sys.argv) > 2 else (0.0, float(subprocess.run(
    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout))
x = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-t', str(b - a), '-i', src, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                                 capture_output=True).stdout, np.float32)
cfg = sherpa_onnx.VadModelConfig(); cfg.silero_vad.model = os.path.join(A, 'silero_vad.onnx')
cfg.silero_vad.min_silence_duration = 0.18; cfg.silero_vad.min_speech_duration = 0.2; cfg.silero_vad.max_speech_duration = 12; cfg.sample_rate = 16000
vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=200)
MD = os.environ.get('WHISPER', 'small.en')                      # WHISPER=tiny.en：快速粗转写，用来找段落；定稿核对用 small.en
M = os.path.join(A, 'sherpa-onnx-whisper-' + MD) + '/'
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=M + MD + '-encoder.int8.onnx', decoder=M + MD + '-decoder.int8.onnx',
                                                 tokens=M + MD + '-tokens.txt', num_threads=int(os.environ.get('THREADS', 4)))
def out(st, sm):
    s = rec.create_stream(); s.accept_waveform(16000, sm); rec.decode_stream(s)
    print(f'{a + st / 16000:.2f}-{a + (st + len(sm)) / 16000:.2f} | {s.result.text.strip()}', flush=True)


for i in range(0, len(x), 512):                      # 边检测边识别，逐段输出
    vad.accept_waveform(x[i:i + 512])
    while not vad.empty(): out(vad.front.start, np.array(vad.front.samples)); vad.pop()
vad.flush()
while not vad.empty(): out(vad.front.start, np.array(vad.front.samples)); vad.pop()
