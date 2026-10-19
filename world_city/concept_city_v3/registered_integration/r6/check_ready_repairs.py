"""Independent handoff composition of sealed clergy + southern repairs only."""
import json
from . import apply_packs as a
from . import merge_patches as m
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import frozen

def main():
 base=a.load(a.BASE_PATH,a.BASE_SHA256)
 refs=[('traversal_r5/revisions/r02/scene_patch.json','1a0b4d6c30205f5d5579afef3d3f928deb143260712caf6539b730b7f282c6d9'),('assemblies/landmarks/registered/precinct_r05_ground/local_frame_r01/corner_repair_r01/terrain_patch/surface_patch.json','b2a352115cc4b8368c7719290d269b0afc97a24d157cef99e53e2b5b9ff751e8')]
 merged=m.merge([a.load(a.CITY/path,h) for path,h in refs]);m.validate_against_scene(base,merged)
 out=frozen.apply_edits(base,merged)
 ledgers=[]
 for name in ['southern_repair','clergy_repair']:
  p=a.HERE/(name+'_pack.json');out,ledger=a.apply_pack(out,a.load(p),name,dict(path=a.rel(p),sha256=a.sha(p)));ledgers.append(ledger)
 assert len(out['common_instances'])==len(base['common_instances'])+1
 assert out['inspection_cameras'] is base['inspection_cameras']
 assert out['bridge_mechanism'] is base['bridge_mechanism']
 assert out['surfaces']['water'] is base['surfaces']['water']
 bank_edits=[r for r in merged['surface_edits'] if r['material']=='bank']
 assert len(bank_edits)==10
 for r in bank_edits:
  for v in base['surfaces']['bank'][r['triangle_index']*3:r['triangle_index']*3+3]:
   assert 242<=v[0]<=330 and 13.94<=v[1]<=14.01 and -353<=v[2]<=-279, 'Unexpected river/bank edit outside clergy retaining strips'
 # frozen.apply_edits already asserts every unedited vertex object/value/order.
 assert len(out['boxes'])==len(base['boxes'])
 report=dict(status='pass_sealed_local_repair_composition',scene_written=False,base_scene_sha256=a.BASE_SHA256,patch_inputs=[dict(path=a.rel(a.CITY/p),sha256=h) for p,h in refs],source_edits=len(merged['surface_edits']),appended_triangles=sum(len(v)//3 for v in merged['appended_surfaces'].values()),patch_ids=[p['id'] for p in merged['source_patches']],instance_count=len(out['common_instances']),water_unchanged=True,bank_unchanged_except_ten_declared_clergy_retaining_triangles=True,bridge_mechanism_unchanged=True,registered_camera_unchanged=True,ledgers=ledgers,limit='No actual R6 frame or combined capsule traversal yet; merchant and productive-ground additions remain separate.')
 dest=a.HERE/'ready_repairs_review.json';assert not dest.exists();dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['ledgers','patch_inputs']},indent=2))
if __name__=='__main__':main()
