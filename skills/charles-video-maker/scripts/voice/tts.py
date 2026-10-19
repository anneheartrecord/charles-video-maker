#!/usr/bin/env python3
"""Synthesize the whole narration in one pass, then speed it up.

  tts.py narration.txt audio/voice.wav                       # Gemini TTS (needs GEMINI_API_KEY)
  tts.py narration.txt audio/voice.wav --backend edge        # edge-tts, free, no key
  tts.py narration.txt audio/voice.wav --backend kokoro      # Kokoro, offline, via the Lemo-Opuscar library
                                                             #   (sh scripts/lemo/setup.sh deps voice); English sounds good, Chinese plain
  tts.py narration.txt audio/voice.wav --speed 1.0           # keep the original pace

narration.txt: one paragraph per line, plain text, no stage directions.
Do not prepend style instructions such as "read this warmly": Gemini TTS reads them out loud.
"""
import argparse, base64, json, os, re, subprocess, sys, tempfile, urllib.request, wave


def gemini(text, out, voice, model):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        sys.exit('GEMINI_API_KEY is not set; use --backend edge for a free voice')
    body = {'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                                 data=json.dumps(body).encode(), headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
    part = json.load(urllib.request.urlopen(req, timeout=600))['candidates'][0]['content']['parts'][0]['inlineData']
    raw, mime = base64.b64decode(part['data']), part.get('mimeType', '')
    if 'wav' in mime:                                   # newer models return a WAV file
        open(out, 'wb').write(raw)
    else:                                               # older models return raw PCM: audio/L16;rate=24000
        rate = int(mime.split('rate=')[-1].split(';')[0]) if 'rate=' in mime else 24000
        with wave.open(out, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(raw)


def edge(text, out, voice):
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        mp3 = f.name
    subprocess.run(['edge-tts', '--voice', voice, '--text', text, '--write-media', mp3], check=True, capture_output=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp3, '-ac', '1', '-ar', '24000', out], check=True)
    os.unlink(mp3)


def kokoro(paras, out, voice):
    lib = os.environ.get('LEMO_OPUSCAR_HOME', os.path.expanduser('~/lemo-opuscar'))
    py, tts = os.path.join(lib, '.venv/bin/python'), os.path.join(lib, 'core/tts/tts.py')
    if not (os.path.exists(py) and os.path.exists(tts)):
        sys.exit(f'Kokoro is not installed in {lib}: run sh scripts/lemo/setup.sh deps voice')
    with tempfile.TemporaryDirectory() as d:
        cjk = lambda s: re.search('[\u4e00-\u9fff]', s)
        lines = [{'id': f'p{i:02d}', 'text': p, 'speed': 1.0, 'lang': 'cmn' if cjk(p) else 'en-us',
                  **({'voice': voice} if voice else {})} for i, p in enumerate(paras)]
        json.dump(lines, open(f'{d}/lines.json', 'w', encoding='utf-8'), ensure_ascii=False)
        subprocess.run([py, tts, f'{d}/lines.json', d], check=True, capture_output=True)
        frames, rate = b'', 24000
        for L in lines:                                 # one take: paragraphs joined with a 0.3 s breath
            with wave.open(f"{d}/{L['id']}.wav") as w:
                rate = w.getframerate(); frames += w.readframes(w.getnframes()) + b'\0\0' * int(.3 * rate)
        with wave.open(out, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(frames)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('narration'); ap.add_argument('out')
    ap.add_argument('--backend', choices=['gemini', 'edge', 'kokoro'], default='gemini')
    ap.add_argument('--voice', help='Gemini: Charon / Puck / Kore ...; edge: zh-CN-YunxiNeural ...; kokoro: zm_yunxi / am_michael ...')
    ap.add_argument('--model', default='gemini-3.8-flash-tts')
    ap.add_argument('--speed', type=float, default=1.25, help='atempo factor applied after synthesis (default 1.25)')
    a = ap.parse_args()
    paras = [l.strip() for l in open(a.narration, encoding='utf-8') if l.strip()]
    text = '\n\n'.join(paras)
    raw = a.out + '.raw.wav'
    if a.backend == 'gemini':
        gemini(text, raw, a.voice or 'Charon', a.model)
    elif a.backend == 'kokoro':
        kokoro(paras, raw, a.voice)
    else:
        edge(text, raw, a.voice or 'zh-CN-YunxiNeural')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af', f'atempo={a.speed}', a.out], check=True)
    os.unlink(raw)
    with wave.open(a.out) as w:
        print(f'{a.out}: {w.getnframes() / w.getframerate():.1f}s at {a.speed}x')


if __name__ == '__main__':
    main()
