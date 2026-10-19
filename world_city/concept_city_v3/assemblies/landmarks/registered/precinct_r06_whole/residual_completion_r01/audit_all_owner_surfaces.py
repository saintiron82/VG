"""Actual R7 surface screening for every protected owner, including civic/port."""
from pathlib import Path
import sys,json
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from plan_grounds import terrain_raster
from build_ledger import *
OUT=Path(__file__).resolve().parent

def main():
 m=np.load(BASE/'owner_masks.npz');scene=terrain.load_scene();h,g,public=terrain_raster(scene,b.buffer(m['labels']>0,30));np.savez_compressed(OUT/'all_owner_terrain_raster.npz',height=h,grade=g,actual_road_top=public);ledger=load(BASE/'actual_owner_use_ledger.json');out=[]
 for j,o in enumerate(ledger['owners'],1):
  own=m['labels']==j;raw=own&~m['native']&~m['reserved']&~m['water']&~m['public'];observed=raw&np.isfinite(h);flat=observed&(g<1e-7);slope=observed&(g>=1e-7)&(g<=.12);steep=observed&(g>.12);out.append({'owner_id':o['owner_id'],'unassigned_after_baseline_grid_m2':b.area(raw),'actual_surface_observed_grid_m2':b.area(observed),'actual_level_surface_grid_m2':b.area(flat),'actual_gradual_surface_grid_m2':b.area(slope),'actual_steep_surface_grid_m2':b.area(steep),'actual_road_colored_grid_m2':b.area(raw&public),'actual_surface_uncovered_grid_m2':b.area(raw&~np.isfinite(h)),'observed_floor_bands_m':sorted(set(np.round(h[flat],3).tolist())),'policy':'One metre source-screen evidence only. Public ownership is not inferred from material; native-floor holes require cache ownership before being counted.'})
 (OUT/'all_owner_surface_audit.json').write_text(json.dumps({'scene':ref(terrain.SCENE_PATH),'owner_ledger':ref(BASE/'actual_owner_use_ledger.json'),'owners':out,'all_17_owner_windows_sampled':True},indent=2)+'\n')
 for r in out:print(r['owner_id'],r['actual_level_surface_grid_m2'],r['actual_surface_uncovered_grid_m2'],r['actual_road_colored_grid_m2'],r['observed_floor_bands_m'])
if __name__=='__main__':main()
