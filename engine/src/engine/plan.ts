// The data contract between the Python planner (tools/make_plan.py) and the renderer. One JSON file drives a whole short.
export type Light = "day" | "golden";
export type Who = {
  outfit: string;                       // hero | rival | commander | soldier | citizen | kid | worker | engineer | tycoon | parent
  expr: string;                         // neutral stern grin laugh whistle nervous shock relief dazed pained smile smile_closed lick
  x: number; z?: number;                // metres from the shot's focus point
  mode?: "stand" | "stroll"; scale?: number;
  action?: "point" | "wave" | "sit" | "hop" | "stroll";   // what the character DOES during the shot (rubber-hose snap on start)
};
export type PlanShot = {
  id: number; a: number; b: number;     // frame range [a, b)
  set: string;                          // field | fortress | canyon | interior | town
  light: Light;
  size: "wide_aerial" | "wide" | "medium" | "medium_low" | "close" | "macro";
  move: string;                         // fly_forward pull_back orbit_slow push_in push_in_low slide dutch_push
  chars: Who[]; props: string[]; fx: string[];
  focus?: string;                       // insert shot: close-up of one object (coin paper calendar newspaper caliper thermometer moneybag map clock marble)
  xfade?: number;                       // crossfade frames at the START of this shot (place/time change)
};
export type Word = { w: string; s: number; e: number };
export type Plan = { fps: number; total: number; flashAt: number | null; captions: boolean; shots: PlanShot[]; words: Word[] };

export const shotIndexAt = (plan: Plan, f: number) => {
  const i = plan.shots.findIndex((s) => f >= s.a && f < s.b);
  return i < 0 ? plan.shots.length - 1 : i;
};
/** layers to draw at frame f: the base shot, plus the next shot fading in during its crossfade */
export const layersAt = (plan: Plan, f: number): { i: number; alpha: number }[] => {
  for (let i = 1; i < plan.shots.length; i++) {
    const x = plan.shots[i].xfade ?? 0, a = plan.shots[i].a;
    if (x && f >= a - x / 2 && f < a + x / 2) return [{ i: i - 1, alpha: 1 }, { i, alpha: (f - (a - x / 2) + 1) / (x + 1) }];
  }
  return [{ i: shotIndexAt(plan, f), alpha: 1 }];
};
export const DOF_BY_SIZE: Record<string, number> = { wide_aerial: 0, wide: 0, medium: 11, medium_low: 12, close: 14, macro: 16 };

/** y of the surface the cast stands on, per set (the canyon cast stands on the sleepers) */
export const GROUND_Y: Record<string, number> = { canyon: 0.36 };
