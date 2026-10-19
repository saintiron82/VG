"""Read-only verification of the sealed roof audit; no geometry or image writes."""
from pathlib import Path
import hashlib,json,resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(15,)*2)
H=Path(__file__).resolve().parent
R=next(p for p in H.parents if(p/'voxel_character/common/core.py').exists())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((H/'handoff.json').read_bytes())
for r in a['files']: assert sha(R/r['path'])==r['sha256'],r['path']
b=json.loads((H/'measurements.json').read_bytes())
for p,s in b['source_dependencies'].items(): assert sha(R/p)==s,p
v=json.loads((H/'validation.json').read_bytes());assert all(v['checks'].values())
m=json.loads((H/'uncertainty_masks.json').read_bytes());x,y,z,w=m['roi_px']
for name,d in m['masks'].items():
 n=0;previous=(-1,-1)
 for row,left,right in d['runs_y_x0_x1']:
  assert 0<=row<w-y and 0<=left<right<=z-x
  assert row>previous[0] or (row==previous[0] and left>=previous[1])
  previous=(row,right);n+=right-left
 assert n==d['true_pixels'],name
c=json.loads((H/'measurement_contract.json').read_bytes())
assert not c['whole_image_affine_inverse_allowed'] and not c['geometry_created']
assert c['uncertainty_interpretation']['working_band_is_not_guaranteed_contour_error_bound']
assert not b['heldout_chimney_consistency']['pass_as_same_metric_chimney']
print(json.dumps({'status':'PASS_SEALED_IMAGE_ONLY_AUDIT','sealed_files':len(a['files']),'source_dependencies':len(b['source_dependencies']),'masks':len(m['masks']),'global_registration_accepted':False,'metric_roof_reconstruction_accepted':False},sort_keys=True))
