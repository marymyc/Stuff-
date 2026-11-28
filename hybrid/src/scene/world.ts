import * as THREE from "three";
import { DustField, LightShafts, addGroundScatter } from "../engine/atmosphere";
import { Batch, V, addCartoonVeg, addTownBuilding, boxGeo, lam, quad } from "../engine/buildHelper";
import { Actor, Fx, Pool } from "../engine/billboard";
import { NOINK } from "../engine/ink";
import { grassHD, rep } from "../engine/paint";
import { asphaltHD, curbConcreteHD, makeSignTex, roadStripeWhiteHD } from "../engine/paintWorld";
import { WorldBase } from "../engine/worldBase";
import { stageStarterCast } from "./cast";
import { FPS, SHOTS, camAt } from "./story";

export class WorldScene extends WorldBase {
  private pool = new Pool();
  private actors: Actor[] = [];
  private fxs: Fx[] = [];
  private dust: DustField;
  private shafts: LightShafts;

  constructor() {
    super();
    const R = this.root;
    const terrain = new Batch();

    const roadMat = lam("asphalt", () => ({ map: rep(asphaltHD(), 2, 12) }));
    terrain.add(quad(V(-4.5, 0, -40), V(-4.5, 0, 40), V(4.5, 0, 40), V(4.5, 0, -40), 1, 8), roadMat);

    const stripeMat = lam("whiteStripe", () => ({ map: rep(roadStripeWhiteHD(), 1, 4) }));
    terrain.add(quad(V(-0.12, 0.012, -40), V(-0.12, 0.012, 40), V(0.12, 0.012, 40), V(0.12, 0.012, -40)), stripeMat);

    const curbMat = lam("curb", () => ({ map: rep(curbConcreteHD(), 6, 1) }));
    terrain.add(boxGeo(V(-7.5, -0.1, -40), V(-4.5, 0.12, 40), 4), curbMat);

    const grassMat = lam("grass", () => ({ map: rep(grassHD(), 8, 8) }));
    terrain.add(quad(V(-40, 0.02, -40), V(-40, 0.02, 40), V(-7.5, 0.02, 40), V(-7.5, 0.02, -40), 6, 8), grassMat);
    terrain.add(quad(V(4.5, -0.02, -40), V(4.5, -0.02, 40), V(40, -0.02, 40), V(40, -0.02, -40), 6, 8), grassMat);

    addTownBuilding(terrain, -11.5, 0.02, -10, Math.PI * 0.5, 9, 8, 9.5, 0);
    addTownBuilding(terrain, 9.5, 0.02, -14, -Math.PI * 0.5, 8.5, 8, 8.2, 2);
    addCartoonVeg(terrain, "round", -7.2, 0.02, -5.5, 4.6, 11);
    addCartoonVeg(terrain, "tall", 6.2, -0.02, -7.5, 5.2, 19);
    addGroundScatter(terrain, { count: 48, xRange: [-7.2, 4.4], zRange: [-18, 8], y: 0.01, seed: 21 });
    terrain.build(R, true);

    this.dust = new DustField(R, { count: 75, center: [0, 2.1, -1.5], span: [10, 3.8, 12], seed: 11 });
    this.shafts = new LightShafts(R, [
      { pos: [1.6, 5.8, -2.5], rot: [0.18, 0.0, -0.58], length: 8.5, radius: 1.5, opacity: 0.075 },
      { pos: [-1.4, 5.2, -5.5], rot: [0.15, 0.0, -0.55], length: 8.0, radius: 1.3, opacity: 0.065 },
    ]);

    // Unlit warning sign (always unlit MeshBasicMaterial + NOINK layer per Visual Spec)
    const signGroup = new THREE.Group();
    const pole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, 2.3, 10).translate(0, 1.15, 0),
      lam("signPole", () => ({ color: "#4c5460" }))
    );
    const board = new THREE.Mesh(
      new THREE.BoxGeometry(1.1, 1.1, 0.06),
      new THREE.MeshBasicMaterial({ map: makeSignTex("30", "SLOW!") })
    );
    board.position.set(0, 2.45, 0.04);
    board.layers.set(NOINK);
    signGroup.add(pole, board);
    signGroup.position.set(3.2, 0, -4.5);
    R.add(signGroup);

    for (let i = 0; i < 4; i++) this.actors.push(new Actor(R));
    for (let i = 0; i < 10; i++) this.fxs.push(new Fx(R));
  }

  update(id: number, f: number, cam: THREE.PerspectiveCamera, scene: THREE.Scene): THREE.Vector3 {
    const s = SHOTS.find((x) => x.id === id) ?? SHOTS[0];
    const c = camAt(id, f);
    cam.position.set(...c.pos);
    cam.up.set(0, 1, 0);
    cam.lookAt(...c.look);
    cam.rotateZ(c.roll);
    cam.fov = c.fov;
    cam.near = 0.2;
    cam.far = 1400;
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();

    const midF = Math.round((s.a + s.b) * 0.5);
    const midCam = camAt(id, midF);
    const focus = V(...c.look);
    this.applyLightingAndAtmosphere(id, s.light, cam, scene, focus, midCam.pos, midCam.look);

    this.dust.update(f / FPS, true);
    this.shafts.setVisible(s.light === "golden", 1.0);
    stageStarterCast(id, f, cam, this.pool, this.actors, this.fxs);
    return focus;
  }
}
