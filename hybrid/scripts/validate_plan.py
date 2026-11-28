#!/usr/bin/env python3
"""
40-check deterministic pre-render plan validator for ricks-clips-animation v2.
Catches timing, camera motion, AABB collisions, invisible spoken props,
mid-speech blinks, and lighting/packaging mistakes BEFORE GPU rendering.

Usage:
  python scripts/validate_plan.py [public/plan.json] [public/audio/words.json] [--starter]
"""
import argparse
import json
import math
import os
import re
import sys
from typing import Any


def norm_tok(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def overlap_interval(a0: int, a1: int, b0: int, b1: int) -> bool:
    return max(a0, b0) < min(a1, b1)


def dist3(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def vec_norm(v: list[float]) -> list[float]:
    m = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / m for c in v]


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate master Short plan (40 checks).")
    ap.add_argument("plan", nargs="?", default="public/plan.json")
    ap.add_argument("words", nargs="?", default="public/audio/words.json")
    ap.add_argument("--starter", action="store_true", help="Allow 5s starter demo timing")
    args = ap.parse_args()

    if not os.path.exists(args.plan):
        print(f"[FAIL] Missing plan file: {args.plan}")
        return 1
    if not os.path.exists(args.words):
        print(f"[FAIL] Missing words file: {args.words}")
        return 1

    with open(args.plan, encoding="utf-8") as f:
        plan: dict[str, Any] = json.load(f)
    with open(args.words, encoding="utf-8") as f:
        words_doc: dict[str, Any] = json.load(f)

    results: list[tuple[str, str, str]] = []

    def check(cid: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        results.append((cid, status, detail))

    fps = float(plan.get("fps", 30))
    total_frames = int(plan.get("totalFrames", words_doc.get("totalFrames", 0)))
    words = words_doc.get("words", [])
    dur = float(words_doc.get("durationSec", total_frames / max(1.0, fps)))
    shots = plan.get("shots", [])
    actors = plan.get("actors", [])
    props = plan.get("props", [])
    flags = plan.get("flags", {})

    # --- A. Audio & Script Pacing (01-08) ---
    check("01_words_present", len(words) >= 4, f"{len(words)} aligned word tokens")
    dur_ok = (4.0 <= dur <= 75.0) if args.starter else (35.0 <= dur <= 72.0)
    check("02_duration_range", dur_ok, f"{dur:.2f}s (starter={args.starter})")

    speech_time = max(0.5, (words[-1]["e"] - words[0]["s"]) if len(words) >= 2 else dur)
    wps = len(words) / speech_time
    wps_ok = (1.4 <= wps <= 4.6) if args.starter else (2.3 <= wps <= 4.35)
    check("03_word_rate", wps_ok, f"{wps:.2f} words/sec over active speech")

    first_s = float(words[0]["s"]) if words else 99.0
    check("04_lead_in_start", first_s <= 0.35, f"first word at {first_s:.3f}s (<= 0.35s)")

    gaps = [float(words[i + 1]["s"]) - float(words[i]["e"]) for i in range(len(words) - 1)]
    max_gap = max(gaps) if gaps else 0.0
    check("05_max_gap_silence", max_gap <= 0.42, f"max inter-word silence {max_gap:.3f}s (<= 0.42s)")

    trail_gap = dur - float(words[-1]["e"]) if words else dur
    check("06_no_trailing_dead_air", trail_gap <= 1.25, f"trailing tail {trail_gap:.3f}s (<= 1.25s)")

    mono_ok = all(words[i]["s"] <= words[i]["e"] <= dur + 0.05 for i in range(len(words))) and all(
        words[i]["s"] <= words[i + 1]["s"] + 1e-4 for i in range(len(words) - 1)
    )
    check("07_word_monotonic", mono_ok, "non-decreasing word intervals inside total duration")

    lines = words_doc.get("lines", {})
    lines_ok = bool(lines) and all(v.get("s", 0) < v.get("e", 0) for v in lines.values())
    check("08_line_mapping", lines_ok, f"{len(lines)} line span entries")

    # --- B. Camera & Long-Shot Film Grammar (09-18) ---
    min_face = min((float(a.get("firstFaceSec", 99.0)) for a in actors), default=99.0)
    check("09_early_first_face", min_face <= 2.8, f"first face at {min_face:.2f}s (<= 2.8s)")

    shot_durs = [(s.get("b", 0) - s.get("a", 0)) / fps for s in shots]
    avg_shot = sum(shot_durs) / max(1, len(shot_durs))
    cuts_ok = (avg_shot >= 2.0) if args.starter else (avg_shot >= 2.0)
    check("10_minimal_hard_cuts", cuts_ok, f"{len(shots)} shots, avg {avg_shot:.2f}s/shot")

    cov_ok = False
    if shots:
        s_sorted = sorted(shots, key=lambda x: x.get("a", 0))
        cov_ok = s_sorted[0].get("a", -1) == 0 and s_sorted[-1].get("b", -1) == total_frames
        for idx in range(len(s_sorted) - 1):
            if s_sorted[idx].get("b") != s_sorted[idx + 1].get("a"):
                cov_ok = False
    check("11_shot_coverage", cov_ok, f"contiguous coverage 0..{total_frames}")

    fov_ok = bool(shots) and all(30.0 <= float(s.get("fov", 40.0)) <= 52.0 for s in shots)
    check("12_camera_fov_wide", fov_ok, "all shots use 30-52 deg wide framing")

    floor_ok = bool(shots) and all(
        float(s.get("camStart", [0, 0, 0])[1]) >= 0.4 and float(s.get("camEnd", [0, 0, 0])[1]) >= 0.4
        for s in shots
    )
    check("13_camera_floor_clearance", floor_ok, "all cameras >= 0.4m above ground")

    travels = [dist3(s.get("camStart", [0, 0, 0]), s.get("camEnd", [0, 0, 0])) for s in shots]
    check("14_camera_travel_distance", bool(travels) and all(d >= 0.45 for d in travels), f"min cam travel {min(travels or [0.0]):.2f}m")

    land_frames_total = sum(
        max(0, int(s["landFrames"][1]) - int(s["landFrames"][0]))
        for s in shots if isinstance(s.get("landFrames"), list) and len(s["landFrames"]) == 2
    )
    glide_ratio = (total_frames - land_frames_total) / max(1, total_frames)
    check("15_glide_motion_ratio", 0.55 <= glide_ratio <= 0.96, f"glide share {glide_ratio * 100:.1f}% (target 55-95%)")

    land_ok = bool(shots) and all(
        isinstance(s.get("landFrames"), list) and len(s["landFrames"]) == 2 and 2 <= (s["landFrames"][1] - s["landFrames"][0]) <= 24
        for s in shots
    )
    check("16_land_hold_budget", land_ok, "every shot settles 2-24f cleanly on landing")

    punch_ok = bool(shots) and all(len(s.get("punchWords", [])) >= 1 for s in shots)
    check("17_punch_on_settle", punch_ok, "every shot specifies punchWords for landing beat")

    valid_lights = {"day", "golden", "interior", "night"}
    light_ok = bool(shots) and all(s.get("light") in valid_lights for s in shots)
    check("18_lighting_preset_valid", light_ok, "all shot lighting presets recognized")

    # --- C. Spatial Staging & AABB Collision (19-28) ---
    check("19_actors_present", len(actors) >= 1, f"{len(actors)} actors defined")

    grounded_ok = all(
        not a.get("grounded", True) or abs(float(a.get("pos", [0, 0, 0])[1])) <= 0.05
        for a in actors
    )
    check("20_actors_grounded", grounded_ok, "grounded actors rest cleanly on Y=0")

    aa_ok = True
    min_aa = 99.0
    for i in range(len(actors)):
        for j in range(i + 1, len(actors)):
            p0, p1 = actors[i].get("pos", [0, 0, 0]), actors[j].get("pos", [0, 0, 0])
            d_xz = math.hypot(p0[0] - p1[0], p0[2] - p1[2])
            min_aa = min(min_aa, d_xz)
            if d_xz < 0.55:
                aa_ok = False
    check("21_actor_actor_clearance", aa_ok, f"min actor separation {min_aa if actors[1:] else 9.9:.2f}m")

    ap_hits = []
    for a in actors:
        ax, ay, az = a.get("pos", [0, 0, 0])
        ar = float(a.get("radius", 0.32))
        ah = float(a.get("height", 1.9))
        for p in props:
            b = p.get("aabb", [0, 0, 0, 0, 0, 0])
            # Ignore flat floor slabs (height <= 0.12) and overhead canopies
            if (b[4] - b[1]) <= 0.12 or b[1] > ay + ah:
                continue
            ov_x = max(0.0, min(ax + ar, b[3]) - max(ax - ar, b[0]))
            ov_z = max(0.0, min(az + ar, b[5]) - max(az - ar, b[2]))
            ov_y = max(0.0, min(ay + ah, b[4]) - max(ay + 0.15, b[1]))
            if ov_x > 0.10 and ov_z > 0.10 and ov_y > 0.10:
                ap_hits.append(f"{a.get('id')}<->{p.get('id')}")
    check("22_actor_prop_clearance", not ap_hits, f"overlaps={ap_hits}" if ap_hits else "0 actor-prop collisions")

    pp_hits = []
    for i in range(len(props)):
        for j in range(i + 1, len(props)):
            p0, p1 = props[i], props[j]
            v0, v1 = p0.get("visibleFrames", [0, total_frames]), p1.get("visibleFrames", [0, total_frames])
            if not overlap_interval(v0[0], v0[1], v1[0], v1[1]):
                continue
            a, b = p0.get("aabb", [0] * 6), p1.get("aabb", [0] * 6)
            if (a[4] - a[1]) <= 0.12 or (b[4] - b[1]) <= 0.12:
                continue
            ox = min(a[3], b[3]) - max(a[0], b[0])
            oy = min(a[4], b[4]) - max(a[1], b[1])
            oz = min(a[5], b[5]) - max(a[2], b[2])
            if ox > 0.15 and oy > 0.15 and oz > 0.15:
                pp_hits.append(f"{p0.get('id')}<->{p1.get('id')}")
    check("23_prop_prop_overlap", not pp_hits, f"overlaps={pp_hits}" if pp_hits else "0 solid prop collisions")

    props_g_ok = all(
        not p.get("grounded", True) or abs(float(p.get("aabb", [0] * 6)[1])) <= 0.08
        for p in props
    )
    check("24_props_grounded", props_g_ok, "all grounded props sit flush on floor")

    spoken_tokens = {norm_tok(w["w"]) for w in words}
    kw_props = [p for p in props if p.get("keywords")]
    kw_missing = [
        f"{p.get('id')}:{kw}"
        for p in kw_props
        for kw in p.get("keywords", [])
        if norm_tok(kw) not in spoken_tokens
    ]
    check("25_prop_keywords_cover", not kw_missing, f"missing={kw_missing}" if kw_missing else f"{len(kw_props)} keyword-bound props matched")

    frustum_ok = True
    frustum_detail = "ok"
    for p in kw_props:
        b = p.get("aabb", [0] * 6)
        pc = [(b[0] + b[3]) * 0.5, (b[1] + b[4]) * 0.5, (b[2] + b[5]) * 0.5]
        # Check against shots overlapping prop visibility window
        pv = p.get("visibleFrames", [0, total_frames])
        visible_in_any = False
        for s in shots:
            if not overlap_interval(s["a"], s["b"], pv[0], pv[1]):
                continue
            cam_mid = [(s["camStart"][i] + s["camEnd"][i]) * 0.5 for i in range(3)]
            fwd = vec_norm([s["lookAt"][i] - cam_mid[i] for i in range(3)])
            to_p = vec_norm([pc[i] - cam_mid[i] for i in range(3)])
            dot = sum(fwd[i] * to_p[i] for i in range(3))
            if dot > 0.25:
                visible_in_any = True
        if not visible_in_any:
            frustum_ok = False
            frustum_detail = f"prop {p.get('id')} outside camera cone"
    check("26_prop_in_view_frustum", frustum_ok, frustum_detail)

    min_cam_actor = 99.0
    for s in shots:
        for cp in (s.get("camStart", [0, 2, 8]), s.get("camEnd", [0, 2, 8])):
            for a in actors:
                ap_head = [a["pos"][0], a["pos"][1] + 1.4, a["pos"][2]]
                min_cam_actor = min(min_cam_actor, dist3(cp, ap_head))
    check("27_actor_min_cam_dist", min_cam_actor >= 0.70, f"closest cam-to-face {min_cam_actor:.2f}m (>= 0.70m)")

    shot0 = shots[0] if shots else None
    f0_ok = False
    if shot0 and actors:
        fwd0 = vec_norm([shot0["lookAt"][i] - shot0["camStart"][i] for i in range(3)])
        to_h = vec_norm([actors[0]["pos"][i] - shot0["camStart"][i] for i in range(3)])
        f0_ok = sum(fwd0[i] * to_h[i] for i in range(3)) > 0.45
    check("28_first_frame_subject", f0_ok, "frame 0 camera faces hero clearly")

    # --- D. Character Acting & Anti-Slop (29-36) ---
    speech_spans = [(int(round(w["s"] * fps)), int(round(w["e"] * fps))) for w in words]
    bad_blinks = []
    for a in actors:
        for bf in a.get("blinkFrames", []):
            if any(sa <= bf <= sb for sa, sb in speech_spans):
                bad_blinks.append((a.get("id"), bf))
    check("29_no_blink_while_speaking", not bad_blinks, f"speech blinks={bad_blinks[:5]}" if bad_blinks else "0 mid-speech blinks")
    check(
        "30_pose_snap_no_bounce",
        bool(flags.get("poseSnapNoIdleBounce")) and not bool(flags.get("lipSyncNarrator", False)),
        "poseSnap-and-freeze enabled & narrator mouth-flapping disabled",
    )
    check("31_no_blink_during_speech_flag", bool(flags.get("noBlinkWhileSpeaking")), "speech blink suppressor enabled")

    poses_ok = bool(actors) and all(len(a.get("poseTransitions", [])) >= 1 for a in actors)
    check("32_pose_transitions_valid", poses_ok, "all actors have discrete beat pose transitions")

    flip_ok = True
    for a in actors:
        pts = sorted(a.get("poseTransitions", []), key=lambda x: x.get("frame", 0))
        for k in range(len(pts) - 1):
            if pts[k + 1]["frame"] - pts[k]["frame"] < 24:
                flip_ok = False
    check("33_one_emotion_per_beat", flip_ok, "pose holds >= 24f between changes")

    meme_cnt = sum(
        1 for a in actors for pt in a.get("poseTransitions", []) if str(pt.get("expr", "")).startswith("meme_")
    )
    check("34_peak_meme_budget", 1 <= meme_cnt <= 4, f"{meme_cnt} peak meme expression beats (target 1-4)")

    check("35_post_grain_budget", float(flags.get("postGrainMax", 1.0)) <= 0.008, f"post grain <= {flags.get('postGrainMax')}")
    check("36_noink_cards_contract", bool(flags.get("noInkCards")), "2D cards & clouds assigned NOINK layer")

    # --- E. Voice, Lighting Turn & Packaging (37-40) ---
    voice = plan.get("voice", {})
    check("37_voice_default", voice.get("model") in ("s2-pro", "chatterbox-tts"), f"voice model={voice.get('model')}")

    distinct_lights = {s.get("light") for s in shots}
    check("38_lighting_turn_shift", len(distinct_lights) >= 2, f"lighting presets used: {sorted(distinct_lights)}")

    title = str(plan.get("title", "")).strip()
    t_words = len(title.split())
    check("39_packaging_title_len", 4 <= t_words <= 9, f"title ({t_words} words): {title}")

    desc = str(plan.get("description", "")).strip()
    tags = plan.get("hashtags", [])
    check("40_packaging_desc_tags", len(desc) >= 20 and len(tags) >= 3, f"{len(desc)} chars desc, {len(tags)} hashtags")

    fails = [r for r in results if r[1] == "FAIL"]
    warns = [r for r in results if r[1] == "WARN"]
    passes = [r for r in results if r[1] == "PASS"]

    print(f"PLAN CHECK SUMMARY: {len(passes)}/40 PASS, {len(warns)} WARN, {len(fails)} FAIL")
    for cid, status, detail in results:
        if status != "PASS":
            print(f"  [{status}] {cid}: {detail}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
