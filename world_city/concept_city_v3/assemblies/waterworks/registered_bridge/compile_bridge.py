"""Hash-bound rigid common assembly union. No core/mesher edits or cell repairs."""
from __future__ import annotations
import argparse,copy,hashlib,itertools,json,math,time,resource
from pathlib import Path
from voxel_character.common import core,coordinate_planes,render_data
from world_city.runtime_city.parts.author import Source,extrusion
from world_city.runtime_city.checks import placement as geo
from .author import HERE,ROOT,PLAN,TERRAIN,Axis,sha,ref,write,bounds,overlaps,cambered_height_at,world_point,unit,sub,strip

PITCH=.25;CANDIDATE_CAP=3_000_000;OUTPUT_CAP=900_000
CANDIDATE=HERE/'candidate.json';SEALED='36b99b2be9f0f6be940a4f1acd64100ed37d088b6c0fad1d23e720cedf845be1'

def transform_inverse(t):
 b=core.transpose(t['basis']);return {'basis':b,'translation':[-sum(b[i][j]*t['translation'][j] for j in range(3)) for i in range(3)]}
def interp(profile,x):
 pts=profile
 if x<=pts[0][0]:return pts[0][1]
 if x>=pts[-1][0]:return pts[-1][1]
 lo,hi=0,len(pts)-1
 while hi-lo>1:
  mid=(lo+hi)//2
  if pts[mid][0]<=x:lo=mid
  else:hi=mid
 a,b=pts[lo],pts[hi];return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
def edge_cone(q,a,b,ha,hb,grade=.1,upper=False):
 v=[b[i]-a[i] for i in (0,1)];L=math.hypot(*v);u=sum((q[i]-a[i])*v[i] for i in (0,1))/L;d=abs(v[0]*(q[1]-a[1])-v[1]*(q[0]-a[0]))/L;k=(hb-ha)/L
 sign=-1 if upper else 1;ss=max(0,min(L,u+sign*k*d/math.sqrt(max(1e-12,grade*grade-k*k))))
 return ha+k*ss+grade*math.hypot(ss-u,d) if upper else ha+k*ss-grade*math.hypot(ss-u,d)

def base_deck_y(overlay,x,z):
 t=overlay['world_to_bridge'];q=core.apply(t,[x,0,z]);base=interp(overlay['profile_x_y_m'],q[0])
 for transition in overlay.get('terminal_transitions',[]):
  o=transition['outer_center_xz_m'];direction=transition['inward_unit_xz'];d=(x-o[0])*direction[0]+(z-o[1])*direction[1]
  if d<=transition['length_m']+1e-7:
   terrain=__import__('world_city.concept_city_v3.registered_topography.author',fromlist=['road_height_at'])
   if d<0:return terrain.road_height_at('MAIN_BRIDGE',x,z)
   edges=transition['inner_edge_segments']+transition['outer_edge_segments'];lo=max(edge_cone([x,z],e['a_xz_m'],e['b_xz_m'],e['a_y_m'],e['b_y_m']) for e in edges);hi=min(edge_cone([x,z],e['a_xz_m'],e['b_xz_m'],e['a_y_m'],e['b_y_m'],upper=True) for e in edges);return (lo+hi)/2
 return base
def distance_to_polygon(p,poly):
 if geo.point_in_convex_polygon(p,poly,1e-9):return 0.
 best=1e99
 for a,b in zip(poly,poly[1:]+poly[:1]):
  v=[b[k]-a[k] for k in (0,1)];n=sum(t*t for t in v)
  f=max(0,min(1,sum((p[k]-a[k])*v[k] for k in (0,1))/n)) if n>1e-20 else 0
  best=min(best,math.hypot(*(p[k]-a[k]-f*v[k] for k in (0,1))))
 return best

def deck_y(overlay,x,z):
 base=base_deck_y(overlay,x,z);j=overlay.get('junction_uplift')
 if not j or not any(geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-8) for r in j['regions']):return base
 distance=min(distance_to_polygon([x,z],p) for p in j['tie_polygons_xz_m'])
 return max(base,j['quay_y_m']-j['grade_bound']*distance)

