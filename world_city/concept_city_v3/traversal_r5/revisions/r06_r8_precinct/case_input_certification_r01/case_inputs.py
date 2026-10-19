"""Conservative transitive runtime-input identity for unchanged-controller cases."""
import argparse,copy,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def fingerprint(data,route,runner_hashes,asset_bytes):
 # Paths are location metadata only. Every loaded byte hash, format, placement,
 # building, route value, hierarchy and controller setting is retained.
 placements=[copy.deepcopy(data['placements'][p])for p in route['placement_ids']]
 keys=sorted({p['asset_key']for p in placements});assets={}
 for k in keys:
  a=copy.deepcopy(data['assets'][k]);a.pop('render_path',None);assert a['render_sha256']==asset_bytes[k];assets[k]=a
 value=dict(route=route,placements_in_load_order=placements,assets=assets,buildings_in_load_order=[data['buildings'][p]for p in route['building_ids']],runner_hashes=runner_hashes,scene_sha256=data['sources']['scene']['sha256'],engine_launch_contract=dict(headless=True,disable_render_loop=True,fixed_fps=60))
 return dict(sha256=canonical(value),value=value)
def manifest(prepared):
 d=json.loads(prepared.read_bytes());hashes={n:sha(prepared.parent/n)for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot']};assert hashes['Traversal.gd']=='09756c7a2686eeef16f79171a089495b0ac10b3f41c5f2949ed8f9131ca14381';assert hashes['RenderData.gd']=='40dc99d08818c8df1a4df13a951cc7b814a6b26d5dc8f1e64901a2c41e794af6'
 actual={}
 for k,a in d['assets'].items():
  p=ROOT/a['render_path'];actual[k]=sha(p);assert actual[k]==a['render_sha256']
 return dict(schema='riverstone.actual_case_transitive_input_identity.v1',prepared=dict(path=str(prepared.relative_to(ROOT)),sha256=sha(prepared)),scene=d['sources']['scene'],runner_hashes=hashes,cases={r['id']:fingerprint(d,r,hashes,actual)for r in d['routes']})
def compare(old,new):
 oldids=set(old['cases']);newids=set(new['cases']);same=sorted(k for k in oldids&newids if old['cases'][k]['sha256']==new['cases'][k]['sha256']);changed=sorted((oldids&newids)-set(same))
 return dict(identical_case_ids=same,changed_case_ids=changed,added_case_ids=sorted(newids-oldids),removed_case_ids=sorted(oldids-newids),required_replay_case_ids=sorted(set(changed)|(newids-oldids)),policy='Only a previously passing case with an identical transitive digest and matching engine/settings result may be reused. Changed or added cases require their own unchanged-controller replay. No prior failed case is promoted by this comparison.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--old',type=pathlib.Path,required=True);ap.add_argument('--new',type=pathlib.Path);ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args();out=args.output.resolve();assert out.is_relative_to(ROOT)and not out.exists();old=manifest(args.old.resolve());new=manifest(args.new.resolve())if args.new else None;d=dict(old=old,new=new,comparison=compare(old,new)if new else None)
 with out.open('x')as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
 print(json.dumps(dict(path=str(out.relative_to(ROOT)),sha256=sha(out),old_cases=len(old['cases']),new_cases=len(new['cases'])if new else None,comparison=d['comparison'])))
if __name__=='__main__':main()
