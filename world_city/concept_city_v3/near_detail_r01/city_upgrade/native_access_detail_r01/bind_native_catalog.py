"""Rebind exact existing common modules to clarified source-visual offset scope."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;U=H.parent;R=U.parents[3];D=U.parents[1]/'playable_detail_r01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 p=H/'generated/source_plan_r02.json';plan=load(p);old=H/'generated/source_plan.json';m=load(H/'generated/modules_r01/catalog.json')
 assert m['source_plan_sha256']==sha(old)
 assert plan['module_demand']==load(old)['module_demand']
 for row in m['modules']:
  assert sha(R/row['render_path'])==row['render_sha256'] and sha(R/row['master_path'])==row['master_sha256']
 m['source_plan_sha256']=sha(p);m['source_dependencies'].pop(str(old.relative_to(R)));m['source_dependencies'][str(p.relative_to(R))]=sha(p);m['reuses_unchanged_modules_from']='generated/modules_r01/catalog.json';m['scope_note']=plan['source_collision_note'];mp=H/'generated/modules_r01/catalog_r02.json';write(mp,m)
 c={'schema':'riverstone.native_access_detail.runtime.v1','source_city_index_sha256':plan['source_city_index_sha256'],'source_plan_path':str(p.relative_to(R)),'source_plan_sha256':sha(p),'module_catalog_path':str(mp.relative_to(R)),'module_catalog_sha256':sha(mp),'radius_m':8.0,'fade_start_m':4.0,'fade_end_m':7.0,'maximum_active_modules':120,'maximum_mesh_bytes':24000000,'update_seconds':.3,'observer_refresh_distance_m':1.0,'collision_change':False,'whole_city_upgrade_complete':False,'offset_scope':'Additional distance from original visible source surface, not total existing visual-collision gap'}
 write(D/'native_access_catalog.json',c)
 print(json.dumps({'modules_reused':len(m['modules']),'resampling':False,'source_plan_sha256':sha(p),'module_catalog_sha256':sha(mp)}))
if __name__=='__main__':main()
