"""Shared actual-scene index and full-width entry screening for the contour batch."""
import json,math,time,collections
from .. import author as a,native_clearance,regeneration
from ..audit_retired_boundaries import interval
HERE=a.HERE/'remaining_level_r01'
BULK=HERE/'bulk_sources.json'

def write(name,data):
 p=HERE/name
 if p.exists():raise ValueError('Preserve '+str(p))
 p.write_text(json.dumps(data,separators=(',',':'))+'\n')

def run():
 start_time=time.monotonic();bulk=json.loads(BULK.read_bytes())
 assert a.sha(BULK)=='56bcb1d718713ff70e3c34bc96a3022562f05c279a413c44033f1d3341d02c4f'
 plan=json.loads(a.PLAN_PATH.read_bytes());roads={r['id']:r for r in plan['roads']};districts=[];windows=[]
 for d in bulk['districts']:
  hand=native_clearance.require_ref(d['terrain']);proposal=native_clearance.require_ref(d['ground_proposal']);layout=native_clearance.require_ref(proposal['layout']);pack=native_clearance.require_ref(d['pack']);districts.append((d,hand,proposal,layout,pack))
  for h in layout['holdings']:windows.append(h['holding_polygon_xz_m']);windows.extend(h['external_route_polygons_xz_m'])
 scene=a.load_scene();index=a.TriangleIndex(scene,windows);rows=[];fields=[];budget=[]
 for district,hand,proposal,layout,pack in districts:
  for h in layout['holdings']:
   id=h['id'];floor=h['floor_y_m'];gate=h['gate_position_xz_m'];target=h['public_target_xz_m'];width=h['external_width_m'];road=roads[h['public_road_id']];choices=[]
   for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
    L=math.dist(u,v);t=max(0.,min(1.,sum((target[k]-u[k])*(v[k]-u[k])for k in(0,1))/L**2));q=[u[k]+t*(v[k]-u[k])for k in(0,1)];choices.append((math.dist(q,target),j,q,u,v,L))
   _,segment,center,u,v,L=min(choices);tg=[(v[k]-u[k])/L for k in(0,1)];normal=[-tg[1],tg[0]];side=1 if sum((gate[k]-center[k])*normal[k]for k in(0,1))>=0 else-1
   end=[[center[k]+side*normal[k]*road['width_m']/2+s*tg[k]*width/2 for k in(0,1)]for s in(-1,1)];dist=math.dist(gate,center);direction=[(center[k]-gate[k])/dist for k in(0,1)];nn=[-direction[1],direction[0]];first=[[gate[k]+s*nn[k]*width/2 for k in(0,1)]for s in(-1,1)]
   if math.dist(first[0],end[0])+math.dist(first[1],end[1])>math.dist(first[0],end[1])+math.dist(first[1],end[0]):end=end[::-1]
   poly=a.common.clean([first[0],first[1],end[1],end[0]]);spans=[]
   for k in index.index.candidates(end):
    r=index.rows[k]
    if r['material']not in('road','alley'):continue
    s=interval(*end,r['polygon_xz_m'])
    if s:spans.append((s,r))
   knots=sorted({0.,1.}|{x for span,_ in spans for x in span});knots=[x for j,x in enumerate(knots)if j==0 or x-knots[j-1]>1e-8];ys=[];errors=[]
   for t in knots:
    p=[end[0][k]+t*(end[1][k]-end[0][k])for k in(0,1)];votes=[a.common.height(r['plane_y_xz_m'],p)for span,r in spans if span[0]-1e-8<=t<=span[1]+1e-8]
    if not votes:errors.append(dict(kind='missing_public_top',point_xz_m=p));ys.append(None)
    elif max(votes)-min(votes)>1e-6:errors.append(dict(kind='discontinuous_public_top',point_xz_m=p,heights_m=votes));ys.append(None)
    else:ys.append(votes[0])
   for lo,hi in zip(knots,knots[1:]):
    if not any(s[0]-1e-9<=(lo+hi)/2<=s[1]+1e-9 for s,_ in spans):errors.append(dict(kind='missing_public_interval',parameters=[lo,hi]))
   sourcegrade=max([abs(y1-y0)/((b-a0)*math.dist(*end))for a0,b,y0,y1 in zip(knots,knots[1:],ys,ys[1:])if y0 is not None and y1 is not None]+[0]);solution=None
   if not errors and sourcegrade<=.12+1e-8 and poly and a.geo.is_convex_polygon(poly):
    pts=[];targets=[];fixed={};n=len(knots);steps=max(4,math.ceil(dist/1.5))
    for row in range(steps+1):
     t=row/steps
     for k,s in enumerate(knots):
      pts.append([(1-t)*(first[0][c]+s*(first[1][c]-first[0][c]))+t*(end[0][c]+s*(end[1][c]-end[0][c]))for c in(0,1)]);targets.append((1-t)*floor+t*ys[k])
      if row==0:fixed[len(pts)-1]=floor
      if row==steps:fixed[len(pts)-1]=ys[k]
    tris=[]
    for row in range(steps):
     for k in range(n-1):i=row*n+k;tris.extend([[i,i+1,i+n+1],[i,i+n+1,i+n]])
    try:solution=regeneration.solve_field(pts,tris,fixed,targets)
    except ValueError as exc:solution=dict(status='TOPOLOGY_HOLD',message=str(exc))
   status='FINITE_PROFILE_MATH_CANDIDATE'if solution and solution.get('status')=='PASSED_FINITE_TRIANGLE_GRADE'else'PUBLIC_INTERFACE_REPAIR_REQUIRED'
   record=dict(id=id,block_id=district['block_id'],floor_y_m=floor,public_road_id=road['id'],public_segment_index=segment,width_m=width,source_gate_xz_m=gate,source_public_target_xz_m=target,canonical_public_center_xz_m=center,private_start_edge_xz_m=first,public_edge_xz_m=end,polygon_xz_m=poly,public_seam_knots_xyz_m=[[end[0][0]+t*(end[1][0]-end[0][0]),y,end[0][1]+t*(end[1][1]-end[0][1])]for t,y in zip(knots,ys)],source_crossfall_grade=sourcegrade,source_errors=errors,source_public_faces=[dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],plane_y_xz_m=r['plane_y_xz_m'])for _,r in spans],profile_status=solution.get('status')if solution else None,status=status)
   rows.append(record)
   if solution:fields.append(dict(id=id,solution=solution))
   parcel=next(p for p in hand['parcels']if p['id']==id);core=parcel['footing_polygons_xz_m']+h['core_court_polygons_xz_m'];cut=fill=0.
   for p in core:
    for r in index.covering(p):
     values=[a.common.height(r['plane_y_xz_m'],q)-floor for q in r['intersection_polygon_xz_m']];cut=max(cut,*values);fill=max(fill,*[-v for v in values])
   budget.append(dict(id=id,block_id=district['block_id'],floor_y_m=floor,maximum_required_core_cut_m=cut,maximum_required_core_fill_m=fill,within_design_screen=max(cut,fill)<=2.5000001))
  print(district['block_id'],collections.Counter(r['status']for r in rows if r['block_id']==district['block_id']),flush=True)
 summary=dict(holdings=len(rows),profile_math_candidates=sum(r['status']=='FINITE_PROFILE_MATH_CANDIDATE'for r in rows),public_interface_holds=sum(r['status']!='FINITE_PROFILE_MATH_CANDIDATE'for r in rows),core_design_holds=sum(not r['within_design_screen']for r in budget),elapsed_s=time.monotonic()-start_time)
 write('entry_screen.json',dict(base_scene_sha256=a.SCENE_SHA256,source_bulk=dict(path=str(BULK.relative_to(a.ROOT)),sha256=a.sha(BULK)),entries=rows,summary=summary,scope='Mathematical full-width profiles only. Exact native/other-owner clearance, finite ownership composition and runtime remain pending.',activation=False));write('profile_math_candidates.json',dict(profiles=fields,activation=False));write('required_core_budget.json',dict(rows=budget,summary=summary,activation=False));print(summary,flush=True)
if __name__=='__main__':run()
