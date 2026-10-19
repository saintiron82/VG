"""Measure fixed-grid preservation. Passing this does not certify a 3D design.

Fiducials are read from output pixels, never synthesized or moved to fit.
Affine fits are diagnostic only; they do not authorize geometric reconstruction.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def measure(image, template):
    rgb = np.asarray(image.convert('RGB'), dtype=np.int16)
    errors = []
    if list(image.size) != template['canvas_px']: errors.append('canvas dimensions changed')
    components = {}
    for f in template['registration_fiducials']:
        color = tuple(f['rgb'])
        if color in components: continue
        delta = rgb - np.array(color)
        mask = (np.sum(delta.astype(float)**2,axis=2) < 72**2)
        labeled,n = ndimage.label(mask)
        sizes = np.bincount(labeled.ravel())
        slices = ndimage.find_objects(labeled)
        found = []
        for k in np.where((sizes >= 3) & (sizes <= 70))[0]:
            if k == 0: continue
            sy,sx = slices[k-1]
            ys,xs = np.where(labeled[sy,sx] == k)
            ys=ys+sy.start;xs=xs+sx.start
            # Reject flower/shingle pixels whose shape does not resemble a marker.
            if max(xs)-min(xs) > 10 or max(ys)-min(ys) > 10: continue
            found.append([float(np.mean(xs)),float(np.mean(ys)),int(sizes[k])])
        components[color] = found
    rows = []
    for f in template['registration_fiducials']:
        expected = np.array(f['center_px'], dtype=float)
        col,row = int(expected[0]//512),int(expected[1]//512)
        candidates = [c for c in components[tuple(f['rgb'])] if int(c[0]//512)==col and int(c[1]//512)==row]
        if not candidates:
            rows.append({'id':f['id'],'expected_px':f['center_px'],'found':False})
            errors.append(f['id']+': missing fiducial'); continue
        observed = min(candidates,key=lambda c:np.linalg.norm(np.array(c[:2])-expected))
        distance = float(np.linalg.norm(np.array(observed[:2])-expected))
        if distance > 200:
            rows.append({'id':f['id'],'expected_px':f['center_px'],'found':False})
            errors.append(f['id']+': no nearby fiducial'); continue
        passed = distance <= template['tolerances']['fiducial_max_error_px']
        rows.append({'id':f['id'],'expected_px':f['center_px'],'found':True,'observed_px':observed[:2],'component_pixels':observed[2],'error_px':distance,'within_tolerance':passed})
        if not passed: errors.append(f['id']+': moved %.3fpx'%distance)
    fits = {}
    for name in template['views']:
        points=[r for r in rows if r['id'].startswith(name+'_') and r['found']]
        if len(points)!=4: continue
        x=np.array([r['expected_px']+[1] for r in points]);y=np.array([r['observed_px'] for r in points])
        a=np.linalg.lstsq(x,y,rcond=None)[0]
        singular=np.linalg.svd(a[:2,:],compute_uv=False)
        fits[name]={'template_to_output_affine':a.tolist(),'singular_scale':singular.tolist(),'anisotropy':float(max(singular)/min(singular)),'max_corner_residual_px':float(np.max(np.linalg.norm(x@a-y,axis=1))),'used_for_reconstruction':False}
    return {'registration_pass':not errors,'errors':errors,'visible_fiducials':sum(r['found'] for r in rows),'max_error_px':max([r.get('error_px',0) for r in rows],default=0),'fiducials':rows,'diagnostic_affine_fits':fits,'scope':'Only output canvas and colored template fiducials. Internal projection and shared 3D geometry require independent checks.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    t=json.loads((HERE/'template.json').read_text())
    result=measure(Image.open(a.image),t)
    result.update({'schema':'riverstone.six_view_registration.v1','image':str(a.image.name),'image_sha256':sha(a.image),'template_sha256':t['template']['sha256']})
    out=json.dumps(result,indent=2)+'\n'
    if a.out:a.out.write_text(out)
    print(out)
    return 0 if result['registration_pass'] else 2
if __name__=='__main__':raise SystemExit(main())
