"""Colab exposes the NVIDIA GPU for CUDA only: no OpenGL / EGL / Vulkan user-space libraries, so Chromium falls back to software
WebGL (minutes per frame). This downloads the NVIDIA driver installer that matches the RUNNING kernel driver, extracts only the
graphics libraries, and registers the EGL vendor file and the Vulkan ICD. Safe to run twice; does nothing when there is no NVIDIA driver."""
import glob, os, shutil, subprocess, sys

GFX = ["libEGL_nvidia", "libGLX_nvidia", "libnvidia-glcore", "libnvidia-eglcore", "libnvidia-glsi", "libnvidia-tls",
       "libnvidia-glvkspirv", "libnvidia-gpucomp", "libnvidia-allocator", "libnvidia-vulkan-producer", "libnvidia-rtcore"]
LIBDIR = "/usr/lib/x86_64-linux-gnu"


def sh(cmd, check=False):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{cmd}\n{r.stderr[-800:]}")
    return r.stdout.strip()


def have_gfx():
    return bool(glob.glob(f"{LIBDIR}/libEGL_nvidia.so.*") or glob.glob("/usr/lib64-nvidia/libEGL_nvidia.so.*"))


def main():
    ver = (sh("nvidia-smi --query-gpu=driver_version --format=csv,noheader") or "").split("\n")[0].strip()
    if not ver:
        print("No NVIDIA driver visible here: nothing to do (is the runtime set to GPU?).")
        return 0
    print("NVIDIA kernel driver:", ver)
    if have_gfx():
        print("Graphics libraries already present.")
    else:
        run, out = f"/content/nvdrv-{ver}.run", f"/content/nvdrv-{ver}"
        if not os.path.exists(run):
            for url in (f"https://us.download.nvidia.com/tesla/{ver}/NVIDIA-Linux-x86_64-{ver}.run",
                        f"https://us.download.nvidia.com/XFree86/Linux-x86_64/{ver}/NVIDIA-Linux-x86_64-{ver}.run"):
                print("downloading", url)
                if subprocess.run(["wget", "-q", "-O", run, url]).returncode == 0 and os.path.getsize(run) > 50_000_000:
                    break
                if os.path.exists(run):
                    os.remove(run)
            else:
                print("Could not download the matching driver installer: stop here and send this output.")
                return 1
        if not os.path.isdir(out):
            sh(f"sh {run} -x --target {out}", check=True)
        copied = []
        for name in GFX:
            for f in glob.glob(f"{out}/{name}.so.{ver}"):
                shutil.copy(f, LIBDIR)
                copied.append(os.path.basename(f))
        for base in ("libEGL_nvidia", "libGLX_nvidia"):
            tgt = f"{LIBDIR}/{base}.so.{ver}"
            if os.path.exists(tgt):
                for link in (f"{LIBDIR}/{base}.so.0",):
                    if os.path.lexists(link):
                        os.remove(link)
                    os.symlink(tgt, link)
        print("copied:", copied or "NOTHING (installer layout differs)")
        sh("apt-get -qq install -y libegl1 libvulkan1 libgl1 > /dev/null 2>&1")
        os.makedirs("/usr/share/glvnd/egl_vendor.d", exist_ok=True)
        open("/usr/share/glvnd/egl_vendor.d/10_nvidia.json", "w").write('{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}\n')
        os.makedirs("/usr/share/vulkan/icd.d", exist_ok=True)
        open("/usr/share/vulkan/icd.d/nvidia_icd.json", "w").write('{"file_format_version":"1.0.0","ICD":{"library_path":"libGLX_nvidia.so.0","api_version":"1.3.0"}}\n')
        sh("ldconfig")
    print("EGL vendor files:", glob.glob("/usr/share/glvnd/egl_vendor.d/*"))
    print("Vulkan ICDs:", glob.glob("/usr/share/vulkan/icd.d/*"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
