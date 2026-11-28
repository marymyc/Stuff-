# Ricks Clips / Brain Snack v5.1 Style Bible

Rules distilled directly from frame-by-frame analysis of real `@RicksClips3000` Shorts (`NpRAk-5VKlo`, `7dGWuCeZ8Ic`, `5c432c69934a7f15` railroad Short, `7xS87iActkU`, dashcam/gunfighter benchmarks) and the 7 quantitative film grammar laws.

## 1. Story, Scene Variety & Narration Architecture (45-68s)
Real `@RicksClips3000` Shorts never trap the viewer in 3 static rooms for 50 seconds. They move briskly across **10-14+ distinct locations, POV inserts, windows, vehicles, or visual gags** (~3.5-5s per space) driven by one brisk narrator voice:

1. **0-5s Hook & Fast Kicker (2 spaces):** Open directly on the protagonist inside a grounded setting (`<= 2.5s` first hero face), then whip onto a crisp close-up clue, headline, or problem prop (`LE JOURNAL`, poster, radar screen).
2. **5-18s Setup & Stakes (2-3 spaces):** Jump into forged prep / secret room / ensemble briefing (`5+` cast reacting together) as tension climbs.
3. **18-32s The Deal / Attempt (2-3 spaces + 3D Action Props):** Animate actual 3D world props (sliding documents across desks, slamming seals/stamps, opening briefcases, digging/building) synced to character squash-and-recoil reactions.
4. **32-48s Escape / Failure / Twist (`day -> night -> golden -> day`):** Keep physical momentum high across transport interiors (moving exterior trees past windows), speeding exteriors (spinning wheels/cars), dramatic low-angle sky cranes, moody night alleys/phone booths, and sudden lightbulb epiphanies.
5. **48-65s Climax & Punchline:** Peak meme reaction (`meme_shock`, glowing sirens) -> high-energy sprint/chase camera -> soaring crane pull-back onto the iconic landmark & irony billboard + sting.

**Voice Pacing & Audio Targets:**
- **Speech Speed:** `3.5-4.1 words/sec` (`~3.7 w/s` sweet spot).
- **Tight Gaps:** Trim leading/trailing TTS breaths (`-55 dB`); keep gaps between lines `0.15-0.28s` (`<= 0.32s` max everywhere).
- **Dynamic Loudness:** Master voice + SFX + underscore bed to **`-15.0 LUFS` integrated / `-3.2 dBFS` (`<= -1.2 dBTP`)**.

## 2. The 7 Quantitative Film Grammar Laws
1. **Never Freeze the Camera (`Rule 1`):** Camera must never sit dead static (`0%` held frames in QA). Keep continuous `push()` creep, synchronized chase tracking (`mix(x0, x1, smooth(u))` matching character motion!), and subtle handheld/impact shakes (`kickAt`).
2. **Respect 9:16 Horizontal Width & Top-Hat Headroom (`Rule 2`):** Vertical `fov 38-48 deg` in 9:16 yields narrow horizontal width (`2 * dist * tan(vfov/2) * 9/16`). Export actor cards at `900x1680` (`designW: 600, designH: 1120, soleY: 1080, heightM: 2.15`) and drive leaps via 3D `pos[1]` rather than shoving crowns into the top of the 2D bitmap. Always check wide table ensembles, locomotive trackside framing (clear foreground poles!), and jump apexes across preview frames so characters, top hats, flanking bosses, and signs keep clean edge margins.
3. **High-Location Velocity Inside Validated Shot Bounds (`Rule 3`):** Keep `<= 12` `plan.json` shots (`avg >= 4.5s`) while packing **10-14 distinct 3D locations / angles** via `KEYS` (`cut: true` + `"planned"` whip frame entries + continuous `16-26f` whips) and per-frame `lightAt(f)` mood switches.
4. **First Face Early (`Rule 4`):** Hero face MUST appear clearly inside frame by `<= 2.5s`.
5. **Outline-FREE Multi-Part PBR 3D Worlds + Stylish Mood Contrast (`Rule 5`):** Keep 3D buildings, rooms, furniture, tracks, and vehicles clean outline-FREE PBR (`--ink` off by default) built with genuine beveled multi-part `bmesh` detail (open-spoked rotating wheels on unrotated XZ pivots synced with rods, I-beam rails + sleepers + ballast, dialed rotary phones, handled cups) paired with rich sky ramps (`day` cerulean, `golden` warm amber, `night` twilight/indigo, `interior` tungsten sconce lighting) so `#1f1526` bold-ink 2D characters pop crisply off the world.
6. **Snap-and-Hold Acting & Grounded Physics (`Rule 6`):** Drive characters at **30fps on ones** (`addLivingSeq`) with purposeful snap-and-hold pose discipline rather than continuous idle sine wobble. Every jump MUST use the 3-phase `jumpState` arc (6f `knees` crouch anticipation -> airborne 3D `pos[1]` arc with folded knees -> 7f landing absorb), runs MUST keep planted stride ground contact (`runHop` only at full stride peak), active hand props (`stamp`, `briefcase`, `contract`) MUST be gripped cleanly inside the character hand (never ghosted autonomously in 3D), and **third-person narration keeps `mouthOpen: "auto"` static expressive beat faces**.
7. **Props Alive in World + Hero Frame Coverage (`Rule 7`):** Every key noun (`seal`, `contract`, `stamp`, `train`, `phone`, `lightbulb`, `sign`) sits cleanly inside the active camera frustum (`validate_plan.py` 40/40 PASS) with articulated 3D geometry and physical `update_frame` animation (spinning spoked wheels + rods, passing poles/trees, stamped ink reveals, flashing sirens).

## 3. Captions & Packaging
- **Captions (`composite_stage2.mjs` & `CaptionsOverlay.tsx`):** `Arial Black` / `Roboto 900`, **`98px` ASS (`MarginV=530`), pure bright `#FFFFFF` with heavy `10px` `#000000` outline** (`--yellow-emphasis` strictly opt-in). Keep `1-2` short punchy words centered just below the mid-line eye zone (`MarginV=530`) in natural case matching `@RicksClips3000`.
- **Shorts Title:** `5-7` words in Title Case naming the concrete hook + irony.
- **Description & Tags:** `1-2` crisp factual sentences plus `4` broad topic hashtags (`#shorts #truestory ...`).
