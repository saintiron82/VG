"""Connect authored placement packs to the existing common renderer; no new engine."""
import json,hashlib,copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def relative(p):
 p=Path(p);return str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
def main():
 source=CITY/'registered_source/plan.json';source_sha=sha(source);plan=json.loads(source.read_bytes());packs={};assets={};instances=[];remove=[];inputs=[]
 def read(name,path):
  p=CITY/path;data=json.loads(p.read_bytes());assert data.get('source_plan_sha256',data.get('registered_source_sha256'))==source_sha,(name,'source mismatch');inputs.append({'name':name,'path':relative(p),'sha256':sha(p)});packs[name]=data;return data
 ordinary=read('ordinary','assemblies/ordinary/registered/resolved_placements.json')
 forest=read('woodland','assemblies/landscape/registered_woodland/resolved_placements.json')
 for name,pack,manifest in [('ordinary',ordinary,ordinary['assets']),('woodland',forest,forest['assets'])]:
  for key,a in manifest.items():
   entry=copy.deepcopy(a);entry['render_path']=relative(a.get('render_path',a.get('compiled_asset_ref')));entry['master_path']=relative(a['master_path'])
   assert sha(ROOT/entry['render_path'])==a['render_sha256'],key
   assets[key]=entry
  for p in pack['placements']:
   item={k:copy.deepcopy(p[k]) for k in ['id','asset_key','position_m','yaw_rad','palette_id','palette_override'] if k in p};item.setdefault('palette_id','native');item.setdefault('palette_override',{});item['source_pack']=name;item['scale']=[1,1,1]
   instances.append(item)
   if name=='ordinary':remove += [p['source_mass_id'],p['source_mass_id']+':support']
 pack=dict(schema='riverstone.registered_integration.r1',status='actual_common_candidate_not_traversal_approved',source_plan_sha256=source_sha,terrain_module='world_city.concept_city_v3.registered_topography.revisions.r01_ownership.author',access_overlay={},floor_ownership_masks=[],remove_proxy_ids=remove,replace_plot_ids=[],replace_landmark_groups=[],common_instances=instances,common_assets=assets,provenance=dict(input_packs=inputs,new_voxel_compile_count=0,common_core_modified=False,instance_scale_policy='native geometry, no whole-house scaling',open_exceptions=['Estate replacements pending exterior access repair.','Ordinary reserved frontage grade is not capsule-approved.','Landmark common modules and port integration are staged separately.','Finite review terrain ownership is not final compiled macro terrain.']))
 (HERE/'ordinary_woodland_candidate.json').write_text(json.dumps(pack,separators=(',',':'))+'\n');print(json.dumps({'source':source_sha,'instances':len(instances),'assets':len(assets),'inputs':inputs},indent=2))
if __name__=='__main__':main()
