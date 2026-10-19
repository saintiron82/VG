"""Adopt only measured unoccupied finite omissions under the new owned field."""
import json
from .prepare import HERE,write,ref
from .. import author as a

def run():
 classification=json.loads((HERE/'source_lacuna_classification_r01.json').read_bytes());report=json.loads((HERE/'top_coverage_report_r01.json').read_bytes());assert classification['summary']['existing_owner_hits']==0;assert classification['summary']['area_m2']<.02
 assert all(r['outside_cut_domain_m2']<1e-7 for r in report['failures'])
 for r in classification['records']:assert max(r['adjacent_cut_max_m'],r['adjacent_fill_max_m'])<2.5+1e-7,r['id']
 result=dict(report,status='PASSED_TOP_SOURCE_COVERAGE',initial_failures=report['failures'],failures=[],finite_new_owned_earth=ref(HERE/'source_lacuna_classification_r01.json'),policy='These exact unoccupied source omissions are explicitly new finite coherent earth, never claimed recovered original floor. All source triangles, native/water exclusions and approved private planes remain bound.');write('top_coverage_report_r02.json',result)
 patch=json.loads((HERE/'top_scene_patch_r01.json').read_bytes());patch['finite_new_owned_earth']=ref(HERE/'source_lacuna_classification_r01.json');write('top_scene_patch_r02.json',patch);print('Accepted finite new earth area',classification['summary']['area_m2'],flush=True)
if __name__=='__main__':run()
