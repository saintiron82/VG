"""Retarget frozen source-bound normals only when every targeted render group is exact.

This does not verify or approve changed, non-targeted body geometry. That requires
its own source-owner/exterior tests. It never changes the old sidecar/render.
"""
from pathlib import Path
import json,gzip,hashlib,argparse

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def load(p):
 b=Path(p).read_bytes();raw=gzip.decompress(b)if str(p).endswith('.gz')else b
 return json.loads(raw),sha(b)
def bind(old,new,side,old_sha,new_sha,side_sha):
 if old.get('schema')!='riverstone.voxel.render.v1' or new.get('schema')!=old['schema']:raise ValueError('common render schema required')
 if side.get('schema')!='riverstone.roof.normal_split_sidecar.v1':raise ValueError('normal source schema required')
 if side.get('render_sha256')!=old_sha:raise ValueError('old source pin mismatch')
 if not old_sha or not new_sha or not side_sha:raise ValueError('all file pins required')
 targets=set()
 for row in side.get('patches',[])+side.get('splits',[]):
  gi=row.get('group_index');qi=row.get('quad_index')
  if not isinstance(gi,int)or not isinstance(qi,int)or gi<0 or qi<0:raise ValueError('integral nonnegative target required')
  if gi>=len(old.get('groups',[]))or qi>=len(old['groups'][gi]['quads']):raise ValueError('target outside old source')
  targets.add(gi)
 if not targets:raise ValueError('empty targets')
 for material,value in old['materials'].items():
  if material not in new['materials'] or canonical(value)!=canonical(new['materials'][material]):raise ValueError('original palette is not a preserved subset')
 appended=sorted(set(new['materials'])-set(old['materials']))
 proof=[]
 for gi in sorted(targets):
  if gi>=len(new.get('groups',[])):raise ValueError('new target group missing')
  a,b=old['groups'][gi],new['groups'][gi]
  if canonical(a)!=canonical(b):raise ValueError('target material/quad ordering or geometry changed')
  material=a['material']
  if canonical(old['materials'][material])!=canonical(new['materials'].get(material)):raise ValueError('target material palette changed')
  proof.append({'group_index':gi,'material':material,'ordered_group_sha256':sha(canonical(a)),'palette_sha256':sha(canonical(old['materials'][material])),'quads':len(a['quads'])})
 result=side.copy();result['render_sha256']=new_sha
 provenance={'original_render_sha256':old_sha,'original_sidecar_sha256':side_sha,'new_render_sha256':new_sha,'groups_exact':proof,'changed_non_target_geometry_approval':False,'source_normals_modified':False,'original_palette_preserved_subset':True,'appended_materials':{key:new['materials'][key]for key in appended}}
 result['compatible_binding']=provenance
 return result,provenance

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--old-render',required=True);ap.add_argument('--new-render',required=True);ap.add_argument('--old-sidecar',required=True);ap.add_argument('--expected-sidecar-sha',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
 old,oh=load(args.old_render);new,nh=load(args.new_render);side,sh=load(args.old_sidecar)
 if sh!=args.expected_sidecar_sha:raise ValueError('frozen sidecar bytes mismatch')
 result,proof=bind(old,new,side,oh,nh,sh);out=Path(args.output)
 if out.exists():raise ValueError('output already exists; preserve revisions')
 raw=canonical(result);encoded=gzip.compress(raw,compresslevel=9,mtime=0);out.write_bytes(encoded)
 proof.update({'output_sha256':sha(encoded),'raw_sha256':sha(raw),'gzip_bytes':len(encoded),'raw_bytes':len(raw),'old_render_path':args.old_render,'new_render_path':args.new_render,'old_sidecar_path':args.old_sidecar})
 out.with_suffix(out.suffix+'.binding.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
