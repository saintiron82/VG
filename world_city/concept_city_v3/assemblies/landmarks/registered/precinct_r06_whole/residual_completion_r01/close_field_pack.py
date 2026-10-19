"""Close residual fields against sealed ownership, routes and later water packs."""
from pathlib import Path
import sys,json,copy,collections,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def parts(u):return u.get('polygon_parts_xz_m',[u.get('polygon_xz_m')])
def routeparts(r):return r.get('ribbon_polygons_xz_m',r.get('polygon_parts_xz_m',[]))
def main():
 t=time.monotonic();ready=load(BASE/'resolved_connected_placements.json');pack=load(OUT/'resolved_field_placements.json');candidate=load(BASE/'resolved_placements.json');train=next(h for h in candidate['holdings']if h['id']=='R06_SITE_TRAIN_01');tid=train['id'];train=copy.deepcopy(train);train['polygon_parts_xz_m']=parts(train);train['public_entry_proof']=ref(OUT/'training_walk_tests.json');train['runtime_ready']=False;pack['holdings'].append(train)
 for k in('placements','actual_bearing_footprints','internal_routes','owned_floors'):pack[k]+= [r for r in candidate[k]if r.get('holding_id')==tid]
 aid={a['id']:a for a in pack['assets']};aid.update({a['id']:a for a in candidate['assets']if a['id']in {p['asset_key']for p in pack['placements']}});pack['assets']=list(aid.values());ta=load(OUT/'training_entry_audit.json');pack['external_routes']=[dict(id=f['id']+':entry',holding_id=f['id'],width_m=2,floor_y_m=f['floor_y_m'],polyline_xz_m=[f['entry']['inside_point_xz_m'],f['entry']['ready_route_point_xz_m']],ribbon_polygons_xz_m=f['entry']['ribbon_polygons_xz_m'],joins_verified_route_id=f['entry']['ready_route_id'])for f in pack['holdings']if 'entry'in f];pack['external_routes'].append({'id':'RETAINED_TRAINING_ENTRY_R01','holding_id':tid,'width_m':2,'polyline_xz_m':ta['proposed_spur_polyline_xz_m'],'ribbon_polygons_xz_m':ta['polygon_parts_xz_m'],'source':ref(OUT/'training_walk_tests.json'),'retained_native_stair_id':'TRAIN:r09:fine','runtime_ready':False})
 priority=[]
 for h in ready['holdings']:priority += [{'id':h['id'],'polygon_xz_m':p}for p in parts(h)]
 for r in ready['external_routes']:priority += [{'id':r['id'],'polygon_xz_m':p}for p in routeparts(r)]
 pi=geo._SpatialIndex(16)
 for i,r in enumerate(priority):pi.add(i,r['polygon_xz_m'])
 clipped=[];scene=terrain.load_scene();degenerate=[]
 for f in pack['holdings']:
  before=f['area_m2'];out=[]
  if 'source_pieces'in f:
   cleanpieces=[]
   for r in f['source_pieces']:
    vs=scene['surfaces'][r['material']][r['triangle_index']*3:r['triangle_index']*3+3];area=geo.polygon_area([[v[0],v[2]]for v in vs])
    if area<=1e-8:degenerate.append({'holding_id':f['id'],'material':r['material'],'triangle_index':r['triangle_index'],'source_area_m2':area,'discarded_unreliable_clip_area_m2':geo.polygon_area(r['polygon_xz_m'])})
    else:cleanpieces.append(r)
   f['source_pieces']=cleanpieces;f['polygon_parts_xz_m']=[r['polygon_xz_m']for r in cleanpieces]
  for p in parts(f):out+=terrain.common.subtract([p],[priority[i]['polygon_xz_m']for i in pi.candidates(p)])
  f['polygon_parts_xz_m']=out;f['area_m2']=sum(geo.polygon_area(p)for p in out);f['exact_area_m2']=f['area_m2'];clipped.append({'holding_id':f['id'],'before_area_m2':before,'final_area_m2':f['area_m2'],'sealed_priority_overlap_removed_m2':before-f['area_m2']})
 # All later registered native and functional ownership is explicit here.
 protected=[];cache={}
 def native_rows(src,label):
  for p in src['placements']:
   rp=p['cache']['path']
   if rp not in cache:
    m=load(ROOT/rp);cache[rp]=roof_rectangles(m,{g['material']for g in m['groups']})[0]
   protected.extend({'id':p['id'],'kind':label,'polygon_xz_m':b.xform(q,p)}for q in cache[rp])
 native_rows(ready,'ready21_native');phasepath=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json';phase=load(phasepath);native_rows(phase,'phase02_native')
 for r in ready['external_routes']+ready['internal_routes']:protected += [{'id':r['id'],'kind':'ready21_walk','polygon_xz_m':p}for p in routeparts(r)]
 for r in phase['internal_routes']:protected += [{'id':r.get('id',r.get('holding_id')),'kind':'phase02_walk','polygon_xz_m':p}for p in routeparts(r)]
 for f in load(CITY/'assemblies/waterworks/registered_services_r01/locations.json')['drawhouses']:
  protected.append({'id':f['id'],'kind':'water_native','polygon_xz_m':f['footprint_xz_m']});protected += [{'id':f['id'],'kind':'water_walk','polygon_xz_m':p}for p in f['walk_polygons_xz_m']]
 mill=load(CITY/'assemblies/waterworks/registered_mill_r01/interface_contract.json');protected.append({'id':'mill','kind':'mill_native','polygon_xz_m':mill['site']['body_polygon_xz_m']});protected += [{'id':'mill','kind':'mill_walk','polygon_xz_m':p}for p in mill['site']['walk_polygons_xz_m']];protected.append({'id':'mill','kind':'mill_navigation','polygon_xz_m':mill['navigation_polygon_xz_m']})
 crossings=load(CITY/'assemblies/waterworks/registered_water_completion_r01/crossing_interfaces.json')
 for c in crossings['crossings']:
  for k,v in c.items():
   if 'polygon' in k and isinstance(v,list) and v and isinstance(v[0],list) and isinstance(v[0][0],(int,float)):protected.append({'id':c.get('id'),'kind':'water_crossing:'+k,'polygon_xz_m':v})
 ix=geo._SpatialIndex(16)
 for i,r in enumerate(protected):ix.add(i,r['polygon_xz_m'])
 hits=[];contain=[];nativepolys=[]
 for p in pack['placements']:
  rp=p['cache']['path']
  if rp not in cache:
   m=load(ROOT/rp);cache[rp]=roof_rectangles(m,{g['material']for g in m['groups']})[0]
  h=next(h for h in pack['holdings']if h['id']==p['holding_id']);gi=geo._SpatialIndex(8)
  for i,q in enumerate(parts(h)):gi.add(i,q)
  for q in [b.xform(q,p)for q in cache[rp]]:
   nativepolys.append({'id':p['id'],'holding_id':p['holding_id'],'polygon_xz_m':q});inside=sum(geo.intersection_area(q,parts(h)[i])for i in gi.candidates(q));err=geo.polygon_area(q)-inside
   if err>1e-6:contain.append({'id':p['id'],'outside_domain_m2':err})
   for i in ix.candidates(q):
    r=protected[i];ar=geo.intersection_area(q,r['polygon_xz_m'])
    if ar>1e-7:hits.append({'native_id':p['id'],'other_id':r['id'],'kind':r['kind'],'area_m2':ar})
 routehits=[];shared=[]
 for r in pack['external_routes']+pack['internal_routes']:
  for q in routeparts(r):
   for i in ix.candidates(q):
    o=protected[i];ar=geo.intersection_area(q,o['polygon_xz_m'])
    if ar>1e-7:
     row={'route_id':r['id'],'other_id':o['id'],'kind':o['kind'],'area_m2':ar}
     (shared if 'walk'in o['kind']else routehits).append(row)
 bad={p['holding_id']for p in pack['placements']if any(x['native_id']==p['id']for x in hits)or any(x['id']==p['id']for x in contain)}
 if bad:raise AssertionError(('native_collision_or_clipped',bad,hits[:5],contain[:5]))
 if routehits:raise AssertionError(('route_contacts',routehits[:5]))
 pack['summary']={'functional_fields':len(pack['holdings'])-1,'training_tack_holdings':1,'exact_domain_area_m2':sum(f['area_m2']for f in pack['holdings']),'native_placements':len(pack['placements']),'native_bearing_pieces':len(pack['actual_bearing_footprints']),'internal_routes':len(pack['internal_routes']),'external_routes':len(pack['external_routes'])};pack['sources']['ready_priority_geometry']=ref(BASE/'connected_surface_patch.json');pack['sources']['resolved_fields']=ref(OUT/'resolved_field_placements.json');pack['sources']['training_native_candidate']=ref(BASE/'resolved_placements.json');pack['status']='RESOLVED_RESIDUAL_CONNECTED_FIELDS_AND_TRAINING_SOURCE_NOT_APPLIED';pack['activation']=False
 report={'status':'PASS','sources':{'ready21':ref(BASE/'resolved_connected_placements.json'),'phase02':ref(phasepath),'services':ref(CITY/'assemblies/waterworks/registered_services_r01/locations.json'),'mill':ref(CITY/'assemblies/waterworks/registered_mill_r01/interface_contract.json'),'crossings':ref(CITY/'assemblies/waterworks/registered_water_completion_r01/crossing_interfaces.json')},'domain_clipping':clipped,'preserved_degenerate_source_triangles':degenerate,'native_contacts':hits,'native_outside_domain':contain,'route_native_contacts':routehits,'intentional_shared_walking_regions':shared,'protected_polygons':len(protected),'summary':pack['summary'],'seconds':time.monotonic()-t}
 for name,data in [('resolved_residual_placements.json',pack),('residual_crosspack_tests.json',report),('residual_native_projection.json',nativepolys)]: (OUT/name).write_text(json.dumps(data,indent=2)+'\n')
 print(report['summary'],'shared_walk',len(shared),'removed_area',sum(r['sealed_priority_overlap_removed_m2']for r in clipped),'seconds',report['seconds'])
if __name__=='__main__':main()
