#!/usr/bin/env python3
"""Small read-only preflight: refuse repeated source-face owners before merging."""
import argparse,json,pathlib,hashlib
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def main():
 p=argparse.ArgumentParser();p.add_argument('--patch',action='append',required=True,type=pathlib.Path);p.add_argument('--report',required=True,type=pathlib.Path);a=p.parse_args();assert a.report.resolve().is_relative_to(H)
 owners={};refs=[];bases=set();conflicts=[]
 for path in a.patch:
  path=path.resolve();assert path.is_relative_to(ROOT);data=json.loads(path.read_bytes());sha=hashlib.sha256(path.read_bytes()).hexdigest();bases.add(data['base_scene_sha256']);identity=data['id'];refs.append({'path':str(path.relative_to(ROOT)),'sha256':sha,'patch_id':identity,'source_face_edits':len(data['surface_edits'])})
  for row in data['surface_edits']:
   key=(row['material'],row['triangle_index'])
   if key in owners:conflicts.append({'material':key[0],'source_triangle_index':key[1],'first_owner':owners[key],'second_owner':identity})
   else:owners[key]=identity
 ok=len(bases)==1 and not conflicts
 result={'schema':'riverstone.r10.interface_source_owner_preflight.v1','status':'PASS_INDEX_DISJOINT_ONLY'if ok else'REJECTED_BEFORE_INTEGRATION','base_scene_hashes':sorted(bases),'patches':refs,'unique_source_faces':len(owners),'source_face_conflicts':conflicts,'limitations':['Read-only source-index/base-identity check, not source geometry validation or a runtime pass.','Actual source hash validation, native identity checks and renderer-equivalent finite composition are separately required.']}
 with a.report.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'conflicts':len(conflicts),'unique_source_faces':len(owners)}));return 0 if ok else 2
if __name__=='__main__':raise SystemExit(main())
