"""Audit common's retained source ramp against the exact actual R7 surfaces."""
from pathlib import Path
import sys,json
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from connect_routes import *
from retained_walks import RetainedWalkIndex
OUT=Path(__file__).resolve().parent

def main():
 src=CITY/'assemblies/landscape/registered/resolved_placements.json';d=load(src);row=next(r for r in d['external_connections']if r['id']=='PUBLIC_TERRACE_PARK:public_approach');ext=row['external_surface'];polys=ext['polygon_regions_xz_m'];scene=terrain.load_scene();index=RetainedWalkIndex(scene,polys);checks=[terrain.audit_polygon(index,p,None)for p in polys];sides=SideIndex(scene,polys);sc=sides.audit([{'id':f'COMMON_SOURCE_ENTRY:{i}:{j}','polygon_xz_m':p['polygon_xz_m'],'plane_y_xz_m':p['plane_y_xz_m']}for i,c in enumerate(checks)for j,p in enumerate(c['source_pieces'])]);out={'source':ref(src),'row':row,'scene':ref(terrain.SCENE_PATH),'checks':checks,'bank_checks':sc,'pass':all(c['passes_existing_surface']for c in checks)and not sc['contacts'],'runtime_ready':False};(OUT/'common_entry_surface_audit.json').write_text(json.dumps(out,indent=2)+'\n');print('common',out['pass'],'checks',[(c['missing_area_m2'],c['max_actual_triangle_grade'])for c in checks],'banks',len(sc['contacts']))
if __name__=='__main__':main()
