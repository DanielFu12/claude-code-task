import sys, json, base64, urllib.request, mimetypes, time
def ask(model, prompt, files=(), temp=0.4):
    parts = []
    for f in files:
        mt = mimetypes.guess_type(f)[0] or "audio/wav"
        parts.append({"inlineData": {"mimeType": mt, "data": base64.b64encode(open(f, "rb").read()).decode()}})
    parts.append({"text": prompt})
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": temp}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=600).read())
    except urllib.error.HTTPError as e:
        return "HTTP %d %s" % (e.code, e.read().decode()[:600])
    return "".join(p.get("text", "") for c in d.get("candidates", []) for p in c["content"]["parts"])
if __name__ == "__main__":
    print(ask(sys.argv[1], sys.argv[2], sys.argv[3:]))
