"""Reproduce a real retained-bank obstruction before district promotion."""
import json
from . import author as a
from .side_clearance import SideIndex
if __name__=='__main__':
 source=a.CITY/'traversal_r5/revisions/r06_r8_precinct/diagnostics/failure_geometry.json';d=json.loads(source.read_text());scene=a.load_scene();first=d['scene_contact_samples'][0];x,y,z=first['target'];p=[[x-.45,z-.45],[x+.45,z-.45],[x+.45,z+.45],[x-.45,z+.45]]
 matches=[]
 for r in d['actual_contact_bank_triangles']:
  actual=scene['surfaces']['bank'][r['triangle_index']*3:r['triangle_index']*3+3]
  if actual!=r['triangle_xyz_m']or a.canonical_sha(actual)!=r['source_triangle_sha256']:raise ValueError('Changed retained failure face')
  matches.append(r['triangle_index'])
 result=SideIndex(scene,[p]).audit([dict(id='KNOWN_R8_FIRST_STAIR_CONTACT',polygon_xz_m=p,floor_y_m=y)])
 contacts={r['triangle_index']for r in result['contacts']if r['material']=='bank'}
 if not{10047,10048}<=contacts:raise ValueError('Real zero-plan-area obstruction was missed')
 report=dict(schema='riverstone.r17.known_bank_failure_regression.v1',status='PASS_CHECKER_DETECTS_PRESERVED_FAILURE',base_scene_sha256=a.SCENE_SHA256,diagnostic_ref=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),identical_prior_source_indices=matches,clear_volume=dict(polygon_xz_m=p,floor_y_m=y,headroom_m=2.2),audit=result,activation=False,scope='Checker regression only. This does not fix the separate native stairs or change any source face.')
 out=a.HERE/'known_bank_failure_regression.json'
 if out.exists():raise SystemExit('Preserve bank regression')
 out.write_text(json.dumps(report,separators=(',',':'))+'\n');print(report['status'],sorted(contacts),a.sha(out))
