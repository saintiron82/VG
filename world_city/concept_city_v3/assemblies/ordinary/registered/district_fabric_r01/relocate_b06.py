"""Shift two fixed native U courts away from the retained upper hill plane."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.bulk_grade_budget import height_part
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc
import types

def shift(ps,dx,dz):return[[[q[0]+dx,q[1]+dz]for q in p]for p in ps]
def run():
 out=SOURCE/'contour_revision_r01/BLOCK_006';g.HERE=out;plan=g.CITY/'registered_integration/r8/coverage_plan';block=next(b for b in g.load(plan/'baseline_blocks.json')['blocks']if b['block_id']=='BLOCK_006');config(block);l=g.load(out/'selected_layout.json');baseline=g.np.load(plan/'baseline_masks.npz');xx=((g.XS-float(baseline['bounds'][0]))).astype(int);zz=((g.ZS-float(baseline['bounds'][1]))).astype(int);ms={k:baseline[k][g.np.ix_(zz,xx)]for k in baseline.files if baseline[k].ndim==2};special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];hard=g.np.logical_or.reduce([ms[k]for k in['spaces','estates','water','wall','retained_native','retained_access']])|g.raster(special,True);domain=g.raster(g.triangulate(block['polygon_xz_m']));allowed=domain&~hard&~ms['road'];index=ta.TriangleIndex(ta.load_scene(),[block['polygon_xz_m']]);records=[]
 for hid in['BLOCK_006:R8_C001','BLOCK_006:R8_C002']:
  h=next(h for h in l['holdings']if h['id']==hid);p=next(p for p in l['placements']if p['holding_id']==hid);floor=h['floor_y_m'];bad=[]
  for r in index.rows:
   for kind,kw in[('cut',dict(low=floor+2.5+1e-7)),('fill',dict(high=floor-2.5-1e-7))]:
    q=height_part(r['polygon_xz_m'],r['plane_y_xz_m'],**kw)
    if q:bad.append(dict(kind=kind,polygon_xz_m=q,source_material=r['material'],source_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],plane_y_xz_m=r['plane_y_xz_m'],classification='holding_margin'))
  badmask=g.raster([q['polygon_xz_m']for q in bad],True);foot=g.raster(p['native_foundation_polygons_xz_m']+h['core_court_polygons_xz_m'],True);roof=g.raster(p['native_roof_polygons_xz_m'],True);others=[p2 for p2 in l['placements']if p2['holding_id']!=hid];otherroof=g.raster([q for pp in others for q in pp['native_roof_polygons_xz_m']],True);othercourt=g.raster([q for hh in l['holdings']if hh['id']!=hid for q in hh['core_court_polygons_xz_m']],True);otherwalk=g.raster([q for pp in others for q in pp['native_walking_obstacles_xz_m']],True);shifts=sorted([(dx,dz)for dx in range(-24,25)for dz in range(-24,25)if dx or dz],key=lambda q:q[0]*q[0]+q[1]*q[1]);chosen=None
  for ix,iz in shifts:
   fm=g.np.roll(foot,(iz,ix),(0,1));rm=g.np.roll(roof,(iz,ix),(0,1))
   if g.np.any(fm&(badmask|~allowed|otherroof|othercourt))or g.np.any(rm&(otherroof|othercourt|~allowed)):continue
   dx,dz=ix*g.GRID,iz*g.GRID;hp=shift([h['holding_polygon_xz_m']],dx,dz)[0];newfoot=shift(p['native_foundation_polygons_xz_m'],dx,dz);newcourt=shift(h['core_court_polygons_xz_m'],dx,dz);own=[q for tri in g.triangulate(block['polygon_xz_m'])if(q:=tc.clean(g.geo.convex_intersection(hp,tri)))];margins=[dict(q,polygon_xz_m=z)for q in bad if(z:=tc.clean(g.geo.convex_intersection(hp,q['polygon_xz_m'])))];own=tc.subtract(own,[q['polygon_xz_m']for q in margins]+[hh['holding_polygon_xz_m']for hh in l['holdings']if hh['id']!=hid])
   if sum(g.geo.polygon_area(x)for q in newfoot+newcourt for x in tc.subtract([q],own))>1e-6:continue
   gate=[h['gate_position_xz_m'][0]+dx,h['gate_position_xz_m'][1]+dz];target=h['public_target_xz_m'];w=h['external_width_m'];free=(domain|ms['road'])&~hard&~otherwalk&~g.raster(shift(p['native_walking_obstacles_xz_m'],dx,dz),True)
   for hh in l['holdings']:
    if hh['id']!=hid:free&=~g.raster([hh['holding_polygon_xz_m']],True)
   clear=g.ndimage.distance_transform_edt(free)*g.GRID>=w/2+.3;start=g.nearest(clear,gate,3);end=g.nearest(clear,target,2.5);goals=g.np.zeros(g.SHAPE,bool)
   if end:goals[end]=True
   line=g.astar(clear,start,goals)if start and end else None
   if not line:continue
   line=[gate]+line+[target];rp=g.ribbons(line,w);obstacles=[q for pp in others for q in pp['native_walking_obstacles_xz_m']]+shift(p['native_walking_obstacles_xz_m'],dx,dz)
   if any(g.geo.intersection_area(q,rr)>1e-6 for q in rp for rr in obstacles):continue
   length=sum(g.math.dist(a,b)for a,b in zip(line,line[1:]));grade=abs(floor-h['public_target_evidence']['y_m'])/max(.1,length-w)
   if grade>.105:continue
   chosen=(dx,dz,hp,newcourt,own,margins,gate,line,rp,grade);break
  if not chosen:records.append(dict(id=hid,status='NO_NATIVE_SAFE_SHIFT_WITHIN_12M'));print('NO_SHIFT',hid,flush=True);continue
  dx,dz,hp,court,own,margins,gate,line,rp,grade=chosen;p['position_m'][0]+=dx;p['position_m'][2]+=dz
  for field in['native_foundation_polygons_xz_m','native_walking_obstacles_xz_m','native_roof_polygons_xz_m']:p[field]=shift(p[field],dx,dz)
  for d in l['actual_doors']:
   if d['holding_id']!=hid:continue
   d['actual_door_xyz_m'][0]+=dx;d['actual_door_xyz_m'][2]+=dz
   for field in['threshold_lip_xz_m']:d[field]=[d[field][0]+dx,d[field][1]+dz]
  h.update(holding_polygon_xz_m=hp,core_court_polygons_xz_m=court,ground_owner_polygons_xz_m=own,nonwalking_slope_verges=margins,gate_position_xz_m=gate,external_route=line,external_route_polygons_xz_m=rp,placement_adjustment=dict(translation_xz_m=[dx,dz],reason='Move actual native footing/core court away from retained upper hill plane; fixed dimensions and unit scale preserved.',minimum_centerline_grade=grade));records.append(dict(id=hid,status='NATIVE_SAFE_SHIFT_CANDIDATE',translation_xz_m=[dx,dz],new_ground_owner_area_m2=sum(g.geo.polygon_area(q)for q in own)));print('SHIFT',hid,dx,dz,flush=True)
 # Recompute every ordinary retirement against actual finite owners and full paths.
 rows=[r for r in g.load(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json')['rows']if r['block_id']=='BLOCK_006'];projection={p['id']:p for p in g.load(plan/'native_projection.json')['instances']}
 for h in l['holdings']:
  owner=h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])+h['external_route_polygons_xz_m'];h['retired_source_ids']=[r['source_id']for r in rows if any(g.geo.intersection_area(r['actual_native_outer_footprint_xz_m'],q)>1e-7 for q in owner)]
 retired=sorted({i for h in l['holdings']for i in h['retired_source_ids']});removed=sum(projection[i]['roof_area_m2']for i in retired);l.update(retired_source_ids=retired,retirement_records=[r for r in rows if r['source_id']in retired],retired_foundation_proxy_ids=[i+':owned_foundation'for i in retired]);l['summary'].update(retired_ordinary_instances=len(retired),retired_ordinary_roof_m2=removed,after_ordinary_roof_m2=l['summary']['before_ordinary_roof_m2']-removed+l['summary']['native_roof_m2'],net_ordinary_roof_gain_m2=l['summary']['native_roof_m2']-removed);g.write(out/'selected_layout.json',l);g.write(out/'native_shift_report.json',dict(rows=records,new_compiles=0))
 for name in['access','furnish']:
  src=(SOURCE/(name+'.py')).read_text()
  if name=='furnish':src=src.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
  m=types.ModuleType(__package__+'.shift_'+name);m.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),m.__dict__);m.run()
 proposal=g.load(out/'ground_proposal.json');proposal.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),retirement_records=l['retirement_records'],retired_foundation_proxy_ids=l['retired_foundation_proxy_ids'],native_shift_report=g.ref(out/'native_shift_report.json'))
 for cl in proposal['clusters']:
  hh=[h for h in l['holdings']if h['id']in cl['holding_ids']];cl['ground_owner_polygons_xz_m']=[q for h in hh for q in h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])];cl['entry_routes']=[dict(id=h['id']+':ENTRY',width_m=h['external_width_m'],polyline_xz_m=h['external_route'],polygons_xz_m=h['external_route_polygons_xz_m'],public_road_id=h['public_road_id'],public_target=h['public_target_evidence'])for h in hh]
 g.write(out/'ground_proposal.json',proposal)
if __name__=='__main__':run()
