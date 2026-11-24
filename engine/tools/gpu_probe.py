"""Which Chromium GL backend reaches a REAL GPU? Prints diagnostics + the WebGL renderer for each config."""
import glob, json, os, subprocess
from playwright.sync_api import sync_playwright

def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()

print("== NVIDIA driver:", sh("nvidia-smi --query-gpu=name,driver_version --format=csv,noheader") or "none")
libs = sh("find / \\( -name 'libEGL_nvidia*' -o -name 'libGLX_nvidia*' -o -name 'libnvidia-glcore*' -o -name 'libnvidia-vulkan*' \\) 2>/dev/null | head -8")
print("== NVIDIA graphics libs (needed for WebGL on GPU):", libs or "NONE FOUND -> this runtime exposes compute only, no OpenGL/EGL/Vulkan")
print("== EGL vendor files:", glob.glob("/usr/share/glvnd/egl_vendor.d/*") or "none")
print("== Vulkan ICDs:", glob.glob("/usr/share/vulkan/icd.d/*") + glob.glob("/etc/vulkan/icd.d/*") or "none")

CONFIGS = {
    "egl": ["--use-gl=egl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"],
    "angle": ["--use-angle=default", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"],
    "vulkan": ["--use-angle=vulkan", "--use-vulkan=native", "--enable-features=Vulkan", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"],
    "swangle": ["--use-gl=angle", "--use-angle=swiftshader", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"],
}
JS = """() => { const g = document.createElement('canvas').getContext('webgl2'); if (!g) return 'NO WEBGL2';
  const e = g.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER); }"""
best = None
with sync_playwright() as p:
    for name, args in CONFIGS.items():
        try:
            b = p.chromium.launch(args=args)
            r = b.new_page().evaluate(JS)
            b.close()
        except Exception as e:
            r = "ERROR " + str(e).splitlines()[0][:100]
        soft = any(k in r for k in ("SwiftShader", "llvmpipe", "NO WEBGL2", "ERROR"))
        print(f"{name:8s} -> {r}   {'' if soft else '<== REAL GPU'}")
        if not soft and best is None:
            best = name
print("RESULT_GL=" + (best or "NONE"))
