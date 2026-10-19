"""Native common replacement, finite patch and full-width static route proof."""
from pathlib import Path
import sys,json,math,time,collections
OUT=Path(__file__).resolve().parent;RES=OUT.parent;BASE=RES.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent;RES=OUT.parent

def main():
 t=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');patch=load(OUT/'native_ground_candidate_patch.json');proof=load(OUT/'native_ground_candidate_audit.json');scene=terrain.load_scene();original=scene['surfaces'];edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};assert len(edits)==len(patch['surface_edits'])
 for (mat,i),e in edits.items():assert terrain.canonical_sha(original[mat][i*3:i*3+3])==e['source_triangle_sha256']
 for mat,vs in list(scene['surfaces'].items()):
  if not any(m==mat for m,i in edits):continue
  scene['surfaces'][mat]=[v for i in range(len(vs)//3)for tri in edits.get((mat,i),{'replacement_triangles_xyz_m':[vs[i*3:i*3+3]]})['replacement_triangles_xyz_m']for v in tri]
 for mat,vs in patch['appended_surfaces'].items():scene['surfaces'].setdefault(mat,[]).extend(vs)
 ext=load(RES/'common_entry_surface_audit.json')['row'];pts=ext['polyline_xz_m'];polys=b.ribbon(pts,2)+[b.rect(pts[1][0]-1,pts[1][1]-1,pts[1][0]+1,pts[1][1]+1)];tops=proof['retained_base_upward_faces']+proof['new_native_upward_faces'];vs=[v for r in tops for tri in terrain.fan_upward([[q[0],r['plane_y_xz_m'][2],q[1]]for q in r['polygon_xz_m']])for v in tri];# Native triangle-skin unions can expose lower cavity ledges below the
 # highest occupied column. Walking support is the exact upper envelope, not
 # every upward face projected on top of one another.
 upper=[];ui=geo._SpatialIndex(8)
 for r in sorted(tops,key=lambda r:-r['plane_y_xz_m'][2]):
  for q in terrain.common.subtract([r['polygon_xz_m']],[upper[i]['polygon_xz_m']for i in ui.candidates(r['polygon_xz_m'])]):
   if geo.polygon_area(q)>1e-8:ui.add(len(upper),q);upper.append(dict(r,polygon_xz_m=q))
 nativevs=[v for r in upper for tri in terrain.fan_upward([[q[0],r['plane_y_xz_m'][2],q[1]]for q in r['polygon_xz_m']])for v in tri]
 class Support:
  def __init__(self):self.ground=terrain.TriangleIndex(scene,polys);self.native=terrain.TriangleIndex({'surfaces':{'actual_replacement_native_walk':nativevs}},polys)
  def covering(self,p):
   rows=list(self.ground.covering(p));claimed=[r['intersection_polygon_xz_m']for r in rows];yield from rows
   for r in self.native.covering(p):
    for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
     if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
 index=Support();checks=[terrain.audit_polygon(index,p,None)for p in polys];seams=[]
 for c in checks:
  for r in c['source_pieces']:
   for q in r['polygon_xz_m']:
    ys=[terrain.common.height(rr['plane_y_xz_m'],q)for rr in c['source_pieces']if geo.point_in_convex_polygon(q,rr['polygon_xz_m'],1e-7)]
    if ys and max(ys)-min(ys)>.15+1e-7:seams.append({'point_xz_m':q,'jump_m':max(ys)-min(ys)})
 side=SideIndex(scene,polys).audit([{'id':f'COMMON_FINE_ROUTE:{i}:{j}','polygon_xz_m':r['polygon_xz_m'],'plane_y_xz_m':r['plane_y_xz_m']}for i,c in enumerate(checks)for j,r in enumerate(c['source_pieces'])]);projection=load(BASE/'actual_native_projection.json');contacts=[]
 for p in projection['instances']:
  if p['id']=='REGISTERED_LANDSCAPE:SITE_COMMON':continue
  for r in p['native_parts_xz_m']:
   for q in polys:
    ar=geo.intersection_area(q,r)
    if ar>1e-7:contacts.append({'native_id':p['id'],'area_m2':ar})
 regen=[]
 for a in pack['assets']:
  s=load(ROOT/a['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':a['pitch_m']},max_candidate_cells=600000,max_output_cells=200000);m=render_data.make_render_data(c);regen.append({'asset_id':a['id'],'common_valid':c['valid'],'fresh_cache_equal':core.digest(m)==core.digest(load(ROOT/a['cache']['path']))})
 # The public repair must meet the sampled native terminal, not silently use
 # the older analytic source endpoint as if it were the voxel top.
 edge=ext['external_surface']['public_lane_endpoint']['seam_xz_m'];terminal=[]
 for r in proof['new_native_upward_faces']:
  # Exact native top patches within the final 1.5 m segment of the source route.
  q=b.ribbon([pts[-2],pts[-1]],2)[0];ar=geo.intersection_area(q,r['polygon_xz_m'])
  if ar>1e-8 and min(math.dist(v,pts[-1])for v in r['polygon_xz_m'])<2:terminal.append(r)
 results={'full_width_surface_pass':all(c['passes_existing_surface']for c in checks),'no_surface_jump_over_0p15':not seams,'no_retained_bank_contacts':not side['contacts'],'no_other_native_contacts':not contacts,'new_bearings_supported':not proof['unsupported'],'retaining_perimeter_closed':not proof['side_closure']['unknown_exterior_segments'],'fresh_common_regeneration':all(r['common_valid']and r['fresh_cache_equal']for r in regen)}
 report={'status':'PASS_STATIC_CONTROLLER_PENDING'if all(results.values())else'HELD_STATIC_FAILURE','checks':results,'full_width_m':2,'source_route_width_m':3,'polyline_xz_m':pts,'ribbon_polygons_xz_m':polys,'actual_surface_checks':checks,'surface_jump_failures':seams,'bank_contacts':side['contacts'],'other_native_contacts':contacts,'native_terminal_top_pieces':terminal,'source_public_profile':ext['external_surface']['public_lane_endpoint'],'independent_regeneration':regen,'maximum_native_pitch_step_m':.125,'runtime_replay':False,'seconds':time.monotonic()-t};(OUT/'static_entry_tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],results,'gap',sum(c['missing_area_m2']for c in checks),'jumps',len(seams),'banks',len(side['contacts']))
if __name__=='__main__':main()
