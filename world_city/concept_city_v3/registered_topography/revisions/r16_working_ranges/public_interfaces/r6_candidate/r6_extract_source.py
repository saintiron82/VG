"""Read-only extraction of exact corrected R6 triangles in one finite study box."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[6];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
SCENE=ROOT/'world_city/concept_city_v3/evidence/visual_registered_common_r6_apron_r01/scene.json'
EXPECTED='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2)+'\n')
def run():
 assert sha(SCENE)==EXPECTED
 old_names=['original_corridor_study.log','original_corridor_summary.json','shared_public_collar_proposal.json','source_read_manifest.json','study_terminal_profiles.py','terminal_00_original_corridor.json','terminal_01_original_corridor.json','terminal_overlap_audit.json']
 write('r6_prior_checkpoint_record.json',dict(status='PRESERVED_MIXED_PASS_CHECKPOINT_NEVER_ACCEPTED',files=[ref(HERE.parent/n)for n in old_names],interpretation='The pause interrupted a rerun after terminal_00 refreshed. Terminal_01 and summary/manifest belong to the preceding pass. Preserve all eight bytes; new R6 analysis supersedes their authority but not their diagnostic evidence.'))
 scene=json.loads(SCENE.read_bytes());records=[];bounds=[204.,126.,232.,155.];x0,z0,x1,z1=bounds
 for mat,vs in scene['surfaces'].items():
  arr=np.asarray(vs,dtype=float).reshape(-1,3,3);lo=arr.min(axis=1);hi=arr.max(axis=1)
  for i in np.where((hi[:,0]>=x0)&(lo[:,0]<=x1)&(hi[:,2]>=z0)&(lo[:,2]<=z1))[0]:
   tri=arr[i].tolist();p=[[v[0],v[2]]for v in tri]
   if geo.polygon_area(p)>1e-10:records.append(dict(material=mat,source_triangle_index=int(i),vertices_m=tri))
 old=json.loads((ROOT/'world_city/concept_city_v3/assemblies/ordinary/registered/working_ranges_r01/evidence/frozen_r5_local_triangles.json').read_bytes())
 oldkeys={r['material']+':'+json.dumps(r['vertices_m'],separators=(',',':')) for r in old['records']}
 matches=sum(r['material']+':'+json.dumps(r['vertices_m'],separators=(',',':'))in oldkeys for r in records)
 out=dict(schema='riverstone.r16_corrected_r6_exact_local_source.v1',scene=ref(SCENE),bounds_xz_m=bounds,records=records,record_count=len(records),identical_r5_local_triangle_count=matches,all_indices_are_actual_r6=True,source_code=ref(Path(__file__)),scope='Exact scene slices only; not authored terrain or an export.')
 write('r6_local_source.json',out);print('records',len(records),'old byte identical',matches,flush=True)
if __name__=='__main__':run()
