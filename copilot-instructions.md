# CAD Agent Rules

- Write all 3D models using `build123d` in Python inside the `models/` folder.
- Every model script MUST assign the final shape to a variable named `result`.
- Define all key dimensions in millimeters as named uppercase constants at the top of the file (e.g., `LENGTH = 60.0`, `WALL_THICKNESS = 3.0`).
- Prefer topological selectors (e.g., `faces().sort_by(Axis.Z)[-1]`) over hardcoded face/edge indices.
- **Mandatory Verification Loop:** After creating or editing any model script, you MUST:
  1. Call `run_cad_script` to confirm `"ok": true`, `"valid": true`, the expected `solid_count`, and accurate `bbox_mm` dimensions.
  2. Call `render_model_views` to visually inspect the 2x2 PNG for flipped extrusions, missing holes, or geometry errors.
  3. If anything looks wrong, fix the script and repeat until verified.