"""One command, run by the USER (never by an assistant or CI): script -> final MP4 with the hybrid pipeline.

    python tools/make.py script.txt --name short1 [--voice chatterbox] [--ref-voice clip.wav]
                         [--engine CYCLES] [--samples 12] [--scale 1.0] [--frames 0-89]

1 plan + voice + audio  2 cards (Canvas2D, no WebGL)  3 Blender renders the 3D world + cards  4 captions + audio mux
Set BLENDER_BIN to the blender executable (Blender 5.2). Cycles uses the GPU through CUDA/OptiX, no OpenGL needed.
"""
import argparse, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, **kw):
    print(">", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT, **kw)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("--name", default="short")
    ap.add_argument("--voice", default="chatterbox", choices=["chatterbox", "silent"]); ap.add_argument("--ref-voice")
    ap.add_argument("--engine", default="CYCLES", choices=["CYCLES", "EEVEE"]); ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--frames", default="", help="e.g. 0-89 to render only a preview range")
    ap.add_argument("--format", default="JPEG", choices=["JPEG", "PNG"]); ap.add_argument("--font", default="DejaVu Sans")
    ap.add_argument("--skip-plan", action="store_true"); ap.add_argument("--skip-cards", action="store_true"); ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--blender", default=os.environ.get("BLENDER_BIN") or shutil.which("blender") or "blender")
    a = ap.parse_args()
    py = sys.executable
    if not a.skip_plan:
        run([py, "tools/make_hybrid_plan.py", os.path.abspath(a.script), "--voice", a.voice] + (["--ref-voice", a.ref_voice] if a.ref_voice else []))
    if not a.skip_cards:
        run(["node", "scripts/export-cards.mjs", "--entry", "src/scene/cards.ts", "--story", "src/scene/story.ts", "--out", "out/cards"])
    if not a.skip_render:
        cmd = [a.blender, "-b", "-noaudio", "-P", "scripts/blender_render.py", "--", "--plan", "public/plan.json", "--cards", "out/cards", "--out", "out/blender_frames",
               "--engine", a.engine, "--samples", str(a.samples), "--scale", str(a.scale), "--format", a.format]
        if a.frames:
            cmd += ["--frames", a.frames]
        run(cmd)
    ext = "jpg" if a.format == "JPEG" else "png"
    out = f"out/{a.name}.mp4"
    run(["node", "scripts/composite_stage2.mjs", "--frames", "out/blender_frames", "--audio", "public/audio/mix.wav", "--words", "public/audio/words.json",
         "--out", out, "--format", ext, "--font", a.font])
    print("DONE ->", os.path.join(ROOT, out))
