import { ctex } from "./paint";

const TAU = Math.PI * 2;

export const asphaltHD = () =>
  ctex("asphaltHD", 1024, 1024, (g, r) => {
    const S = 1024;
    g.fillStyle = "#525864";
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 65; i++) {
      const x = r() * S;
      const y = r() * S;
      const rad = 28 + r() * 80;
      const light = r() > 0.5;
      for (const ox of [-S, 0, S]) {
        for (const oy of [-S, 0, S]) {
          const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, rad);
          gr.addColorStop(0, light ? "rgba(130,138,150,0.12)" : "rgba(42,46,54,0.14)");
          gr.addColorStop(1, "rgba(0,0,0,0)");
          g.fillStyle = gr;
          g.fillRect(x + ox - rad, y + oy - rad, rad * 2, rad * 2);
        }
      }
    }
    for (let i = 0; i < 3600; i++) {
      const sz = 1.2 + r() * 2.2;
      g.fillStyle = r() < 0.55 ? "rgba(210,214,220,0.18)" : "rgba(35,38,44,0.22)";
      g.fillRect(r() * S, r() * S, sz, sz);
    }
  });

export const roadStripeWhiteHD = () =>
  ctex("roadStripeWhiteHD", 512, 512, (g, r) => {
    const S = 512;
    g.fillStyle = "#f2ede2";
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 24; i++) {
      g.fillStyle = r() > 0.4 ? "rgba(85,90,102,0.14)" : "rgba(255,255,255,0.2)";
      g.fillRect(0, r() * S, S, 4 + r() * 10);
    }
  });

export const curbConcreteHD = () =>
  ctex("curbConcreteHD", 1024, 256, (g, r) => {
    const W = 1024;
    const H = 256;
    g.fillStyle = "#cec7ba";
    g.fillRect(0, 0, W, H);
    const seg = 256;
    for (let x = 0; x < W; x += seg) {
      g.fillStyle = r() > 0.5 ? "#d5cebf" : "#c7c0b3";
      g.fillRect(x + 2, 0, seg - 4, H);
      g.fillStyle = "#8a8275";
      g.fillRect(x, 0, 4, H);
    }
    for (let i = 0; i < 450; i++) {
      g.fillStyle = r() < 0.5 ? "rgba(95,88,78,0.18)" : "rgba(255,250,240,0.18)";
      g.beginPath();
      g.arc(r() * W, r() * H, 1 + r() * 2, 0, TAU);
      g.fill();
    }
  });

export const hazardStripeHD = () =>
  ctex("hazardStripeHD", 512, 512, (g) => {
    const S = 512;
    g.fillStyle = "#f2b830";
    g.fillRect(0, 0, S, S);
    g.fillStyle = "#26282e";
    for (let x = -S; x < S * 2; x += 128) {
      g.beginPath();
      g.moveTo(x, 0);
      g.lineTo(x + 64, 0);
      g.lineTo(x - 64, S);
      g.lineTo(x - 128, S);
      g.closePath();
      g.fill();
    }
  });

/** Unlit road/street sign face helper with readable dark plum ink border. */
export const makeSignTex = (title: string, sub: string, bg = "#f7f3ea", fg = "#241726", subCol = "#d93434") =>
  ctex(`sign_${title}_${sub}`, 512, 512, (g) => {
    const S = 512;
    g.fillStyle = bg;
    g.beginPath();
    g.roundRect(14, 14, S - 28, S - 28, 30);
    g.fill();
    g.lineWidth = 16;
    g.strokeStyle = "#241726";
    g.stroke();

    g.fillStyle = fg;
    g.font = "900 120px 'Arial Black', sans-serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(title, S / 2, S * 0.42);

    g.fillStyle = subCol;
    g.font = "900 56px 'Arial Black', sans-serif";
    g.fillText(sub, S / 2, S * 0.74);
  });

