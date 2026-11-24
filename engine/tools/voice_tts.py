"""Make projects/<name>/voice/voice.wav (48 kHz mono, 24-bit) from the '## Voiceover' section of SCRIPT.md.
Usage: python tools/voice_tts.py <name> [--engine elevenlabs|openai|kokoro|manual]
  elevenlabs : ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID. Also writes words.json directly (character timestamps).
  openai     : OPENAI_API_KEY (+ OPENAI_TTS_VOICE). Run tools/words_align.py afterwards.
  kokoro     : free, local, offline after first model download (python packages kokoro + soundfile).
  manual     : you record it yourself: put any audio file at voice/raw.* and this converts it to voice.wav.
One steady tone, English. Settings in .env (see .env.example)."""
import base64, glob, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import check_name, load_env, project_dir, voiceover_text

load_env()
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
name = check_name(args[0])
engine = args[args.index("--engine") + 1] if "--engine" in args else os.environ.get("TTS_ENGINE", "elevenlabs")
pd = project_dir(name)
vdir = os.path.join(pd, "voice")
os.makedirs(vdir, exist_ok=True)
text = voiceover_text(os.path.join(pd, "SCRIPT.md"))
if engine != "manual" and len(text.split()) < 20:
    sys.exit("SCRIPT.md has no usable '## Voiceover' section")
raw = os.path.join(vdir, "raw_tts")
out = os.path.join(vdir, "voice.wav")


def to48k(src):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s24le", out], check=True)


def words_from_chars(al):
    chars, s, e = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, t0, t1 = [], "", None, None
    for c, a, b in zip(chars, s, e):
        if c.isspace():
            if cur:
                words.append({"w": cur, "s": round(t0, 3), "e": round(t1, 3)})
            cur, t0 = "", None
            continue
        if t0 is None:
            t0 = a
        cur += c
        t1 = b
    if cur:
        words.append({"w": cur, "s": round(t0, 3), "e": round(t1, 3)})
    return words


if engine == "elevenlabs":
    import requests
    key, vid = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not vid:
        sys.exit("set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env")
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps",
                      params={"output_format": "mp3_44100_192"}, headers={"xi-api-key": key},
                      json={"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                            "voice_settings": {"stability": 0.7, "similarity_boost": 0.8, "style": 0.0}}, timeout=300)
    r.raise_for_status()
    j = r.json()
    open(raw + ".mp3", "wb").write(base64.b64decode(j["audio_base64"]))
    to48k(raw + ".mp3")
    al = j.get("normalized_alignment") or j.get("alignment")
    if al:
        json.dump(words_from_chars(al), open(os.path.join(vdir, "words.json"), "w"), indent=1)
        print("words.json written from ElevenLabs timestamps (still check it)")
elif engine == "openai":
    import requests
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("set OPENAI_API_KEY in .env")
    r = requests.post("https://api.openai.com/v1/audio/speech", headers={"Authorization": f"Bearer {key}"},
                      json={"model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "input": text,
                            "voice": os.environ.get("OPENAI_TTS_VOICE", "onyx"), "response_format": "wav",
                            "instructions": "Calm, dry, deadpan documentary narrator. One steady tone, no acting."}, timeout=300)
    r.raise_for_status()
    open(raw + ".wav", "wb").write(r.content)
    to48k(raw + ".wav")
elif engine == "kokoro":
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a")
    parts = [a for _, _, a in pipe(text, voice=os.environ.get("KOKORO_VOICE", "am_michael"), speed=1.0, split_pattern=r"\n+")]
    gap = np.zeros(int(24000 * 0.25), dtype=np.float32)
    audio = np.concatenate([np.concatenate([np.asarray(p, dtype=np.float32), gap]) for p in parts])
    sf.write(raw + ".wav", audio, 24000)
    to48k(raw + ".wav")
elif engine == "manual":
    cands = [p for p in glob.glob(os.path.join(vdir, "raw.*"))]
    if not cands:
        sys.exit(f"record the voice-over and save it as {vdir}/raw.wav (or .mp3/.m4a), then run this again")
    to48k(cands[0])
else:
    sys.exit(f"unknown engine {engine}")

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                           capture_output=True, text=True).stdout or 0)
print(f"voice.wav: {dur:.2f} s, {len(text.split())} words, {len(text.split()) / max(dur, 1e-6):.2f} words/s (target ~3.7, 55-70 s)")
if not os.path.exists(os.path.join(vdir, "words.json")):
    print(f"next: python tools/words_align.py {name}")
