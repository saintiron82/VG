"""Addendum for later frozen water-crossing field reservations."""
from pathlib import Path
import sys,json
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def main():
 wp=CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/public_handoff.json';water=load(wp);reserved=[dict(id=r['id'],polygon_xz_m=q,kind='water_crossing_field')for r in water['finite_field_owners']for q in r['polygons_xz_m']]+[dict(r,kind='native_deck')for r in water['native_deck_holes']];ix=geo._SpatialIndex(16)
 for i,r in enumerate(reserved):ix.add(i,r['polygon_xz_m'])
 paths=[BASE/'resolved_connected_placements.json',OUT/'resolved_residual_placements.json',OUT/'common_entry_repair_r02/resolved_placements.json',OUT/'residual_extensions_r02/resolved_extension_placements.json'];hits=[];walkseams=[];domaincontacts=[];cache={}
 for path in paths:
  pack=load(path)
  for p in pack['placements']:
   rp=p['cache']['path']
   if rp not in cache:
    m=load(ROOT/rp);cache[rp]=roof_rectangles(m,{g['material']for g in m['groups']})[0]
   for q in [b.xform(q,p)for q in cache[rp]]:
    for i in ix.candidates(q):
     ar=geo.intersection_area(q,reserved[i]['polygon_xz_m'])
     if ar>1e-7:hits.append({'native_id':p['id'],'water_owner':reserved[i]['id'],'area_m2':ar})
  for h in pack.get('holdings',[]):
   for q in h.get('polygon_parts_xz_m',[h.get('polygon_xz_m')]):
    for i in ix.candidates(q):
     ar=geo.intersection_area(q,reserved[i]['polygon_xz_m'])
     if ar>1e-7:domaincontacts.append({'holding_id':h['id'],'water_owner':reserved[i]['id'],'area_m2':ar})
  for r in pack.get('external_routes',[])+pack.get('internal_routes',[]):
   for q in r.get('ribbon_polygons_xz_m',r.get('polygon_parts_xz_m',[])):
    for i in ix.candidates(q):
     ar=geo.intersection_area(q,reserved[i]['polygon_xz_m'])
     if ar>1e-7:walkseams.append({'route_id':r['id'],'water_owner':reserved[i]['id'],'kind':reserved[i]['kind'],'area_m2':ar})
 out={'sources':{'water':ref(wp),'precincts':[ref(p)for p in paths]},'native_contacts':hits,'domain_contacts':domaincontacts,'walk_crossings':walkseams,'status':'PASS'if not(hits or domaincontacts or walkseams)else'REVIEW_FINITE_CONTACTS'};(OUT/'late_water_approach_crosspack.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(hits),len(domaincontacts),len(walkseams))
if __name__=='__main__':main()
