"""Explicit civic-parcel supersession and cached landmark scene orchestration."""
import json,copy,hashlib,math
from pathlib import Path
HERE=Path(__file__).parent;ROOT=HERE.resolve().parents[2];CITY=ROOT/'world_city/concept_city_v3'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=HERE/'ordinary_woodland_candidate.json';out=json.loads(p.read_bytes());native=CITY/'assemblies/landmarks/registered/assembly_r01/resolved_placements.json';d=json.loads(native.read_bytes());overlay_path=CITY/'assemblies/landmarks/registered/assembly_r01/supersession_overlay.json';ov=json.loads(overlay_path.read_bytes());source_sha=out['source_plan_sha256'];assert d['source_plan']['sha256']==ov['source_plan']['sha256']==source_sha
 remove=set(ov['remove_ordinary_placement_ids']);out['common_instances']=[p for p in out['common_instances'] if p['id'] not in remove]
 out['remove_proxy_ids']+=list(remove)+[s+':support' for s in remove]+[s+':owned_foundation' for s in remove]
 out['access_overlay']={'remove_path_ids':ov['remove_path_ids'],'add_paths':[],'replace_roads':[]}
 out['replace_landmark_groups']=ov['remove_landmark_component_group_ids']
 out['floor_ownership_masks']=[{'id':f['id'],'polygon_xz_m':f['polygon_xz_m'],'floor_y_m':f['floor_y_m'],'owner_placement_id':f['placement_id']} for f in d['owned_floors']]
 for a in d['assets']:
  assert sha(ROOT/a['cache']['path'])==a['cache']['sha256']
  assert sha(ROOT/a['source']['path'])==a['source']['sha256']
  out['common_assets'][a['id']]={'render_path':a['cache']['path'],'render_sha256':a['cache']['sha256'],'master_path':a['source']['path'],'master_sha256':a['source']['sha256'],'quad_count':a['quad_count'],'pitch_m':a['pitch_m']}
 for p in d['placements']:
  assert p['scale']==[1,1,1]
  out['common_instances'].append({'id':p['id'],'asset_key':p['asset_key'],'position_m':p['position_m'],'yaw_rad':p['yaw_rad'],'scale':[1,1,1],'palette_id':'native_registered_landmark','palette_override':{},'source_pack':'registered_landmarks'})
 out['terrain_module']='world_city.concept_city_v3.registered_topography.revisions.r02_assembly_overlay.author'
 out['provenance']['input_packs'] += [{'name':'landmarks','path':str(native.relative_to(ROOT)),'sha256':sha(native)},{'name':'civic_supersession','path':str(overlay_path.relative_to(ROOT)),'sha256':sha(overlay_path)}]
 out['provenance']['superseded_ordinary_ids']=sorted(remove);out['provenance']['open_exceptions']=['Estate replacements remain held pending exterior gate repair.','New landmark source openings exist, but exterior access routes are under review.','Ordinary frontage grades and sampled foundations are not capsule-approved.','Terrain is an exact-owner review mesh; compiled macro terrain remains staged.','Port/bridge/gardens are ongoing stages.']
 out['status']='native_common_landmark_ordinary_woodland_visual_candidate';out['counts']={'ordinary_houses':sum(p['source_pack']=='ordinary' for p in out['common_instances']),'landmark_modules':len(d['placements']),'woodland_instances':sum(p['source_pack']=='woodland' for p in out['common_instances']),'owned_landmark_floors':len(d['owned_floors'])}
 (HERE/'common_city_candidate.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(out['counts']))
if __name__=='__main__':main()
