import json, sys
from faster_whisper import WhisperModel
m = WhisperModel('medium.en', device='cpu', compute_type='int8', cpu_threads=4)
import soundfile as sf; aud, _ = sf.read(sys.argv[1], dtype='float32')
segs, info = m.transcribe(aud, word_timestamps=True, beam_size=5, language='en', vad_filter=False)
out = []
for s in segs:
    for w in s.words:
        out.append([w.start, w.end, w.word, w.probability])
    print(f'{s.start:7.2f} {s.end:7.2f} {s.text}', flush=True)
json.dump(out, open(sys.argv[2], 'w'))
