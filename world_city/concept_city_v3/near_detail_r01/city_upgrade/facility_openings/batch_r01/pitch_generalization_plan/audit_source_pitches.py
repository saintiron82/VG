"""Read-only native grid inventory and validation proposal; no occupancy compilation."""
from pathlib import Path
import collections,hashlib,json,math
ROOT=Path(__file__).resolve().parents[7]
U=ROOT/'world_city/concept_city_v3/near_detail_r01/city_upgrade'
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def main():
 audit_path=U/'house_extensions/facility_opening_audit/asset_audit.json';cat_path=U/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json';audit=load(audit_path);cat=load(cat_path);rows=[]
 for r in audit['assets']:
  mp=ROOT/r['source_master_path'];rp=ROOT/r['render_path'];assert sha(mp)==r['source_sha256'] and sha(rp)==r['render_sha256'];m=load(mp);render=load(rp);pitch=render['pitch'];origin=render['grid_origin'];assert pitch==r['cache_pitch_m'] and origin==m['grid_origin'];ratio=pitch/.05;assert abs(ratio-round(ratio))<1e-8
  vertices=offnative=offfine=0
  for g in render['groups']:
   for q in g['quads']:
    for v in q:
     vertices+=1;offnative+=any(abs((v[j]-origin[j])/pitch-round((v[j]-origin[j])/pitch))>1e-7 for j in range(3));offfine+=any(abs(v[j]/.05-round(v[j]/.05))>1e-7 for j in range(3))
  assert offnative==offfine==0
  cuts=[{'component':c['id'],'operation':o['id'],'shape':o['shape']['kind']} for c in m['components'] for o in c['operations'] if o['action']=='cut'];variants=[{'asset_key':x['asset_key'],'master_path':x['emitted_master_path'],'master_sha256':x['emitted_master_sha256']} for x in cat['assets'] if x.get('native_asset_key',x['asset_key'])==r['asset_key']]
  rows.append({'asset_key':r['asset_key'],'placements':r['city_placements'],'source_master_path':r['source_master_path'],'source_master_sha256':r['source_sha256'],'source_render_path':r['render_path'],'source_render_sha256':r['render_sha256'],'native_pitch_m':pitch,'grid_origin_m':origin,'fine_pitch_m':.05,'native_to_fine_integer_ratio':round(ratio),'source_cell_count':render['cell_count'],'source_quad_count':render['quad_count'],'source_bounds':render['bounds'],'actual_vertex_grid_check':{'vertices':vertices,'off_native_grid_vertices':offnative,'off_fine_grid_vertices':offfine},'component_cuts':cuts,'assembly_cut_count':len(m.get('assembly_cuts',[])),'source_roles':r['source_roles'],'entrance_metadata':r['entrance_metadata'],'roof_variants':variants})
 for row in rows:
  if row['native_pitch_m']==.5:
   for field in ['roof_variants','component_cuts','entrance_metadata','source_roles','source_bounds']:row.pop(field)
 report={'schema':'riverstone.facility.native_pitch_inventory.v1','compile_calls':0,'source_modified':False,'runtime_modified':False,'implementation':{'path':str(Path(__file__).relative_to(ROOT)),'sha256':sha(Path(__file__))},'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [audit_path,cat_path]],'asset_count':len(rows),'placement_count':sum(r['placements'] for r in rows),'pitch_asset_counts':dict(collections.Counter(str(r['native_pitch_m']) for r in rows)),'non_half_pitch_asset_count':sum(r['native_pitch_m']!=.5 for r in rows),'non_half_pitch_placement_count':sum(r['placements'] for r in rows if r['native_pitch_m']!=.5),'assets':rows,'all_file_hash_and_grid_checks_pass':True}
 (HERE/'inventory.json').write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['assets','inputs','implementation']}))
if __name__=='__main__':main()