export const sunDiscTex = () =>
  ctex("sunDiscTex", 256, 256, (g) => {
    const gr = g.createRadialGradient(128, 128, 12, 128, 128, 126);
    gr.addColorStop(0, "rgba(255,252,240,1)");
    gr.addColorStop(0.55, "rgba(255,235,195,0.95)");
    gr.addColorStop(0.85, "rgba(255,215,150,0.35)");
    gr.addColorStop(1, "rgba(255,200,120,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 256, 256);
  });

export const sunHaloTex = () =>
  ctex("sunHaloTex", 256, 256, (g) => {
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, "rgba(255,230,185,0.85)");
    gr.addColorStop(0.3, "rgba(255,200,140,0.35)");
    gr.addColorStop(0.7, "rgba(255,175,110,0.08)");
    gr.addColorStop(1, "rgba(255,160,95,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 256, 256);
  });

export const panelWallHD = (base = "#2e3c52", seam = "#1d2738") =>
  ctex(`panelWallHD_${base}_${seam}`, 1024, 1024, (g, r) => {
    const S = 1024;
    g.fillStyle = base;
    g.fillRect(0, 0, S, S);
    for (let y = 0; y < S; y += 256) {
      for (let x = 0; x < S; x += 256) {
        g.fillStyle = r() > 0.5 ? "rgba(255,255,255,0.035)" : "rgba(0,0,0,0.04)";
        g.fillRect(x + 6, y + 6, 244, 244);
        g.strokeStyle = seam;
        g.lineWidth = 5;
        g.strokeRect(x + 3, y + 3, 250, 250);
        g.fillStyle = "rgba(190,210,235,0.22)";
        for (const rx of [x + 18, x + 238]) {
          for (const ry of [y + 18, y + 238]) {
            g.beginPath();
            g.arc(rx, ry, 4, 0, TAU);
            g.fill();
          }
        }
      }
    }
    for (let i = 0; i < 900; i++) {
      g.fillStyle = r() > 0.5 ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)";
      g.fillRect(r() * S, r() * S, 2, 2);
    }
  });

export const concreteFloorHD = (base = "#737a84") =>
  ctex(`concreteFloorHD_${base}`, 1024, 1024, (g, r) => {
    const S = 1024;
    g.fillStyle = base;
    g.fillRect(0, 0, S, S);
    for (let y = 0; y < S; y += 256) {
      for (let x = 0; x < S; x += 256) {
        g.fillStyle = r() > 0.5 ? "rgba(255,255,255,0.04)" : "rgba(20,24,30,0.05)";
        g.fillRect(x + 3, y + 3, 250, 250);
        g.fillStyle = "rgba(38,42,50,0.35)";
        g.fillRect(x, y, S, 3);
        g.fillRect(x, y, 3, S);
      }
    }
    for (let i = 0; i < 2400; i++) {
      g.fillStyle = r() > 0.5 ? "rgba(235,240,245,0.09)" : "rgba(25,28,34,0.11)";
      g.fillRect(r() * S, r() * S, 1.5 + r() * 2, 1.5 + r() * 2);
    }
  });

export const slateRockHD = (base = "#55606e", vein = "#38414d") =>
  ctex(`slateRockHD_${base}_${vein}`, 1024, 1024, (g, r) => {
    const S = 1024;
    g.fillStyle = base;
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 42; i++) {
      const y0 = r() * S;
      g.strokeStyle = i % 3 === 0 ? "rgba(220,228,240,0.12)" : vein;
      g.lineWidth = 4 + r() * 14;
      g.beginPath();
      g.moveTo(0, y0);
      g.bezierCurveTo(S * 0.33, y0 + (r() - 0.5) * 44, S * 0.66, y0 + (r() - 0.5) * 44, S, y0 + (r() - 0.5) * 24);
      g.stroke();
    }
    for (let i = 0; i < 1600; i++) {
      g.fillStyle = r() > 0.5 ? "rgba(255,255,255,0.07)" : "rgba(20,25,32,0.09)";
      g.fillRect(r() * S, r() * S, 2 + r() * 3, 2 + r() * 3);
    }
  });

export const wallpaperStripeHD = (c1 = "#d9d0be", c2 = "#ccc1ab") =>
  ctex(`wallpaperStripeHD_${c1}_${c2}`, 512, 512, (g, r) => {
    const S = 512;
    g.fillStyle = c1;
    g.fillRect(0, 0, S, S);
    g.fillStyle = c2;
    for (let x = 0; x < S; x += 64) g.fillRect(x, 0, 28, S);
    g.fillStyle = "rgba(120,104,84,0.09)";
    for (let i = 0; i < 900; i++) g.fillRect(r() * S, r() * S, 1.5, 1.5);
  });
