"""用 Gemini 的音频理解对 A/B 试听包做第二意见：A = 参照段，B = 新合成段，是否同一说话人、同一风格。
用法：python3 tools/ab_judge.py work/ab/*.wav（只作参考；最终以人耳为准）"""
import base64, json, os, ssl, subprocess, sys, urllib.request

MODEL = 'gemini-3.1-pro-preview'
PROMPT = ('This audio has two parts separated by a short beep. Part A (before the beep) is the reference Mandarin documentary narrator; '
          'Part B (after the beep) is a newly generated take. Judge strictly by ear: (1) same speaker voice/timbre? '
          '(2) same pitch register? (3) same delivery style and pace? Reply in JSON: {"same_speaker":true/false, '
          '"timbre":1-10, "pitch_register":1-10, "style":1-10, "notes":"short Chinese note on any audible difference"}')


def judge(path):
    mp3 = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', '1', '-b:a', '96k', '-f', 'mp3', '-'], capture_output=True, check=True).stdout
    body = {'contents': [{'parts': [{'inline_data': {'mime_type': 'audio/mp3', 'data': base64.b64encode(mp3).decode()}}, {'text': PROMPT}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    ctx = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
    r = json.load(urllib.request.urlopen(req, timeout=300, context=ctx))
    return r['candidates'][0]['content']['parts'][-1]['text']


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(os.path.basename(p), judge(p), flush=True)
