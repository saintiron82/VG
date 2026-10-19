"""Fresh two-source regeneration and exact finite removed-cell proof."""
from author_gates import *

def main():
 pack=load(OUT/'resolved_native_candidate.json');rows=[]
 for owner in pack['owners']:
  p=next(p for p in pack['placements']if p['id']==owner['new_native_id']);a=next(a for a in pack['assets']if a['id']==p['asset_key']);old=coordinate_planes.compile_master(load(ROOT/owner['original_source']['path']),{'pitch':a['pitch_m']},max_candidate_cells=1500000,max_output_cells=250000);new=coordinate_planes.compile_master(load(ROOT/a['source']['path']),{'pitch':a['pitch_m']},max_candidate_cells=1500000,max_output_cells=250000);om={tuple(c[:3]):c for c in old['cells']};nm={tuple(c[:3]):c for c in new['cells']};removed=[c for k,c in om.items()if k not in nm];added=[c for k,c in nm.items()if k not in om];changed=[c for k,c in nm.items()if k in om and c!=om[k]];ledger=[]
  for c in removed:
   center=[old['grid_origin'][i]+(c[i]+.5)*a['pitch_m']+p['position_m'][i]for i in range(3)];ledger.append(dict(source_cell=c,world_center_xyz_m=center,inside_finite_opening=any(geo.point_in_convex_polygon([center[0],center[2]],q,1e-9)for q in owner['all_finite_opening_polygons_xz_m']),above_retained_floor=center[1]>=8))
  tests=dict(original_cache_exact=core.digest(render_data.make_render_data(old))==core.digest(load(ROOT/owner['original_cache']['path'])),new_cache_exact=core.digest(render_data.make_render_data(new))==core.digest(load(ROOT/a['cache']['path'])),only_finite_above_floor_cells_removed=bool(removed)and all(r['inside_finite_opening']and r['above_retained_floor']for r in ledger),no_added_or_changed_cells=not added and not changed,source_operations_preserved=owner['original_operations_preserved']and owner['all_other_components_exact'],native_pose_exact=p['yaw_rad']==0 and p['scale']==[1,1,1]);rows.append(dict(site_id=owner['site_id'],tests=tests,removed_cell_count=len(removed),removed_cells=ledger,source=owner['original_source'],new_source=a['source'],new_cache=a['cache']));print(owner['site_id'],tests,len(removed),flush=True)
 write('source_cell_tests.json',dict(status='PASS'if all(all(r['tests'].values())for r in rows)else'HELD',owners=rows,native_pack=ref(OUT/'resolved_native_candidate.json'),runtime_ready=False))
if __name__=='__main__':main()
