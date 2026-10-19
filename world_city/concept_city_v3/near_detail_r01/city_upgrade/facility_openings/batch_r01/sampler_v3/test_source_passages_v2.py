"""Positive/negative rectangle-ray probes; no voxel compile or generated mesh."""
import json,hashlib
from pathlib import Path
import verify_source_passages_v2 as v

def main():
    a=v.a;p={'axis':2,'point_m':[.25,1.25,0.0],'interval_m':[-1,1]};tests={}
    wall=a.rect_quad([0,1,.5,1.5],2,[0,1],0,1);tests['blocking_face_detected']=v.hits(wall,p)
    tests['opposing_blocking_face_detected']=v.hits(list(reversed(wall)),p)
    tests['parallel_floor_not_blocking']=not v.hits(a.rect_quad([0,-1,.5,1],1,[0,2],0,1),p)
    tests['outside_tangent_not_blocking']=not v.hits(a.rect_quad([.5,1,1,1.5],2,[0,1],0,1),p)
    tests['outside_interval_not_blocking']=not v.hits(a.rect_quad([0,1,.5,1.5],2,[0,1],2,1),p)
    source={'components':[],'instances':[],'assembly_cuts':[{'id':'gate','shape':{'kind':'box','min':[-1,0,-.5],'max':[1,3,.5]},'transform':{'translation':[2,0,-4]}}]};rows=v.cut_inventory(source);tests['assembly_cut_found_once']=len(rows)==1;tests['assembly_cut_bytes_preserved']=rows[0][2]==source['assembly_cuts'][0];tests['assembly_cut_world_transform_preserved']=rows[0][3]['translation']==[2,0,-4];assert all(tests.values());report={'schema':'riverstone.facility.open_passage_ray_tests.v1','all_pass':True,'tests':tests,'driver_sha256':a.sha(__file__),'driver_reference':{'path':str(Path(__file__).relative_to(a.ROOT)),'sha256':a.sha(__file__)},'verifier_sha256':a.sha(v.__file__),'compile_calls':0};Path(__file__).with_name('source_passage_v2_tests.json').write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(report))
if __name__=='__main__':main()
