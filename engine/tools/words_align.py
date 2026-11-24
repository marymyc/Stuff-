"""Word timings: projects/<name>/voice/voice.wav -> voice/words.json  [{"w": word, "s": start_s, "e": end_s}, ...]
Usage: python tools/words_align.py <name> [--model small.en]
Uses faster-whisper (or openai-whisper as a fallback). The transcript words are then matched to the script words
(difflib), so the spelling in words.json is the script's, with whisper's times. Always spot-check the result:
everything in the picture and the sound is timed to this file."""
import difflib, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import check_name, project_dir, voiceover_text

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
name = check_name(args[0])
model_name = args[args.index("--model") + 1] if "--model" in args else "small.en"
pd = project_dir(name)
wav = os.path.join(pd, "voice", "voice.wav")
if not os.path.exists(wav):
    sys.exit(f"missing {wav}: run tools/voice_tts.py {name} first")

heard = []
try:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="auto", compute_type="auto")
    segs, _ = model.transcribe(wav, word_timestamps=True, language="en", vad_filter=False)
    for s in segs:
        for w in s.words:
            heard.append({"w": w.word.strip(), "s": float(w.start), "e": float(w.end)})
except ImportError:
    import whisper
    model = whisper.load_model(model_name)
    res = model.transcribe(wav, word_timestamps=True, language="en")
    for s in res["segments"]:
        for w in s.get("words", []):
            heard.append({"w": w["word"].strip(), "s": float(w["start"]), "e": float(w["end"])})

norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
script_words = voiceover_text(os.path.join(pd, "SCRIPT.md")).split()
out = heard
if script_words:
    a, b = [norm(w["w"]) for w in heard], [norm(w) for w in script_words]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += [{"w": script_words[j1 + k], "s": heard[i1 + k]["s"], "e": heard[i1 + k]["e"]} for k in range(i2 - i1)]
        elif tag in ("replace", "insert"):
            s = heard[i1]["s"] if i1 < len(heard) else (heard[-1]["e"] if heard else 0.0)
            e = heard[i2 - 1]["e"] if i2 > i1 else s + 0.25 * (j2 - j1)
            n = j2 - j1
            for k in range(n):
                out.append({"w": script_words[j1 + k], "s": s + (e - s) * k / n, "e": s + (e - s) * (k + 1) / n})
    print(f"matched {sm.ratio() * 100:.0f}% of words to the script")
for w in out:
    w["s"], w["e"] = round(w["s"], 3), round(w["e"], 3)
json.dump(out, open(os.path.join(pd, "voice", "words.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"words.json: {len(out)} words, {out[0]['s']:.2f}-{out[-1]['e']:.2f} s" if out else "no words found")
