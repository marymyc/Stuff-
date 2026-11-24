"""Start a new short from the proven bridge template.
Usage: python tools/new_short.py <name> [path/to/your_script.md]
  - copies src/videos/bridge -> src/videos/<name>   (picture code: the look stays, the story gets rewritten)
  - registers composition <Name>Short in src/Root.tsx
  - creates projects/<name>/ with SCRIPT.md, voice/, audio/ (sound code copied from projects/bridge/audio) and STATUS.md
"""
import os, shutil, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, check_name, comp_id, project_dir, video_dir

if len(sys.argv) < 2:
    sys.exit(__doc__)
name = check_name(sys.argv[1])
script = sys.argv[2] if len(sys.argv) > 2 else None
vd, pd, cid = video_dir(name), project_dir(name), comp_id(name)
if os.path.exists(vd) or os.path.exists(pd):
    sys.exit(f"{name} already exists (src/videos/{name} or projects/{name}). Resume it: read projects/{name}/STATUS.md")

shutil.copytree(os.path.join(ROOT, "src/videos/bridge"), vd)
os.makedirs(os.path.join(pd, "voice"))
shutil.copytree(os.path.join(ROOT, "projects/bridge/audio"), os.path.join(pd, "audio"),
                ignore=shutil.ignore_patterns("*.wav", "__pycache__", "cues_reference.md"))
shutil.copy2(script or os.path.join(ROOT, "SCRIPT_TEMPLATE.md"), os.path.join(pd, "SCRIPT.md"))

root = os.path.join(ROOT, "src/Root.tsx")
src = open(root, encoding="utf-8").read()
up = cid.upper()
imp = f'import {{ BridgeShort as {cid}, BRIDGE_FRAMES as {up}_FRAMES }} from "./videos/{name}/Bridge";\n// @@IMPORTS@@'
comp = (f'<Composition id="{cid}" component={{{cid}}} durationInFrames={{{up}_FRAMES}} fps={{30}} '
        f'width={{1080}} height={{1920}} />\n    {{/* @@COMPOSITIONS@@ */}}')
src = src.replace("// @@IMPORTS@@", imp, 1).replace("{/* @@COMPOSITIONS@@ */}", comp, 1)
open(root, "w", encoding="utf-8").write(src)

status = f"""# STATUS - {name}
Composition: `{cid}`  |  picture: `src/videos/{name}/`  |  voice + sound: `projects/{name}/`
Created {time.strftime('%Y-%m-%d %H:%M')}. Any agent resuming this short: read AGENTS.md, then continue from the first unchecked step.

- [ ] 1 Facts + sources at the top of SCRIPT.md
- [ ] 2 Script final (55-70 s, ~3.7 words/s, beat formula) - approved by the user
- [ ] 3 voice/voice.wav (48 kHz) + voice/words.json (checked)
- [ ] 4 story.ts rewritten: SHOTS, XFADE, FLASH_AT, CAMS, KICKS, DOF, FOREGROUND timed to words.json
- [ ] 5 World rewritten (build.ts layout and props) - look values untouched
- [ ] 6 Characters and roles rewritten (cast.ts; toon.ts faces/poses if needed)
- [ ] 7 Typecheck passes, stills reviewed against references
- [ ] 8 Sound: timeline.py / sfx.py / music.py / mix.py updated, mix.wav made
- [ ] 9 Final render + mux + QA clean
- [ ] 10 Delivered: out/{name}/final.mp4

## Notes / decisions
"""
open(os.path.join(pd, "STATUS.md"), "w", encoding="utf-8").write(status)
print(f"created src/videos/{name}/, projects/{name}/ and composition {cid}")
print(f"next: finish projects/{name}/SCRIPT.md, then: python tools/voice_tts.py {name}")
