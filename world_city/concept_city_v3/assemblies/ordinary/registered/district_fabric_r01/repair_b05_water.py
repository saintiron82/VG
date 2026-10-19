"""Dry-side correction for one frozen contour route; no scene or frozen-pack mutation."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import PublicSamples
from .finalize_coherent import overlap

def run():
 root=SOURCE/'contour_revision_r01';lp=root/'BLOCK_005/selected_layout.json';l=g.load(lp);scene=g.load(g.R7);h=next(x for x in l['holdings']if x['id']=='BLOCK_005:R8_C006');manifest=g.load(SOURCE/'effective_city_manifest_r01.json');retired=set(manifest['replaced_placement_ids']);proj=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];native=[q for r in proj if r['id']not in retired for q in r['native_owner_parts_xz_m']];newnative=[]
 for d in manifest['districts']:
  pack=g.load(g.ROOT/d['pack']['path']);ll=g.load(g.ROOT/pack['layout']['path']);newnative += [q for p in ll['placements']for q in p['native_walking_obstacles_xz_m']];cp=(g.ROOT/pack['layout']['path']).parent/'court_equipment.json'
  if cp.exists():newnative += [q for p in g.load(cp)['placements']for q in p['native_walking_obstacles_xz_m']]
 vs=scene['surfaces']['water'];water=[[[v[0],v[2]]for v in vs[i:i+3]]for i in range(0,len(vs),3)];special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];sets={'water':water,'retained_native':native,'new_native_and_court_equipment':newnative,'special_reservations':special};indexes={}
 for k,ps in sets.items():
  idx=g.geo._SpatialIndex(16)
  for i,p in enumerate(ps):idx.add(i,p)
  indexes[k]=idx
 def screen(polys):return {k:sum(g.geo.intersection_area(p,sets[k][j])for p in polys for j in indexes[k].candidates(p))for k in sets}
 orig=h['external_route'];pub=PublicSamples(scene);found=None;trials=[]
 for shift in [.1,.25,.5,.75,1.0]:
  line=g.copy.deepcopy(orig);line[11][0]+=shift;line[12][0]+=shift
  for dx,dz in [(-.75,0),(-1,0),(-.5,.5),(-1,.5),(-1,1),(-1.5,0),(-1.5,.5),(-1.5,1),(-2,0),(-2,1)]:
   ll=g.copy.deepcopy(line);ll[-1]=[orig[-1][0]+dx,orig[-1][1]+dz];e=pub.at(ll[-1]);polys=g.ribbons(ll,h['external_width_m']);checks=screen(polys);trials.append(dict(shift=shift,terminal_offset=[dx,dz],public=bool(e),overlap_m2=checks))
   if e and all(v<1e-7 for v in checks.values()):found=(ll,polys,checks,e);break
  if found:break
 if not found:g.write(root/'b05_dryside_search_diagnostic.json',trials);print('NO_CLEAR_ROUTE',trials);return
 line,polys,checks,e=found;out=dict(schema='riverstone.district_fabric.contour_route_addendum.v1',base_scene=g.ref(g.R7),effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),source_layout=g.ref(lp),source_pack=g.ref(root/'BLOCK_005/resolved_placements.json'),holding_id=h['id'],supersedes='Only this holding external_route and external_route_polygons_xz_m; all native, court, internal-door routes and frozen source bytes remain unchanged.',superseded_route=dict(polyline_xz_m=orig,polygons_xz_m=h['external_route_polygons_xz_m'],width_m=h['external_width_m'],public_target_evidence=h['public_target_evidence']),replacement_route=dict(id=h['id']+':EXTERNAL',holding_id=h['id'],width_m=h['external_width_m'],polyline_xz_m=line,polygons_xz_m=polys,public_road_id=h['public_road_id'],public_target_xz_m=line[-1],public_target_evidence=e,floor_y_m=h['floor_y_m'],status='Dry-side projected-clearance proof only; shared profile and full transverse public seam require R17/R18.'),changed_knots=[dict(index=i,before=a,after=b)for i,(a,b)in enumerate(zip(orig,line))if a!=b],exact_projected_overlap_m2=checks,passed=all(v<1e-7 for v in checks.values()),new_retirements=[],terrain_fill_permitted_in_water=False);g.write(root/'b05_dryside_addendum_r01.json',out);print(out['changed_knots']);print(checks);print(g.ref(root/'b05_dryside_addendum_r01.json'))
if __name__=='__main__':run()
