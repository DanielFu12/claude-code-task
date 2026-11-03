"""质检辅助：把音频/视频/图片交给 Gemini 多模态模型“听/看”，按时间戳给出问题清单。

python3 src/review_ai.py FILE "提示词" [model]
大文件走 Files API 上传；响应用流式接口（避免网关 30s 超时）。
"""
import sys, os, json, time, urllib.request, mimetypes, base64

BASE = 'https://generativelanguage.googleapis.com'


def upload(path):
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    size = os.path.getsize(path)
    req = urllib.request.Request(f'{BASE}/upload/v1beta/files', method='POST', data=json.dumps(
        {'file': {'display_name': os.path.basename(path)}}).encode(), headers={
        'X-Goog-Upload-Protocol': 'resumable', 'X-Goog-Upload-Command': 'start',
        'X-Goog-Upload-Header-Content-Length': str(size), 'X-Goog-Upload-Header-Content-Type': mime,
        'Content-Type': 'application/json'})
    url = urllib.request.urlopen(req, timeout=120).headers['X-Goog-Upload-URL']
    req = urllib.request.Request(url, method='POST', data=open(path, 'rb').read(), headers={
        'X-Goog-Upload-Command': 'upload, finalize', 'X-Goog-Upload-Offset': '0', 'Content-Length': str(size)})
    f = json.load(urllib.request.urlopen(req, timeout=600))['file']
    while f.get('state') == 'PROCESSING':
        time.sleep(5)
        f = json.load(urllib.request.urlopen(f"{BASE}/v1beta/{f['name']}", timeout=60))
    return f['uri'], mime


def ask(path, prompt, model='gemini-3.8-flash'):
    mime = mimetypes.guess_type(path)[0]
    if os.path.getsize(path) > 15e6:
        uri, mime = upload(path)
        part = {'fileData': {'mimeType': mime, 'fileUri': uri}}
    else:
        part = {'inlineData': {'mimeType': mime, 'data': base64.b64encode(open(path, 'rb').read()).decode()}}
    body = {'contents': [{'parts': [part, {'text': prompt}]}],
            'generationConfig': {'thinkingConfig': {'thinkingLevel': os.environ.get('THINK', 'low')}}}
    for k in range(4):
        try:
            req = urllib.request.Request(f'{BASE}/v1beta/models/{model}:streamGenerateContent?alt=sse',
                                         data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
            out = []
            with urllib.request.urlopen(req, timeout=900) as r:
                for line in r:
                    line = line.decode().strip()
                    if line.startswith('data:'):
                        j = json.loads(line[5:])
                        for p in j.get('candidates', [{}])[0].get('content', {}).get('parts', []):
                            out.append(p.get('text', ''))
            return ''.join(out)
        except Exception as e:
            print('retry', k, e, file=sys.stderr); time.sleep(8 * (k + 1))
    raise RuntimeError('review failed')


if __name__ == '__main__':
    print(ask(sys.argv[1], sys.argv[2], *(sys.argv[3:4])))
