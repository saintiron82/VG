"""One authorized target-overlay edit: measured boundaries, palette and gate."""
from pathlib import Path
from PIL import Image, ImageDraw
import json, hashlib, numpy as np
B = Path(__file__).resolve().parents[1]
R = B.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def lab(rgb):
    c = np.array(rgb, float) / 255
    v = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    v = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.072175], [0.0193339, 0.119192, 0.9503041]]) @ v / [0.95047, 1.0, 1.08883]
    d = 6 / 29
    t = np.where(v > d ** 3, np.cbrt(v), v / (3 * d * d) + 4 / 29)
    return np.array([116 * t[1] - 16, 500 * (t[0] - t[1]), 200 * (t[1] - t[2])])

def run():
    ap = B / 'data/local_edit_r02_annotations.json'
    ann = json.load(open(ap))
    p = B / ann['image']
    im = Image.open(p).convert('RGB')
    a = np.array(im)
    found = {}
    for name, v in ann['searches'].items():
        x, y, x1, y1 = v['roi']
        c = a[y:y1, x:x1].astype(int)
        if v['rule'] == 'dark_purple_cap':
            mask = (c[:, :, 0] < 140) & (c[:, :, 1] < 100) & (c[:, :, 2] < 150) & (c[:, :, 0] > c[:, :, 1] + 8)
        elif v['rule'] == 'warm_skin':
            mask = (c[:, :, 0] > 140) & (c[:, :, 1] > 100) & (c[:, :, 2] > 95) & (c[:, :, 0] > c[:, :, 1] + 20)
        else:
            mask = (c[:, :, 0] > 90) & (c[:, :, 1] > 55) & (c[:, :, 2] > 55) & (abs(c[:, :, 0] - c[:, :, 2]) < 100) & ~((c[:, :, 1] > c[:, :, 0] + 80) & (c[:, :, 1] > c[:, :, 2] + 80))
        yy, xx = np.where(mask)
        if not len(yy):
            raise ValueError('No observed boundary in declared ROI: ' + name)
        found[name] = {'roi': v['roi'], 'rule': v['rule'], 'pixels': int(mask.sum()), 'boundary_y_px': int((yy.min() if v['boundary'] == 'min_y' else yy.max()) + y), 'pixel_bounds': [int(xx.min() + x), int(yy.min() + y), int(xx.max() + x), int(yy.max() + y)]}
    obs = np.array([found[k]['boundary_y_px'] for k in ['crown', 'chin', 'sole']])
    target = np.array(ann['native_target_crown_chin_sole_y'])
    ratio = float((obs[2] - obs[0]) / (obs[1] - obs[0]))
    palette = json.load(open(B / 'evidence/observed_palette_comparison.json'))['standard_palette_for_this_project']
    skin = {}
    for n, box in ann['skin_roi_xyxy'].items():
        x, y, x1, y1 = box
        v = a[y:y1, x:x1].reshape(-1, 3)
        med = np.median(v, 0)
        ref = np.array(palette[n]['median_observed_srgb'])
        dl = lab(med) - lab(ref)
        skin[n] = {'roi': box, 'median_observed_rgb': med.tolist(), 'p10_rgb': np.percentile(v, 10, axis=0).tolist(), 'p90_rgb': np.percentile(v, 90, axis=0).tolist(), 'approved_observed_rgb': ref.tolist(), 'delta_rgb': (med - ref).tolist(), 'delta_Lab': dl.tolist(), 'deltaE76_diagnostic': float(np.linalg.norm(dl)), 'albedo': None, 'color_pass': None}
    u = ann['landmark_uncertainty_px']
    result = {'schema': 'riverstone.local_edit_input_validation.v1', 'status': 'FAIL_TARGET_PROPORTION_AND_INVARIANT_PRESERVATION', 'image_sha256': sha(p), 'annotation_sha256': sha(ap), 'validator_sha256': sha(Path(__file__)), 'actual_size': list(im.size), 'measurements': found, 'observed_crown_chin_sole_y': obs.tolist(), 'target_crown_chin_sole_y': target.tolist(), 'errors_px': (obs - target).tolist(), 'head_ratio': ratio, 'conservative_ratio_range': [(obs[2] - obs[0] - 2 * u) / (obs[1] - obs[0] + 2 * u), (obs[2] - obs[0] + 2 * u) / (obs[1] - obs[0] - 2 * u)], 'skin_observed_comparison': skin, 'color_space_limit': 'Assumed encoded sRGB/D65 Lab diagnostics, unmatched illustrated shading and patch context. No calibrated albedo or automatic color PASS.', 'visual_review': {'direction': 'Nose stays image-right; opposite camera side retained. Exact90degree torso still not proven.', 'silhouette': 'FAIL: crown and entire figure shifted down despite fixed target.', 'missing_parts': 'No new missing large parts apparent; far-side ornament remains inferred/occluded.', 'stretching': 'FAIL: visible head interval is243px instead of313px; total ratio worsened from3.663 to3.852.', 'color': 'Face/arm/thigh apparent RGB/Lab drift despite preserve-color request. Shading difference and albedo remain distinct.', 'component_relationships': 'Head/neck still coherent-looking illustration, but torso/costume/halo shifted; shared3D consistency not established.', 'costume': 'Large white/purple panels retained visually, exact approved cut/fold correspondence not certified.'}, 'approved_r06_still_valid': True, 'new_generated_inputs_approved': False, 'actual_Godot_six_view_review': False, 'new_voxel_or_shader': False, 'no_more_imagegen_in_this_bounded_correction': True}
    (B / 'evidence/local_edit_validation_r02.json').write_text(json.dumps(result, indent=2) + '\n')
    source1 = B / 'generated/violet_left_camera_single_r01.png'
    source2 = B / 'reference/local_correction_targets_r02.jpg'
    source3 = R / 'voxel_character/three_head_reference_r01/violet_costume_skin_candidate_r06.png'
    prompt = B / 'data/generation_prompt_left_single_r02.txt'
    receipt = {'tool': 'built-in imagegen', 'scope': 'One explicitly approved local target-overlay correction', 'inputs': [{'path': str(q.relative_to(R)), 'sha256': sha(q)} for q in [source1, source2, source3]], 'prompt': {'path': str(prompt.relative_to(R)), 'sha256': sha(prompt)}, 'output': {'path': str(p.relative_to(R)), 'sha256': sha(p)}, 'original_preserved': 'Publication metadata omitted.', 'actual_size': list(im.size), 'result': 'FAIL_NEW_REFERENCE_ONLY_APPROVED_R06_UNCHANGED'}
    (B / 'evidence/generation_receipt_left_single_r02.json').write_text(json.dumps(receipt, indent=2) + '\n')
    comparison = Image.new('RGB', (1536, 640), 'white')
    d = ImageDraw.Draw(comparison)
    d.text((10, 8), 'AI INPUT comparison, NOT a3D render. Approved r06 remains valid; both newly generated profiles fail proportion.', fill='black')
    approved = Image.open(source3).crop((655, 0, 1050, 624))
    approved.thumbnail((480, 570))
    comparison.paste(approved, ((512 - approved.width) // 2, 40))
    d.text((12, 610), 'Approved reference (opposite facing); ~3heads', fill='black')
    for i, (file, title) in enumerate([(source1, 'Before: crown157 / chin418 / sole1113 =3.663'), (p, 'After: crown201 / chin444 / sole1137 =3.852')], 1):
        pic = Image.open(file).convert('RGB')
        pic.thumbnail((512, 550))
        comparison.paste(pic, (i * 512, 40))
        d.text((i * 512 + 8, 610), title, fill='black')
    comparison.save(B / 'evidence/local_edit_before_after.jpg', quality=90)
    print(json.dumps({'ratio': ratio, 'observed': obs.tolist(), 'targets': target.tolist(), 'errors': (obs - target).tolist(), 'skin_deltaE76': {k: v['deltaE76_diagnostic'] for k, v in skin.items()}, 'status': result['status']}))
if __name__ == '__main__':
    run()
