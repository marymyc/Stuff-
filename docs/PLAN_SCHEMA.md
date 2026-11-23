# plan.json

```json
{"version": 1, "title": "demo", "meta": {"words": 38, "est_seconds": 14.6},
 "shots": [{
   "id": 0, "text": "In 1869, two companies were racing across a canyon",
   "kit": "field | fortress | canyon | interior",
   "tod": "day | dawn | dusk | night",
   "shot_size": "wide_aerial | wide | medium | medium_low | close | macro",
   "camera_move": "fly_forward | pull_back | orbit_slow | push_in | push_in_low | slide | dutch_push",
   "transition": "cut | dissolve",
   "characters": [{"role": "hero | rival | extra", "expression": "neutral|angry|rage|happy|shocked|worried|smug", "side": "left|right|center"}],
   "props": ["cart", "crate", "barrel", "umbrella", "lamp", "table"],
   "fx": ["explosion"],
   "sfx": [{"name": "whoosh|boom|ding|rumble|spark|pop", "at": 0.0, "gain": 0.6}],
   "emphasis": ["1869"]
 }]}
```
`text` of all shots, concatenated, is exactly what the narrator says. Each shot's duration comes from its audio, not from the plan.