def triangular_cap(source,ident,points,thickness=.45):
 # One native rigid triangular prism; authored top-plane dimensions, no scaling.
 a,b,c=points;u=[b[k]-a[k] for k in range(3)];length=math.sqrt(sum(v*v for v in u));u=[v/length for v in u]
 w=[c[k]-a[k] for k in range(3)];n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];length=math.sqrt(sum(v*v for v in n));n=[v/length for v in n]
 if n[1]<0:n=[-v for v in n]
 v=[n[1]*u[2]-n[2]*u[1],n[2]*u[0]-n[0]*u[2],n[0]*u[1]-n[1]*u[0]]
 poly=[[sum((q[k]-a[k])*u[k] for k in range(3)),sum((q[k]-a[k])*v[k] for k in range(3))] for q in points]
 source.op(ident,extrusion(poly,-thickness,0),'stone',component='port_junction_cap',transform={'basis':[[u[k],v[k],n[k]] for k in range(3)],'translation':a})
 return math.hypot(n[0],n[2])/n[1]

def trim_union(regions):
 result=[]
 for item in regions:
  parts=[item['polygon_xz_m']]
  for old in result:
   parts=[q for p in parts for q in (geo.convex_difference(p,old['polygon_xz_m']) if overlaps(bounds(p),bounds(old['polygon_xz_m'])) else [p]) if geo.polygon_area(q)>1e-8]
  for i,p in enumerate(parts):result.append({**item,'id':item['id']+f':union:{i}','polygon_xz_m':p,'area_m2':geo.polygon_area(p)})
 return result

