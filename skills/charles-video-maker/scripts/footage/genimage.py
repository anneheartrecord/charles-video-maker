#!/usr/bin/env python3
"""Generate a still for a shot that no recording or stock clip covers (an abstract idea, a historical scene).

  genimage.py "a quiet porcelain kiln at dawn, smoke, warm light, cinematic" source/footage/kiln.png --aspect 9:16

Gemini image model (GEMINI_API_KEY). compose.py moves the still (push / pull / pan), so it plays like footage.
Every prompt gets the house rules appended: no text in the picture, no recognisable real people, no logos.
Logged in source/credits.md as generated.
"""
import argparse, base64, json, os, sys, urllib.error, urllib.request

RULES = ' No text, letters or watermarks in the image. No real, recognisable people and no human faces in close-up. No brand logos.'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prompt'); ap.add_argument('out')
    ap.add_argument('--aspect', default='9:16', help='9:16, 16:9, 1:1, 3:4, 4:3')
    ap.add_argument('--model', default='gemini-3.1-flash-image', help='or gemini-3-pro-image for harder scenes')
    a = ap.parse_args()
    key = os.environ.get('GEMINI_API_KEY') or sys.exit('GEMINI_API_KEY is not set')
    body = {'contents': [{'parts': [{'text': a.prompt + RULES}]}],
            'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': a.aspect}}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{a.model}:generateContent',
                                 data=json.dumps(body).encode(), headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
    try:
        parts = json.load(urllib.request.urlopen(req, timeout=300))['candidates'][0]['content']['parts']
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read() or b'{}').get('error', {}).get('message', '')[:200]
        sys.exit(f'{a.model}: HTTP {e.code} {msg}' + ('\n  image quota used up: enable billing for this key (https://ai.dev/rate-limit), or fill the shot with stock or a recording' if e.code == 429 else ''))
    img = next((p['inlineData'] for p in parts if 'inlineData' in p), None) or sys.exit(f'no image returned: {parts}')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, 'wb').write(base64.b64decode(img['data']))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from source import credit
    credit(f'- `{os.path.basename(a.out)}` · 生成（{a.model}）· 提示词：{a.prompt} · 补位')
    print(f'{a.out}: {img.get("mimeType")} from {a.model}')


if __name__ == '__main__':
    main()
