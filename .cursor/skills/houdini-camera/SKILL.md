---
name: houdini-camera
description: >-
  Frames and debugs Houdini cameras across /obj, Solaris/LOPs, and husk/Karma
  renders. Use for camera angle, framing, look-at, focalLength, black frames,
  mirrored view, Camera LOP vs OBJ cam, matching a reference plate, or when
  HIP viewport camera disagrees with the beauty render.
---

# Houdini: Camera (OBJ + Solaris + render)

Cross-cutting camera skill. Topic skills (`houdini-solaris`, `houdini-render`,
`houdini-model`) defer framing pitfalls here.

## When to load this

- Match a reference camera / ракурс (SketchUp, photo, still).
- Black / empty beauty while geo exists.
- HIP camera ≠ husk / Karma plate.
- Mirrored or upside-down plates.
- Camera LOP optics look like `focal≈0.5`.

## Golden rules

1. **Composition first, not formulas.** Name what must read in frame (e.g. tall
   left, return right, floor slab, wall corner). Iterate eye/target against a
   **low-spp draft** — not 96+ beauty.
2. **One source of truth for pose.** Prefer a shared look-at (eye → target →
   matrix) written into both the authoring camera and the husk USD. Do not aim
   with RotateXYZ guesses alone.
3. **HIP viewport must equal beauty.** If a post-export script rewrites the USD
   camera and leaves the OBJ/Camera LOP alone, the user will report “сцена
   смотрит не туда”. Sync both every time.
4. **Draft cheap.** Default lookdev drafts: ~4 spp, ~960×540. Raise quality only
   after the user approves framing.
5. **Reference projection ≠ required projection.** A SketchUp still may look
   near-parallel; the user often only needs the **viewpoint** (height, azimuth,
   subject). Do not overfit true isometric unless asked.

## OBJ context (`/obj`)

- Default cam looks down local **-Z**, +Y up.
- Seed with translate + yaw/pitch from eye→target; verify by looking through the
  camera in the Scene Viewer before lighting.
- `focal` / `aperture` on OBJ cams are the usual film-back parms (mm).
- Parenting / constraints: `lookat` OBJ or CHOP/constraint — fine for OBJ-only
  shots. For Solaris delivery, still author a USD camera (see below).

## Solaris / Camera LOP

### Parm names (H21+)

| Intent | Parm (typical) |
| --- | --- |
| Focal length | `focalLength` (not always `focal`) |
| Film back | `horizontalAperture`, `verticalAperture` |
| Controls | every `*_control` → **Set** (not Do Nothing) |

Broken export signature: `focalLength≈0.5`, `horizontalAperture≈0.21` → husk
black/tiny plate while a default cube cam works.

### Pose: matrix over euler

Camera LOP `t`/`r` euler often cannot express the same basis as a USD look-at
matrix (especially after a horizontal unmirror). Pattern that worked:

1. Build camera-to-world with an orthonormal basis (look **-Z**).
2. Apply it with `UsdGeom.Xformable.AddTransformOp` (Python LOP or post-export).
3. Keep LOP `t`/`r` as UI seeds only, or they will drift from beauty.

Handedness check after build:

- `right · world_X > 0` and `up · world_Y > 0` when looking roughly +Z → upright,
  unmirrored for a Y-up kitchen/archviz plate.
- OpenGL `right = up × back` alone often **mirrors** the plate (subject flipped
  left/right). Negating local X after that basis fixed “tall on the wrong side”.
- Flipping Cross order alone produced **upside-down** bird’s-eye — do not do that.

### Bbox traps

- Read bbox only from a **force-cooked** display/OUT node.
- Reject degenerate boxes at origin (empty geo → 0-size bbox → eye at nonsense).
- Do not aim at bbox center blindly: stand in the **open** of an L / set, look at
  the subject knuckle. Standing on a return wing (`eye.x` on the peninsula)
  fills the frame with the wrong mass.

## husk / Karma / ROPs

- Force mm optics on the USD camera before CLI husk.
- Strip `/Render` products from `karmarendersettings` when calling
  `husk file.usd -c /cameras/...` (instant black otherwise).
- Export beauty stage from a null **above** karma settings when using CLI husk.
- `-p` defaults high in husk — always pass draft spp explicitly.
- Do not run long husk inside MCP `execute_python` (blocks the bridge).

## Matching a reference plate (checklist)

1. Read the ref: wall corner side, which mass is left/right, camera height
   (eye-level vs bird’s-eye), how much floor/ceiling shows.
2. Fix **set dressing that defines the corner** (e.g. back+right walls, not
   back+left) before blaming the camera.
3. Place eye in open space; target at subject height (often counter / mid-cab).
4. Verify handedness (unmirrored, upright).
5. Sync HIP + USD.
6. Draft 4 spp → user feedback → nudge height/azimuth/distance only.
7. Final spp only after explicit approval.

## Failure signatures

| Symptom | Likely cause |
| --- | --- |
| Black EXR, husk <1s | Optics in broken units; `/Render` present; cam aimed at empty space |
| HIP view ≠ beauty | Post-pass rewrote USD only |
| Tall/subject on wrong side | Mirrored cam basis (need local −X after OpenGL look-at) |
| Upside-down / ceiling view | Bad Cross order / negated up |
| Peninsula fills frame | Eye sitting on return wing (+X), not in open bay |
| Too “SketchUp iso” / too steep | Eye too high; lower Y and aim nearer counter height |
| Draft takes forever | Forgot `-p 4` / full res; husk default spp |

## Related skills

- `houdini-solaris` — LOPs / stage assembly; camera pitfalls summarized with a
  pointer here.
- `houdini-render` — Karma/ROP order of work; framing before lights.
- `houdini-troubleshooting` — cook/display failures; use this skill when the
  failure is camera/framing specific.
- `houdini-discipline` — do not “fix” the camera when the user only asked why
  the view is empty.