def prepare():
 assert sha(CANDIDATE)==SEALED,'sealed candidate changed'
 p=json.loads(CANDIDATE.read_text());plan=json.loads(PLAN.read_text());axis=Axis(next(r for r in plan['roads'] if r['id']=='MAIN_BRIDGE'))
 a=p['bays'][0]['endpoints_xz_m'][0];b=p['bays'][-1]['endpoints_xz_m'][1];t=unit(sub(b,a));center=p['bays'][4]['center_xz_m']
 frame={'translation':[center[0],0,center[1]],'basis':[[t[0],0,-t[1]],[0,1,0],[t[1],0,t[0]]]};inv=transform_inverse(frame)
 fixed_s=[0,p['width_reconciliation']['gate_station_m'],p['camber_overlay']['start_station_m'],p['camber_overlay']['end_station_m'],axis.length]
 stations=sorted(set([i*axis.length/math.ceil(axis.length/.25) for i in range(math.ceil(axis.length/.25)+1)]+axis.stations+fixed_s+[p['camber_overlay']['crest_station_m']]))
 raw=[];anchors=[]
 for s in stations:
  q=axis.at(s);x=core.apply(inv,[q[0],0,q[1]])[0];y=cambered_height_at(*q,axis,p['camber_overlay']);raw.append([x,y])
  if s in fixed_s:anchors.append({'source_station_m':s,'world_xz_m':q,'bridge_x_m':x,'finished_y_m':y})
 # A single 10% Lipschitz profile, constrained to fixed gate/bank/axis endpoints.
 capped=[[x,min(y,*(q['finished_y_m']+.1*abs(x-q['bridge_x_m']) for q in anchors))] for x,y in raw]
 profile=[[x,max(v-.1*abs(x-u) for u,v in capped)] for x,_ in raw]
 max_repair=max(abs(y-v) for (_,y),(_,v) in zip(raw,profile))
 owned=trim_union([dict(r,ownership_kind='deck') for r in p['deck_regions']]+[dict(r,ownership_kind='dry_approach') for r in p['approach_regions']])
 overlay={'schema':'riverstone.registered_bridge_continuous_deck.v1','candidate':ref(str(CANDIDATE.relative_to(ROOT))),'source_plan':p['source_plan'],'terrain_author':p['terrain_author'],'bridge_to_world':frame,'world_to_bridge':inv,'profile_x_y_m':profile,'fixed_endpoints':anchors,'regions':owned,'supersedes':'MAIN_BRIDGE road/deck surfaces only within this exact owned polygon union','height_lookup':'compile_bridge.deck_y(overlay,x,z): transform world XZ into bridge frame X, then linearly interpolate the one shared profile.','reason':'Resolve independently reported 17.509 mm oblique-bay source-height seam and two deck/approach ownership overlaps.','maximum_centerline_lipschitz_repair_m':max_repair,'maximum_profile_grade':max(abs(y1-y0)/(x1-x0) for (x0,y0),(x1,y1) in zip(profile,profile[1:])),'max_local_cap_top_lowering_m':.05,'joint_pier_top_lowering_m':.10,'parapet_base_embed_m':.10,'shared_cap_thickness_m':.40,'source_candidate_modified':False}
 # Exact full-width outer ties use a 10% Lipschitz extension from an inner
 # transverse edge, combined with the unchanged terrain field. This keeps
 # both the outer crossfall and inner shared deck datum without endpoint steps.
 overlay['terminal_transitions']=[]
 for name,outer,neighbor,length in [('north',axis.points[0],axis.points[1],8.),('south',axis.points[-1],axis.points[-2],7.)]:
  direction=unit(sub(neighbor,outer));normal=[-direction[1],direction[0]];inside=[outer[i]+direction[i]*length for i in(0,1)];a=[inside[i]-normal[i]*4 for i in(0,1)];b=[inside[i]+normal[i]*4 for i in(0,1)];xa=core.apply(inv,[a[0],0,a[1]])[0];xb=core.apply(inv,[b[0],0,b[1]])[0];ts=[0.,1.]
  if abs(xb-xa)>1e-12:ts+= [(x-xa)/(xb-xa) for x,y in profile if 0<(x-xa)/(xb-xa)<1]
  pts=[[a[i]+f*(b[i]-a[i]) for i in(0,1)] for f in sorted(ts)];segments=[]
  for c,d in zip(pts,pts[1:]):segments.append({'a_xz_m':c,'b_xz_m':d,'a_y_m':interp(profile,core.apply(inv,[c[0],0,c[1]])[0]),'b_y_m':interp(profile,core.apply(inv,[d[0],0,d[1]])[0])})
  outer_pts=[[outer[i]+normal[i]*(-4+j*.05) for i in(0,1)] for j in range(161)];terrain=__import__('world_city.concept_city_v3.registered_topography.author',fromlist=['road_height_at']);outer_segments=[{'a_xz_m':c,'b_xz_m':d,'a_y_m':terrain.road_height_at('MAIN_BRIDGE',*c),'b_y_m':terrain.road_height_at('MAIN_BRIDGE',*d)} for c,d in zip(outer_pts,outer_pts[1:])]
  overlay['terminal_transitions'].append({'outer_edge_segments':outer_segments,'id':'TERMINAL_'+name.upper(),'outer_center_xz_m':outer,'inward_unit_xz':direction,'length_m':length,'inner_edge_segments':segments,'grade_bound':.1,'method':'Mean of analytical 10%-Lipschitz lower/upper extensions from both transverse edges. Outer edge samples exact frozen H every5 cm; inner edge matches the shared profile.'})
 overlay['height_lookup']='compile_bridge.deck_y(overlay,x,z): one shared bridge-frame profile, with two explicit bounded 10%-Lipschitz terminal crossfall transitions.'
 overlay['terminal_width_contract']={'total_shared_corridor_m':7,'gate_cart_band_m':4,'shared_pedestrian_margin_each_m':1.5,'full_bridge_cart_width_m':8,'full_bridge_footway_each_m':2.4,'merge_behavior':'Separate bridge walks merge before the unchanged gate. No 8 m cart-lane claim through the 7 m total throat.'}
 junction_path=HERE/'junction_uplift_contract.json';junction=json.loads(junction_path.read_text())
 assert junction['bridge_overlay_sha256']==sha(HERE/'evidence/compiled_before_junction_uplift/continuous_deck_overlay.json')
 overlay['junction_uplift']={'contract':ref(str(junction_path.relative_to(ROOT))),'base_overlay':ref(str((HERE/'evidence/compiled_before_junction_uplift/continuous_deck_overlay.json').relative_to(ROOT))),'regions':junction['junction_regions'],'tie_polygons_xz_m':junction['owned_polygons_xz_m'],'quay_y_m':junction['flat_quay_y_m'],'grade_bound':junction['maximum_analytic_gradient'],'height_rule':'Within exact bridge junction regions only: max(base_deck_y, quay_y - grade_bound * Euclidean distance to finite tie union).','reason':'Full-width oblique tie reached a low bridge edge at +1.886 m; this bounded uplift allows the +2.2 m quay connection without a dip.'}
 overlay['height_lookup']+=' Apply explicit finite junction_uplift after the base profile.'
 overlay['terminal_continuity_tolerance_m']=.001
 overlay['terminal_continuity_limit']='Independent base-overlay audit found 0.21334 mm rail residual and 0.93900 mm cross-boundary residual. This is a 1 mm tolerance contract, not exact mathematical continuity.'
 for r in owned:r['vertex_y_m']=[deck_y(overlay,*q) for q in r['polygon_xz_m']];r.pop('surface_profile',None)
 write(HERE/'continuous_deck_overlay.json',overlay)
 # Compose instances in a rigid, bridge-aligned frame so this remains one bounded job.
 master={'schema':'riverstone.voxel.master.v1','id':'registered_main_bridge_composite_r1','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':None,'coordinate_planes':[],'components':[],'instances':[],'constraints':[{'id':'bridge_present','kind':'nonempty','selector':{}},{'id':'bridge_unified_connected','kind':'connected','selector':{}}],'provenance':{'candidate':ref(str(CANDIDATE.relative_to(ROOT))),'continuous_deck_overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'author':ref(str(Path(__file__).relative_to(ROOT))),'new_engine':False,'new_mesher':False,'cell_edits':False,'source_adaptations':'Native cap contour lowered 5 cm, joint-pier tops lowered 10 cm, parapet bases embedded 10 cm. One shared continuous 40 cm cap supplies the final deck datum. These bounded source changes occur only in the derived assembly.'},'extensions':{'assembly_group_id':'REGISTERED_MAIN_BRIDGE','candidate_pitch_m':PITCH,'candidate_cell_cap':CANDIDATE_CAP,'output_cell_cap':OUTPUT_CAP,'world_pose':frame,'internal_face_policy':'One final composited common occupancy is meshed once; no separate cached bay faces survive internal unions.'}}
 registered={}
 def adopt(path,prefix,world_pose,role):
  src=json.loads((ROOT/path).read_text());key=(path,role)
  if master['materials'] is None:master['materials']=src['materials']
  assert master['materials']==src['materials']
  if key not in registered:
   cmap={}
   for c in src['components']:
    cc=copy.deepcopy(c);new_id=f'SRC_{len(registered):02}_{c["id"]}';cmap[c['id']]=new_id;cc['id']=new_id
    for o in cc['operations']:
     if role=='cap' and c['id']=='deck' and o['id']=='profiled_deck_spandrel':
      for point in o['shape']['polygon'][2:]:point[1]-=.05
     if role=='cap' and c['id']=='parapets':
      for point in o['shape']['polygon'][:len(o['shape']['polygon'])//2]:point[1]-=.1
     if role=='joints' and c['id']=='pier_joints':o['shape']['z_max']-=.1
     if role=='joints' and c['id']=='parapet_joints':o['shape']['z_min']-=.1
    master['components'].append(cc)
   registered[key]=cmap
  cmap=registered[key];relative=core.compose(inv,world_pose);poses={}
  original={i['id']:i for i in src['instances']}
  def local(k):
   if k not in poses:
    i=original[k];v=core.transform(i.get('transform'));poses[k]=core.compose(local(i['parent']),v) if i.get('parent') else v
   return poses[k]
  for i in src['instances']:master['instances'].append({'id':prefix+'__'+i['id'],'component':cmap[i['component']],'transform':core.compose(relative,local(i['id']))})
 for b in p['bays']:
  adopt(b['source']['path'],b['id'],b['transform'],'arch');adopt(b['cap_source']['path'],b['id']+'_CAP',b['transform'],'cap')
  if b.get('pier_extension_source'):adopt(b['pier_extension_source']['path'],b['id']+'_FOOT',b['transform'],'footing')
  rel=core.compose(inv,b['transform']);master['constraints'].append({'id':b['id']+'_real_barrel_void','kind':'empty_region','selector':{},'shape':{'kind':'box','min':[-2,-4.7,-7.01],'max':[2,-1.4,7.01]},'transform':rel})
 adopt(p['joint_source']['path'],'JOINTS',p['joint_transform'],'joints')
 # The shared cap has one global height function. Trim its source footprint to the
 # actual finite union; these are ordinary component-local source cuts.
 deck=[r for r in owned if r['ownership_kind']=='deck'];local_polys=[]
 for r in deck:local_polys.append([[q[0],q[2]] for q in (core.apply(inv,[x,0,z]) for x,z in r['polygon_xz_m'])])
 box=bounds([q for poly in local_polys for q in poly]);xmin,zmin,xmax,zmax=box
 xx=sorted(set([xmin,xmax]+[x for x,y in profile if xmin<x<xmax]));cap=Source('shared_bridge_deck',[xmin,0,zmin],[xmax,5,zmax])
 for i,(x0,x1) in enumerate(zip(xx,xx[1:])):
  y0,y1=interp(profile,x0),interp(profile,x1);cap.op(f'continuous_cap_{i:04}',extrusion([[x0,y0-.4],[x1,y1-.4],[x1,y1],[x0,y0]],zmin,zmax),'stone',component='shared_deck')
 outside=[[[xmin,zmin],[xmax,zmin],[xmax,zmax],[xmin,zmax]]]
 for poly in local_polys:
  outside=[q for part in outside for q in (geo.convex_difference(part,poly) if overlaps(bounds(part),bounds(poly)) else [part]) if geo.polygon_area(q)>1e-8]
 lo_y=min(y for x,y in profile)-.5;hi_y=max(y for x,y in profile)+.1
 for i,poly in enumerate(outside):cap.plan(f'trim_outside_owned_deck_{i:04}',poly,lo_y,hi_y,component='shared_deck',action='cut')
 cm=cap.finish()
 for c in cm['components']:master['components'].append(c)
 master['instances'].append({'id':'SHARED_CONTINUOUS_DECK','component':'shared_deck'})
 # Native cap triangles approximate only the finite analytic junction uplift.
 # The unchanged common compiler unions them with all bays before final meshing.
 junction_cap=Source('port_junction_cap',[xmin,0,zmin],[xmax,5,zmax]);spacing=.5;sample_cache={};approx=[];maximum_lift=0.;maximum_triangle_grade=0.;triangles=0
 def point_height(q):
  key=tuple(round(v,9) for v in q)
  if key not in sample_cache:
   w=core.apply(frame,[q[0],0,q[1]]);sample_cache[key]=(deck_y(overlay,w[0],w[2]),interp(profile,q[0]))
  return sample_cache[key]
 for region in junction['junction_regions']:
  local_poly=[[q[0],q[2]] for q in (core.apply(inv,[x,0,z]) for x,z in region['polygon_xz_m'])];rb=bounds(local_poly)
  for ix in range(math.floor(rb[0]/spacing),math.ceil(rb[2]/spacing)):
   for iz in range(math.floor(rb[1]/spacing),math.ceil(rb[3]/spacing)):
    x0,z0=ix*spacing,iz*spacing;square=[[x0,z0],[x0+spacing,z0],[x0+spacing,z0+spacing],[x0,z0+spacing]]
    for tri in ([square[0],square[1],square[2]],[square[0],square[2],square[3]]):
     clipped=geo.convex_intersection(tri,local_poly)
     if geo.polygon_area(clipped)<1e-8:continue
     for k in range(1,len(clipped)-1):
      vertices=[clipped[0],clipped[k],clipped[k+1]]
      if geo.polygon_area(vertices)<1e-8:continue
      values=[point_height(q) for q in vertices];lift=max(y-base for y,base in values)
      if lift<1e-7:continue
      pts=[[q[0],y,q[1]] for q,(y,base) in zip(vertices,values)];grade=triangular_cap(junction_cap,f'junction_triangle_{triangles:05}',pts);maximum_triangle_grade=max(maximum_triangle_grade,grade);maximum_lift=max(maximum_lift,lift);triangles+=1
      centre=[sum(q[k] for q in vertices)/3 for k in (0,1)];exact=point_height(centre)[0];linear=sum(y for y,b in values)/3;approx.append(abs(linear-exact))
 if triangles:
  for i,poly in enumerate(outside):junction_cap.plan(f'junction_trim_owned_{i:04}',poly,lo_y-.5,hi_y+.5,component='port_junction_cap',action='cut')
  for c in junction_cap.finish()['components']:master['components'].append(c)
  master['instances'].append({'id':'PORT_TIE_JUNCTION_CAP','component':'port_junction_cap'})
 master['extensions']['junction_cap_approximation']={'native_triangular_prisms':triangles,'source_lattice_spacing_m':spacing,'maximum_sampled_top_plane_error_m':max(approx,default=0),'maximum_triangle_gradient':maximum_triangle_grade,'maximum_analytic_uplift_m':maximum_lift,'analytical_datum_grade_bound':.1,'note':'Continuous source triangle approximation is independently reported; the final 0.25 m occupied-cell surface adds separately measured quantization.'}
 # A real empty navigation prism through the full bridge, plus above-deck cart clearance.
 nav=next(b for b in p['bays'] if b['id']==p['navigation_channel']['bay_id']);ys=[]
 for x in (-3,3):
  for z in (-7,7):q=core.apply(nav['transform'],[x,0,z]);ys.append(__import__('world_city.concept_city_v3.registered_topography.author',fromlist=['river_water_y']).river_water_y(q[0]))
 master['constraints'].append({'id':'central_navigation_clearance_3m','kind':'empty_region','selector':{},'shape':{'kind':'box','min':[-3,min(ys)+.05-nav['arch_top_y_m'],-7.01],'max':[3,max(ys)+3-nav['arch_top_y_m'],7.01]},'transform':core.compose(inv,nav['transform'])})
 for b in p['bays']:
  c=core.apply(inv,[b['center_xz_m'][0],0,b['center_xz_m'][1]]);y=interp(profile,c[0]);master['constraints'].append({'id':b['id']+'_central_cart_headroom','kind':'empty_region','selector':{},'shape':{'kind':'box','min':[-1,y+.3-b['arch_top_y_m'],-3.8],'max':[1,y+3.0-b['arch_top_y_m'],3.8]},'transform':core.compose(inv,b['transform'])})
 # Preserve the existing port connection with a genuine side-parapet opening.
 tie=next(r for r in plan['roads'] if r['id']=='PORT_BRIDGE_TIE');portal_raw=[strip(a,b,tie['width_m']+1) for a,b in zip(tie['polyline_xz_m'],tie['polyline_xz_m'][1:])];portal=[]
 for poly in portal_raw:
  for region in deck:
   cut=geo.convex_intersection(poly,region['polygon_xz_m'])
   if geo.polygon_area(cut)>1e-7:portal.append({'id':f'PORT_TIE_CUT_{len(portal):02}','polygon_xz_m':cut})
 portal=trim_union(portal);master['assembly_cuts']=[]
 parapets=[i for i in master['instances'] if 'parapet' in i['component']]
 for j,part in enumerate(portal):
  lp=[[q[0],q[2]] for q in (core.apply(inv,[x,0,z]) for x,z in part['polygon_xz_m'])];ys=[deck_y(overlay,*q) for q in part['polygon_xz_m']];src=Source('portal',[-1,-1,-1],[1,1,1]);src.plan('opening',lp,min(ys)-.5,max(ys)+1.5,action='cut');op=next(iter(src.components.values()))['operations'][0]
  for inst in parapets:
   master['assembly_cuts'].append({'id':f'port_opening_{j}_{inst["id"]}','action':'cut','selector':{'instance':inst['id']},'shape':op['shape'],'transform':op['transform']})
 interface={'schema':'riverstone.bridge_port_tie_interface.v1','source_road_id':tie['id'],'source_polyline_xz_m':tie['polyline_xz_m'],'source_width_m':tie['width_m'],'parapet_opening_reserved_width_m':tie['width_m']+1,'parapet_cut_regions':portal,'bridge_endpoint_xz_m':tie['polyline_xz_m'][-1],'bridge_endpoint_y_m':deck_y(overlay,*tie['polyline_xz_m'][-1]),'port_endpoint_xz_m':tie['polyline_xz_m'][0],'port_endpoint_floor_y_m':2.2,'continuous_deck_overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'outside_bridge_profile_status':'Requires the port/terrain-owned finite approach to meet deck_y on its full bridge boundary; no flat +2.2 override is authorized.'}
 write(HERE/'port_tie_interface.json',interface)
 master['provenance']['port_tie_interface']=ref(str((HERE/'port_tie_interface.json').relative_to(ROOT)))
 core.validate_master(master,PITCH);write(HERE/'assembly_source.json',master)
 # Match the unchanged compiler's AABB candidate counting before any sampling.
 comps={c['id']:c for c in master['components']};count=0;details=[];paint_upper=0
 def count_shape(shape,tr):
  shape=core.prepare_shape(shape,PITCH);lo,hi=core.shape_bounds(shape);corners=[core.apply(tr,p) for p in itertools.product(*zip(lo,hi))];mn=[min(q[i] for q in corners) for i in range(3)];mx=[max(q[i] for q in corners) for i in range(3)];return math.prod(math.ceil(b/PITCH-core.EPS)-math.floor(a/PITCH+core.EPS) for a,b in zip(mn,mx))
 for inst in master['instances']:
  tr=core.transform(inst.get('transform'));subtotal=0
  for o in comps[inst['component']]['operations']:
   n=count_shape(o['shape'],core.compose(tr,core.transform(o.get('transform'))));subtotal+=n
   if o['action']=='paint':paint_upper+=n
  count+=subtotal;details.append({'instance_id':inst['id'],'candidate_cells':subtotal})
 for cut in master.get('assembly_cuts',[]):count+=count_shape(cut['shape'],core.transform(cut.get('transform')))
 for con in master['constraints']:
  if con['kind']=='empty_region':count+=count_shape(con['shape'],core.transform(con.get('transform')))
 report={'schema':'riverstone.bridge_compile_preflight.v1','candidate':ref(str(CANDIDATE.relative_to(ROOT))),'assembly_source':ref(str((HERE/'assembly_source.json').relative_to(ROOT))),'continuous_deck_overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'pitch_m':PITCH,'predicted_candidate_cells':count,'paint_aabb_cell_upper_bound':paint_upper,'candidate_cap':CANDIDATE_CAP,'output_cap':OUTPUT_CAP,'estimated_peak_memory_mib_range':[300,850],'bounded_runtime_target_seconds':240,'instance_candidate_counts':details,'common_core':ref('voxel_character/common/core.py'),'common_mesher':ref('voxel_character/tools/mesh.py'),'source_candidate_unchanged':sha(CANDIDATE)==SEALED,'overlay_regions':len(owned),'shared_cap_outside_cut_polygons':len(outside)}
 assert count<=CANDIDATE_CAP,(count,CANDIDATE_CAP);write(HERE/'compile_preflight.json',report)
 print(json.dumps({k:report[k] for k in ('predicted_candidate_cells','paint_aabb_cell_upper_bound','estimated_peak_memory_mib_range','overlay_regions','shared_cap_outside_cut_polygons')},indent=2));return master,overlay,report

def compile_bridge(master,overlay,preflight):
 started=time.monotonic();compiled=coordinate_planes.compile_master(master,{'pitch':PITCH},max_candidate_cells=CANDIDATE_CAP,max_output_cells=OUTPUT_CAP);elapsed=time.monotonic()-started
 assert compiled['candidate_cells']==preflight['predicted_candidate_cells']
 report={'schema':'riverstone.registered_bridge_compile.v1','candidate':ref(str(CANDIDATE.relative_to(ROOT))),'assembly_source':ref(str((HERE/'assembly_source.json').relative_to(ROOT))),'continuous_deck_overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'valid':compiled['valid'],'constraints':compiled['constraints'],'candidate_cells':compiled['candidate_cells'],'output_cells':len(compiled['cells']),'pitch_m':PITCH,'compile_seconds':elapsed,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'payload_hash':compiled['payload_hash'],'master_hash':compiled['master_hash'],'core_sha256':compiled['compiler_source_hash'],'source_candidate_unchanged':sha(CANDIDATE)==SEALED}
 write(HERE/'compile_report.json',report)
 if not compiled['valid']:raise RuntimeError('Common source constraints failed; compiled geometry not released')
 render=render_data.make_render_data(compiled);write(HERE/'cache/bridge.pitch_0.25.compiled.json',compiled);write(HERE/'cache/bridge.pitch_0.25.render.json',render)
 report.update(quad_count=render['quad_count'],render=ref(str((HERE/'cache/bridge.pitch_0.25.render.json').relative_to(ROOT))),compiled=ref(str((HERE/'cache/bridge.pitch_0.25.compiled.json').relative_to(ROOT))),total_seconds=time.monotonic()-started,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 write(HERE/'compile_report.json',report);print(json.dumps({k:report[k] for k in ('valid','candidate_cells','output_cells','quad_count','total_seconds','peak_rss_mib')},indent=2))
 return compiled,render,report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--compile',action='store_true');args=ap.parse_args();m,o,r=prepare()
 if args.compile:compile_bridge(m,o,r)
