"""Native-pixel validation of the independent opposite-side view; no art repair."""
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np, json, hashlib
B = Path(__file__).resolve().parents[1]
R = B.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = B / 'generated/violet_left_camera_single_r01.png'
im = Image.open(p).convert('RGB')
a = np.array(im)
w, h = im.size
t = json.loads((B / 'data/left_camera_template_contract.json').read_text())
src = []
dst = []
for x, y in [[18, 64], [1006, 64], [18, 960], [1006, 960]]:
    xx, yy = (int(round(x * w / 1024)), int(round(y * h / 1024)))
    cut = a[yy - 6:yy + 7, xx - 6:xx + 7]
    v, u = np.where(np.all(cut > 225, axis=2))
    src.append([x, y, 1])
    dst.append([float(u.mean() + xx - 6), float(v.mean() + yy - 6)])
mat = np.linalg.lstsq(np.array(src), np.array(dst), rcond=None)[0]
err = np.linalg.norm(np.array(src) @ mat - dst, axis=1)
obs = [157, 418, 1113]
target = (np.array([[512, y, 1] for y in t['crown_chin_sole_y']]) @ mat)[:, 1]
ratio = (obs[2] - obs[0]) / (obs[1] - obs[0])
u = 3
boxes = {'face': [730, 379, 742, 390], 'upper_arm': [654, 472, 666, 484], 'thigh': [711, 715, 723, 728]}
regions = {}
for name, box in boxes.items():
    x, y, x1, y1 = box
    q = a[y:y1, x:x1].reshape(-1, 3)
    regions[name] = {'manual_semantic_roi_xyxy': box, 'median_rgb': np.median(q, 0).tolist(), 'p10_rgb': np.percentile(q, 10, axis=0).tolist(), 'p90_rgb': np.percentile(q, 90, axis=0).tolist(), 'min_rgb': q.min(0).tolist(), 'max_rgb': q.max(0).tolist()}
out = {'schema': 'riverstone.single_view_image_validation.v1', 'status': 'FAIL_APPROVED_PROPORTION_AND_UNRESOLVED_ORTHOGRAPHY', 'image_sha256': sha(p), 'template_sha256': t['template_sha256'], 'validator_sha256': sha(Path(__file__)), 'actual_size': [w, h], 'registration': {'markers': 4, 'affine': mat.tolist(), 'rms_px': float(np.sqrt(np.mean(err ** 2)))}, 'manual_observed_crown_chin_sole_y': obs, 'uncertainty_px': u, 'registered_template_targets_y': target.tolist(), 'target_error_px': (np.array(obs) - target).tolist(), 'measured_head_ratio': ratio, 'conservative_ratio_range': [(obs[2] - obs[0] - 2 * u) / (obs[1] - obs[0] + 2 * u), (obs[2] - obs[0] + 2 * u) / (obs[1] - obs[0] - 2 * u)], 'target_head_ratio': 3, 'skin_regions': regions, 'visual_review': {'direction': 'Improved: nose and toes point image-right, opposite side supplied. Camera name is canonical left(-X).', 'proportion': 'FAIL: neck/body remains too long relative to visible crown-to-chin; about3.66heads.', 'silhouette': 'Large hair/skirt forms remain, but precise approved3head silhouette not preserved.', 'costume': 'Major white corset/gloves/stockings/bouquet/lavender lining retained; panel and depth coherence with other views unvalidated.', 'face': 'Narrow eye and purple bangs recognizable; strict90degree profile and identity dimensions not proven.', 'color': 'Closer apparent skin than sheet r01, still not calibrated albedo; use separate Lab diagnostic, never R delta alone.', 'missing_parts': 'Far-side ornament hidden plausibly, not a proven attachment mapping.', 'stretching': 'Whole-body elongation remains.', 'component_relationships': 'No shared3D source or rig/socket validated; measured inter-view correspondence absent.'}, 'six_view_gate': False, 'voxel_compile': False, 'ready_for_measurement_voxel': False}
(B / 'evidence/single_validation_r01.json').write_text(json.dumps(out, indent=2) + '\n')
j = {'mode': 'built-in imagegen independent opposite-side correction', 'input_paths': ['voxel_character/three_head_reference_r01/violet_costume_skin_candidate_r06.png', str(B.relative_to(R) / 'reference/left_camera_single_template.png')], 'input_sha256': ['43d5ac6d62060513808037e247bac625a0f2eaa22b67422898a482aa2c6eb8d5', t['template_sha256']], 'prompt_path': 'data/generation_prompt_left_single_r01.txt', 'prompt_sha256': sha(B / 'data/generation_prompt_left_single_r01.txt'), 'output_sha256': sha(p), 'output_path': str(p.relative_to(R)), 'original_preserved': 'Publication metadata omitted.', 'generated_view_status': 'inferred design, not observed original opposite-side geometry'}
(B / 'evidence/generation_receipt_left_single_r01.json').write_text(json.dumps(j, indent=2) + '\n')
print(json.dumps({'ratio': ratio, 'observed': obs, 'targets': target.tolist(), 'error': out['target_error_px'], 'registration': out['registration']}))
