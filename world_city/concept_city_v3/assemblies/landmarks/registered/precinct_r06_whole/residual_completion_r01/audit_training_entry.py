"""Exact retained training entry check, without changing the R7 scene."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;sys.path.insert(0,str(BASE))
from connect_routes import *
from retained_walks import RetainedWalkIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
OUT=Path(__file__).resolve().parent

def main():
 source=CITY/'assemblies/landscape/registered/training/resolved_placements.json';d=load(source);scene=terrain.load_scene();ext=d['external_access_surfaces'][0];pts=[[-306,-132],[-308.9425903476245,-137.68143362578468],[-273.26657717500365,-151.67656047567058],[-270.2670847275223,-151.73174251534238]];polys=b.ribbon(pts,2)
 # The final existing three metre approach is audited as its exact source domain.
 polys+=ext['polygon_regions_xz_m'];polys+=b.ribbon([[-255.7695378980291,-151.9984557070894],[-254,-152]],2);public_terminal=b.rect(-255,-153,-253,-151);polys.append(public_terminal);index=RetainedWalkIndex(scene,polys);checks=[terrain.audit_polygon(index,p,None)for p in polys];sides=SideIndex(scene,polys);sc=sides.audit([{'id':f'TRAIN_RETAINED_ENTRY:{j}:{k}','polygon_xz_m':q['polygon_xz_m'],'plane_y_xz_m':q['plane_y_xz_m']}for j,c in enumerate(checks)for k,q in enumerate(c['source_pieces'])]);rows=[]
 for j,c in enumerate(checks):rows.append({'polygon_index':j,**c})
 out={'source':ref(source),'base_scene':ref(terrain.SCENE_PATH),'proposed_spur_polyline_xz_m':pts,'actual_public_terminal_polygon_xz_m':public_terminal,'polygon_parts_xz_m':polys,'checks':rows,'side_clearance':sc,'named_public_source_endpoint':ext['public_lane_endpoint'],'support_and_sides_pass':all(r['passes_existing_surface']for r in checks)and not sc['contacts'],'public_continuation_verified':False}
 (OUT/'training_entry_audit.json').write_text(json.dumps(out,indent=2)+'\n');print('support_side',out['support_and_sides_pass'],'bad',[(j,c['missing_area_m2'],c['max_actual_triangle_grade'])for j,c in enumerate(checks)if not c['passes_existing_surface']],'banks',len(sc['contacts']))
if __name__=='__main__':main()
