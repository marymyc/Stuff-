import * as THREE from "three";
import { NOINK } from "./ink";
import { LIGHTS, LOOK, LightMode, LightPreset } from "./lights";
import { cloudHD } from "./paint";
import { sunDiscTex, sunHaloTex } from "./paintWorld";
import { CHAR, TONE, untone } from "./shade";

export type ShotLightingSpec = {
  id: number;
  light: LightMode;
};

/**
 * Shared 3D stylized environment rig: sky shader dome, sun disc/halo,
 * camera-relative frozen-per-shot directional shadow rig, painted clouds,
 * and automatic TONE / CHAR / fog synchronization.
 */
export class WorldBase {
  root = new THREE.Group();
  skyMat: THREE.ShaderMaterial;
  sky: THREE.Mesh;
  sunDisc: THREE.Sprite;
  sunHalo: THREE.Sprite;
  hemi: THREE.HemisphereLight;
  sun: THREE.DirectionalLight;
  fog = new THREE.Fog("#b8d0ec", 25, 300);
  clouds: THREE.Mesh[] = [];
  cloudMaps: Record<LightMode, THREE.Texture[]>;
  private sunDirs = new Map<number, THREE.Vector3>();

  constructor() {
    const R = this.root;
    this.skyMat = new THREE.ShaderMaterial({
      uniforms: {
        c0: { value: new THREE.Color() },
        c1: { value: new THREE.Color() },
        c2: { value: new THREE.Color() },
        c3: { value: new THREE.Color() },
        c4: { value: new THREE.Color() },
        e: { value: new THREE.Vector4() },
      },
      vertexShader:
        "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: `uniform vec3 c0, c1, c2, c3, c4; uniform vec4 e; varying vec3 vP;
        void main(){ float el = asin(clamp(normalize(vP).y, -1.0, 1.0));
          vec3 c = mix(c0, c1, smoothstep(0.0, e.x, el));
          c = mix(c, c2, smoothstep(e.x, e.y, el));
          c = mix(c, c3, smoothstep(e.y, e.z, el));
          c = mix(c, c4, smoothstep(e.z, e.w, el));
          gl_FragColor = vec4(c, 1.0); }`,
      side: THREE.BackSide,
      depthWrite: false,
      fog: false,
    });

    this.sky = new THREE.Mesh(new THREE.SphereGeometry(1100, 48, 24), this.skyMat);
    this.sky.renderOrder = -1;
    this.sky.frustumCulled = false;
    this.sky.layers.set(NOINK);
    R.add(this.sky);

    this.sunDisc = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: sunDiscTex(), color: new THREE.Color(6, 4.4, 2.4), fog: false, depthWrite: false })
    );
    this.sunHalo = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: sunHaloTex(),
        color: new THREE.Color(1, 1, 1),
        fog: false,
        depthWrite: false,
        depthTest: true,
        transparent: true,
        blending: THREE.AdditiveBlending,
      })
    );
    this.sunDisc.renderOrder = -0.5;
    this.sunHalo.renderOrder = 5;
    for (const sp of [this.sunDisc, this.sunHalo]) {
      sp.frustumCulled = false;
      sp.layers.set(NOINK);
      R.add(sp);
    }

    this.hemi = new THREE.HemisphereLight("#cfe6ff", "#6c5c8c", 1.1);
    this.sun = new THREE.DirectionalLight("#fff0d6", 2.6);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    R.add(this.hemi, this.sun, this.sun.target);

    this.cloudMaps = {
      day: [0, 1, 2, 3].map((k) => cloudHD(k, LOOK.day.cloud)),
      golden: [0, 1, 2, 3].map((k) => cloudHD(k, LOOK.golden.cloud)),
      interior: [0, 1, 2, 3].map((k) => cloudHD(k, LOOK.interior.cloud)),
      night: [0, 1, 2, 3].map((k) => cloudHD(k, LOOK.night.cloud)),
    };
    for (let i = 0; i < 10; i++) {
      const a = (i / 10) * Math.PI * 2 + 0.25;
      const d = 580 + (i % 3) * 70;
      const w = 125 + (i % 4) * 28;
      const mat = new THREE.MeshBasicMaterial({
        map: this.cloudMaps.day[i % 4],
        color: new THREE.Color(1.08, 1.08, 1.08),
        transparent: true,
        depthWrite: false,
        fog: false,
      });
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
      m.position.set(Math.cos(a) * d, 95 + (i % 3) * 28, Math.sin(a) * d);
      m.scale.set(w, w * 0.42, 1);
      m.layers.set(NOINK);
      m.frustumCulled = false;
      R.add(m);
      this.clouds.push(m);
    }
  }

  /** Sun direction computed once at each shot's mid-frame so light stays rock-steady inside glides. */
  protected getShotSun(
    shotId: number,
    lightMode: LightMode,
    midPos: [number, number, number],
    midLook: [number, number, number],
    preset: LightPreset
  ): THREE.Vector3 {
    let dir = this.sunDirs.get(shotId);
    if (!dir) {
      const fwd = new THREE.Vector3(...midLook).sub(new THREE.Vector3(...midPos)).setY(0).normalize();
      if (fwd.lengthSq() < 1e-4) fwd.set(0, 0, -1);
      const right = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 1, 0)).normalize();
      const az = THREE.MathUtils.degToRad(preset.az);
      const el = THREE.MathUtils.degToRad(preset.el);
      dir = fwd
        .multiplyScalar(Math.cos(az))
        .addScaledVector(right, Math.sin(az))
        .multiplyScalar(Math.cos(el))
        .addScaledVector(new THREE.Vector3(0, 1, 0), Math.sin(el))
        .normalize();
      this.sunDirs.set(shotId, dir);
    }
    void lightMode;
    return dir;
  }

  protected applyLightingAndAtmosphere(
    shotId: number,
    lightMode: LightMode,
    cam: THREE.PerspectiveCamera,
    scene: THREE.Scene,
    focus: THREE.Vector3,
    midPos: [number, number, number],
    midLook: [number, number, number]
  ) {
    const L = LIGHTS[lightMode];
    const K = LOOK[lightMode];
    const dist = cam.position.distanceTo(focus);

    const sunDir = this.getShotSun(shotId, lightMode, midPos, midLook, L);
    this.hemi.color.set(L.sky);
    this.hemi.groundColor.set(L.ground);
    this.hemi.intensity = L.hemiI;
    this.sun.color.set(L.sunCol);
    this.sun.intensity = L.sunI;

    let Rr = THREE.MathUtils.clamp(dist * 1.15 + 8, 14, 92);
    if (lightMode === "golden") Rr = Math.max(Rr, 32);
    this.sun.position.copy(focus).addScaledVector(sunDir, 220);
    this.sun.target.position.copy(focus);
    const sc = this.sun.shadow.camera;
    sc.left = -Rr;
    sc.right = Rr;
    sc.top = Rr;
    sc.bottom = -Rr;
    sc.near = 20;
    sc.far = 480;
    sc.updateProjectionMatrix();
    this.sun.shadow.bias = L.bias;
    this.sun.shadow.normalBias = L.normalBias * (Rr / 12);

    TONE.uLitCol.value.set(...L.lit);
    TONE.uShadeCol.value.set(...L.shade);
    TONE.uShadeLift.value.set(...L.lift);
    TONE.uLambert.value = L.lambert;
    TONE.uSideK.value = L.sideK;
    TONE.uTerm.value = L.term;
    TONE.uBounce.value.set(...K.bounce);
    TONE.uSat.value = K.sat;

    CHAR.uCharTint.value.set(...L.charTint);
    CHAR.uCharShade.value = L.charShade;
    CHAR.uGrad.value = L.charGrad;
    CHAR.uBodyGrad.value = L.bodyGrad;
    CHAR.uSideTint.value.set(...L.sideTint);

    const su = this.skyMat.uniforms;
    K.sky.c.forEach((h, i) => untone(h, su["c" + i].value));
    const e = K.sky.e.map((deg) => THREE.MathUtils.degToRad(deg));
    su.e.value.set(e[1], e[2], e[3], e[4]);
    this.sky.position.copy(cam.position);

    untone(L.fog, this.fog.color);
    this.fog.near = L.fogNear;
    this.fog.far = L.fogFar;
    scene.fog = this.fog;
    scene.background = null;

    const showSun = lightMode === "golden";
    this.sunDisc.visible = this.sunHalo.visible = showSun;
    if (showSun) {
      this.sunDisc.position.copy(cam.position).addScaledVector(sunDir, 900);
      this.sunDisc.scale.setScalar(2 * 900 * Math.tan(THREE.MathUtils.degToRad(1.7)));
      this.sunHalo.position.copy(this.sunDisc.position);
      this.sunHalo.scale.setScalar(2 * 900 * Math.tan(THREE.MathUtils.degToRad(24)));
      (this.sunHalo.material as THREE.SpriteMaterial).color.set(L.sunDisc).multiplyScalar(1.3);
    }

    for (let i = 0; i < this.clouds.length; i++) {
      const m = this.clouds[i];
      m.visible = lightMode !== "interior";
      m.lookAt(cam.position.x, m.position.y, cam.position.z);
      (m.material as THREE.MeshBasicMaterial).map = this.cloudMaps[lightMode][i % 4];
    }
  }
}
