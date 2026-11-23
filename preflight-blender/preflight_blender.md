# Preflight `blender`: FAIL

- PASS **import bpy** (0.3s): bpy 4.2.0
- FAIL **render 4 kits (Cycles CPU, tiny)** (0.2s): TypeError: bpy_struct.keyframe_insert() property "angle" not animatable
```
Traceback (most recent call last):
  File "/home/runner/work/Stuff-/Stuff-/src/stuff/preflight.py", line 20, in _check
    detail = fn()
             ^^^^
  File "/home/runner/work/Stuff-/Stuff-/src/stuff/preflight.py", line 97, in render_kits
    render_blender.run_job(job, wd)
  File "/home/runner/work/Stuff-/Stuff-/src/stuff/render_blender.py", line 30, in run_job
    return scene_runner.run(job)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/Stuff-/Stuff-/src/stuff/blender/scene_runner.py", line 221, in run
    build_shot(shot, job, out_dir, frames)
  File "/home/runner/work/Stuff-/Stuff-/src/stuff/blender/scene_runner.py", line 201, in build_shot
    cam = add_camera(scene, shot, info["focus"], rng, frames)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/Stuff-/Stuff-/src/stuff/blender/scene_runner.py", line 160, in add_camera
    cd.keyframe_insert("angle", frame=f)
TypeError: bpy_struct.keyframe_insert() property "angle" not animatable

```
