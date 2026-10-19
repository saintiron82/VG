"""Exact ready21 cross-pack ownership versus phase02 native geometry and access."""
from pathlib import Path
import sys,json
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from world_city.concept_city_v3.assemblies.landmarks.registered.coverage_r5_draft_01.project_native import roof_rectangles

def main():
 oldpath=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json';old=load(oldpath);packpath=BASE/'resolved_connected_placements.json';pack=load(packpath);cache={};shapes=[]
 for p in old['placements']:
  rp=p['cache']['path']
  if rp not in cache:
   m=load(ROOT/rp);cache[rp]=roof_rectangles(m,{g['material']for g in m['groups']})[0]
  shapes.extend((p['id'],b.xform(q,p))for q in cache[rp])
 ix=geo._SpatialIndex(16)
 for i,(_,q)in enumerate(shapes):ix.add(i,q)
 nativehits=[];routehits=[];domainhits=[];routecross=[]
 for u in pack['holdings']:
  for h in old['holdings']:
   area=sum(geo.intersection_area(u['polygon_xz_m'],p)for p in h['polygon_parts_xz_m'])
   if area>1e-7:domainhits.append({'ready_holding_id':u['id'],'phase02_holding_id':h['id'],'area_m2':area})
 for p in pack['placements']:
  rp=p['cache']['path']
  if rp not in cache:
   m=load(ROOT/rp);cache[rp]=roof_rectangles(m,{g['material']for g in m['groups']})[0]
  for q in [b.xform(q,p)for q in cache[rp]]:
   for i in ix.candidates(q):
    id,r=shapes[i];area=geo.intersection_area(q,r)
    if area>1e-7:nativehits.append({'ready_placement_id':p['id'],'phase02_placement_id':id,'area_m2':area})
 for r in pack['external_routes']:
  for q in r['ribbon_polygons_xz_m']:
   for i in ix.candidates(q):
    id,p=shapes[i];area=geo.intersection_area(q,p)
    if area>1e-7:routehits.append({'ready_route_id':r['id'],'phase02_placement_id':id,'area_m2':area})
   for oldr in old['internal_routes']:
    area=sum(geo.intersection_area(q,p)for p in oldr['ribbon_polygons_xz_m'])
    if area>1e-7:routecross.append({'ready_route_id':r['id'],'phase02_route_owner':oldr.get('holding_id'),'area_m2':area,'classification':'Shared walking region requires same actual surface ownership; not counted as native collision.'})
 result={'sources':{'ready21':ref(packpath),'phase02':ref(oldpath)},'phase02_native_placements_tested':len(old['placements']),'phase02_exact_native_polygons':len(shapes),'ready_native_placements_tested':len(pack['placements']),'ready_full_width_routes_tested':len(pack['external_routes']),'domain_contacts':domainhits,'native_contacts':nativehits,'route_native_contacts':routehits,'walking_region_crossings':routecross,'method':'Actual phase02 and ready21 cached native horizontal face unions at native pitch and rigid transforms, plus all exact route ribbons and source holding parts. No R7-only index assumption. Full native projections are conservative for overhead geometry.'};result['status']='PASS'if not(nativehits or routehits or domainhits or routecross)else'REVIEW_CONTACTS';(OUT/'ready21_phase02_crosspack.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],{k:len(result[k])for k in ('domain_contacts','native_contacts','route_native_contacts','walking_region_crossings')})
if __name__=='__main__':main()
