# VG: public source snapshot

A filtered preservation snapshot of a procedural medieval-city and voxel-asset project, prepared on 2026-10-19.

## What is included

- Python authoring, geometry, sampling, assembly, quality checks and tests.
- Godot scripts and lightweight project/scene definitions.
- Selected procedural master data, city layouts, rules, schemas and small fixtures.
- Generic voxel framework and mesher at their original relative paths.
- Image-dependent measurement, registration, reconstruction and validation source, where it can be shared safely.

The file-by-file source manifest records SHA-256, bytes, original relative location and whether metadata was sanitized. Most retained files are byte-identical. Metadata-only public variants explicitly link their original and public hashes.

## Important limits

This is source preservation, not a complete playable game release. A clone does not contain the full city runtime, frozen generated baselines, compiled meshes, render caches, private reference photographs, character source images or historical evidence. Many integration and historical scripts therefore cannot run end to end from this export alone.

Image-dependent experiments retain useful algorithms but cannot reproduce their measured results without their omitted original inputs. Do not substitute arbitrary images and call the original experiments reproduced. Provenance/hash checks tied to omitted inputs or sanitized metadata may intentionally fail.

No engine binary, distribution archive or complete dependency lock is supplied. No licensing grant is added by this snapshot.

## Safe starting point

Use Python 3.12, from this repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python voxel_character/common/core.py --help
PYTHONDONTWRITEBYTECODE=1 python voxel_character/common/render_data.py --help
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s voxel_character/common -p test_six_view_review.py -v
python tools/verify_snapshot.py
```

The review-validator suite uses synthetic temporary fixtures. The CLI checks do not generate meshes. See `snapshot/validation.json` for exactly what was checked. No full city generation or Godot execution is claimed.

Some authoring modules use NumPy, SciPy, Pillow or Matplotlib. Install only what the specific task needs; versions are not pinned here. Existing scripts may also assume unavailable historical inputs or platform-specific tooling.

## Inventory and scope

- `snapshot/source_manifest.json`: preserved source/data files and hashes
- `snapshot/dependency_mapping.json`: common framework and mesher mapping
- `snapshot/exclusions.json`: omitted inputs, artifacts and reproducibility limits
- `snapshot/preparation_summary.json`: counts and public transformations
- `snapshot/validation.json`: bounded validation and privacy scan results
- `snapshot/file_manifest.json`: all publishable files except the manifest itself

Only this repository directory is intended for publication. Local preparation logs and scripts are not part of it.
