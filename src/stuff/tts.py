"""Fixed-identity narration. Backends: chatterbox (real) and silent (tests only)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from .planner import WPS


def trim_silence(x, sr, thresh=0.01, pad=0.04):
    idx = np.where(np.abs(x) > thresh)[0]
    if idx.size == 0:
        return x
    return x[max(0, idx[0] - int(pad * sr)): min(len(x), idx[-1] + int(pad * sr))]


class SilentVoice:
    sr = 24000

    def synth(self, text, seed):
        return np.zeros(int(self.sr * max(1.2, len(text.split()) / WPS)), dtype=np.float32)


class ChatterboxVoice:
    def __init__(self, vcfg):
        import torch
        from chatterbox.tts import ChatterboxTTS

        self.torch = torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = ChatterboxTTS.from_pretrained(device=device)
        self.sr = self.model.sr
        self.ex, self.cfg, self.temp = vcfg["exaggeration"], vcfg["cfg_weight"], vcfg["temperature"]
        ref = vcfg.get("reference_wav")
        if ref:
            self.model.prepare_conditionals(str(ref), exaggeration=self.ex)  # prepared once, reused for all shots

    def synth(self, text, seed):
        torch = self.torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        wav = self.model.generate(text, exaggeration=self.ex, cfg_weight=self.cfg, temperature=self.temp)
        return wav.squeeze(0).detach().cpu().numpy().astype("float32")


def get_voice(vcfg):
    if vcfg["backend"] == "silent":
        return SilentVoice()
    if vcfg["backend"] == "chatterbox":
        return ChatterboxVoice(vcfg)
    raise ValueError(f"unknown voice backend {vcfg['backend']}")


def voice_fingerprint(vcfg) -> str:
    h = hashlib.sha256(json.dumps({k: vcfg[k] for k in ("backend", "seed", "exaggeration", "cfg_weight", "temperature")},
                                  sort_keys=True).encode())
    ref = vcfg.get("reference_wav")
    if ref and Path(ref).exists():
        h.update(Path(ref).read_bytes())
    return h.hexdigest()[:16]


def synthesize_plan(plan, workdir, cfg, force=False) -> dict:
    vdir = Path(workdir) / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    vcfg = cfg["voice"]
    mpath = Path(workdir) / "voice_manifest.json"
    fp = voice_fingerprint(vcfg)
    if mpath.exists() and not force:
        m = json.loads(mpath.read_text())
        if m.get("fingerprint") == fp and len(m["shots"]) == len(plan["shots"]) and \
                all(Path(s["wav"]).exists() for s in m["shots"]) and \
                all(a["text"] == b["text"] for a, b in zip(m["shots"], plan["shots"])):
            return m
    voice = get_voice(vcfg)
    shots = []
    for s in plan["shots"]:
        x = voice.synth(s["text"], vcfg["seed"])
        if vcfg["backend"] != "silent":
            x = trim_silence(x, voice.sr)
        p = vdir / f"shot_{s['id']:03d}.wav"
        sf.write(p, x, voice.sr)
        shots.append({"id": s["id"], "text": s["text"], "wav": str(p), "sr": int(voice.sr),
                      "duration": round(len(x) / voice.sr, 3)})
    m = {"fingerprint": fp, "backend": vcfg["backend"], "seed": vcfg["seed"],
         "reference_wav": vcfg.get("reference_wav"), "shots": shots}
    mpath.write_text(json.dumps(m, indent=2))
    return m
