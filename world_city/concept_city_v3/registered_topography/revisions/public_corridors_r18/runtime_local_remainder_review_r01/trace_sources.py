import json,collections,math
from pathlib import Path
from ..north_junction_transition_r01.author import ROOT,CITY,HERE as N,a,g,ref,dump
HERE=Path(__file__).resolve().parent

def key(t):return tuple(sorted(tuple(v)for v in t))
def main():
 d=json.loads((HERE/'upper_contour_local_faces.json').read_bytes());needles=[r for r in d['rows']if r['xz_area64_m2']<1e-8];targets={key(r['triangle_xyz_m']):r for r in needles};bp=N/'activation_binding.json';binding=json.loads(bp.read_bytes());matches=[]
 for pi,rr in enumerate(binding['patches']):
  pp=ROOT/rr['path'];patch=json.loads(pp.read_bytes())
  for ei,e in enumerate(patch['surface_edits']):
   if e['material']!='road':continue
   for ri,t in enumerate(e['replacement_triangles_xyz_m']):
    if key(t)in targets:matches.append(dict(patch_index=pi,patch=rr,producer_id=patch['id'],source_edit_index=ei,original_source_triangle_index=e['triangle_index'],original_source_triangle_sha256=e['source_triangle_sha256'],replacement_index=ri,replacement_count=len(e['replacement_triangles_xyz_m']),replacement_triangle_sha256=a.canonical_sha(t),triangle_xyz_m=t,collision_source=targets[key(t)]))
 out=dict(sources=[ref(bp),ref(HERE/'upper_contour_local_faces.json')],matches=matches,needle_count=len(needles),unmatched=[r for r in needles if not any(key(r['triangle_xyz_m'])==key(x['triangle_xyz_m'])for x in matches)]);dump(HERE/'upper_contour_source_matches.json',out);print('needles',len(needles),'matches',len(matches),'edits',collections.Counter((r['patch_index'],r['source_edit_index'],r['original_source_triangle_index'],r['replacement_count'])for r in matches))
 for x in out['unmatched']:print('unmatched',x['source_face_key'])
if __name__=='__main__':main()
