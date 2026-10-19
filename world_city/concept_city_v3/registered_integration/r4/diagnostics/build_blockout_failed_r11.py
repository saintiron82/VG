"""Source plan to bounded Godot spatial-review data; no voxel engine changes.
This first representation uses honest mass/terrain proxies. Common assemblies replace
source IDs later. It never edits generated common cells or the prior city versions.
"""
from pathlib import Path
import hashlib,json,math,sys,importlib,collections,time
from functools import lru_cache
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inside(p,poly):
 x,z=p;yes=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:yes=not yes
 return yes
def poly(o):return o.get('polygon_xz_m',o.get('boundary_xz_m',[]))
def path(o):return o.get('polyline_xz_m',o.get('points_xz_m',[]))
def length(p):return sum(math.dist(a,b) for a,b in zip(p,p[1:]))
def samples(p,step=2):
 out=[]
 for a,b in zip(p,p[1:]):
  n=max(1,math.ceil(math.dist(a,b)/step))
  out.extend([[a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n] for i in range(n)])
 if p:out.append(p[-1])
 return out
def main():
 args=dict(a[2:].split('=',1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
 source=Path(args.get('source',HERE/'source/plan.json')).resolve(); source_bytes=source.read_bytes(); source_hash=hashlib.sha256(source_bytes).hexdigest(); plan=json.loads(source_bytes); write(Path(args.get('source-snapshot',HERE/'generated/source_plan.snapshot.json')),plan)
 landmark_overlay={}
 if 'landmark-proxies' in args:
  overlay_path=Path(args['landmark-proxies']).resolve();landmark_overlay=json.loads(overlay_path.read_text());new_groups={g['id']:g for g in landmark_overlay['groups']}
  old_groups=plan.get('landmark_components',[]);plan['landmark_components']=[new_groups.pop(g['id'],g) for g in old_groups]+list(new_groups.values())
  landmark_overlay={'path':str(overlay_path.relative_to(ROOT)),'sha256':sha(overlay_path),'status':'explicit component review overlay; canonical source unchanged'}
 integration=json.loads(Path(args['integration']).read_text()) if 'integration' in args else {}
 if integration:
  assert integration['source_plan_sha256']==source_hash,'Integration/source hash mismatch'
  access=integration.get('access_overlay',{});remove=set(access.get('remove_path_ids',[]));plan['paths']=[p for p in plan['paths'] if p['id'] not in remove]+access.get('add_paths',[])
  replacements={r['id']:r for r in access.get('replace_roads',[])};plan['roads']=[replacements.get(r['id'],r) for r in plan['roads']]
 mod=importlib.import_module(args.get('terrain-module',integration.get('terrain_module','world_city.concept_city_v3.topography.author')))
 h=lru_cache(maxsize=None)(mod.height_at); land_h=lru_cache(maxsize=None)(getattr(mod,'land_height_at',mod.height_at)); terrain_contract=mod.build_contract()
 if terrain_contract.get('source_plan_sha256'):assert terrain_contract['source_plan_sha256']==source_hash,'Source changed during snapshot; retry with stable source.'
 from world_city.concept_city_v3.review_geometry import DomainCut,fan,prune_collinear_xyz
 from world_city.runtime_city.checks import placement as geo
 water_domains=mod.finite_water_polygons() if hasattr(mod,'finite_water_polygons') else []
 floor_records=integration.get('floor_ownership_masks',[])
 floor_cut=DomainCut(floor_records)
 water_cut=DomainCut(water_domains+floor_records)
 material_classifier=importlib.import_module(integration['material_classifier_module']) if integration.get('material_classifier_module') else None
 groups={}; terrain_records=[]
 def tri(material,a,b,c):
  # Upward source winding for all land/water ribbons, independent of input polygon winding.
  if (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])<0:b,c=c,b
  groups.setdefault(material,[]).extend([a,b,c])
 def quad(material,a,b,c,d):tri(material,a,c,b);tri(material,a,d,c)
 def xyz(x,z,offset=0):return [round(x,5),round(land_h(x,z)+offset,5),round(z,5)]
 districts=plan.get('districts',[])
 palette={'ground':'68735b','road':'aaa28b','alley':'9c9782','water':'3c8998','wall':'b4ac93','support':'8c897b','boundary':'736a59'}
 for d in districts:palette['land_'+d['id']]=d.get('ground_color',{'noble':'7d8966','clergy':'889276','poor':'817d68','craft':'94856d','merchant':'a0957b','port':'8b897c'}.get(d.get('role'),'848775'))
 palette.update({'plot_noble_estate':'758565','plot_merchant_court':'9b9078','plot_poor_block':'91846e','plot_old_town_block':'968d75','space_training':'aaa084','space_civic':'aba58f','space_garden':'6e805a'})
 plots=plan.get('plots',[]);spaces=plan.get('spaces',[])
 plot_index=geo._SpatialIndex(32);space_index=geo._SpatialIndex(32);ground_index=geo._SpatialIndex(32);grounds=[]
 for n,p in enumerate(plots):plot_index.add(n,poly(p))
 for n,p in enumerate(spaces):space_index.add(n,poly(p))
 for p in plan.get('grounds',[]):
  for q in p['polygons_xz_m']:ground_index.add(len(grounds),q);grounds.append((q,p['material']))
 palette.update({'ground_earth':'8b826a','ground_grass':'71815e','ground_stone':'a49f8a'})
 # Finite land surface; four-metre review mesh, not a microscopic full-city voxel fill.
 terrain_start=time.monotonic()
 bounds=terrain_contract.get('review_bounds_xz_m',[-580,-520,580,590]);step=int(args.get('terrain-pitch',4));exact_ownership=hasattr(mod,'surface_domains');owned_domains_count=0;interface_ids=set()
 for z in range(math.floor(bounds[1]/step)*step,math.ceil(bounds[3]/step)*step,step):
  if (z-math.floor(bounds[1]/step)*step)%(step*16)==0:print(json.dumps({'phase':'terrain_owner_export','z':z,'elapsed_s':round(time.monotonic()-terrain_start,2),'domains':owned_domains_count,'surface_vertices':sum(len(q) for q in groups.values())}),flush=True)
  for x in range(math.floor(bounds[0]/step)*step,math.ceil(bounds[2]/step)*step,step):
   key='ground'; tile=[[x,z],[x+step,z],[x+step,z+step],[x,z+step]]
   for d in districts:
    if inside([x+2,z+2],poly(d)):key='land_'+d['id'];break
   for gi in ground_index.candidates(tile):
    q,material=grounds[gi]
    if inside([x+2,z+2],q):key='ground_'+material;break
   for pi in plot_index.candidates(tile):
    pp=plots[pi]
    if inside([x+2,z+2],poly(pp)):
     pk='plot_'+pp.get('property_type',pp.get('land_use',''))
     if pk in palette:key=pk
     break
   for si in space_index.candidates(tile):
    sp=spaces[si]
    if inside([x+2,z+2],poly(sp)):
     role=sp.get('role','')
     if 'training' in role:key='space_training'
     elif 'market' in role or 'civic' in role:key='space_civic'
     elif 'garden' in role or 'park' in role:key='space_garden'
   if exact_ownership:
    records=mod.surface_domains([x,z,x+step,z+step]);owned_domains_count+=len(records)
    for record in records:
     if not record.get('render_land',True):continue
     material='road' if record['kind'] in ('road','replacement_road','port_tie') else 'alley' if record['kind'] in ('door_landing','door_approach') else key
     # Explicit new owner material is data, never a second offset floor.
     requested=record.get('material')
     if requested is None and record['kind'] in ('external_triangular_surface','reservoir_service_public_landing'):requested=record.get('material_hint')
     if requested is not None:
      requested={'stone':'ground_stone','earth':'ground_earth','grass':'ground_grass'}.get(requested,requested)
      if requested not in palette:raise ValueError('Unknown explicit surface material: '+str(requested))
      material=requested
     for piece in floor_cut.subtract(record['polygon_xz_m']):
      verts=prune_collinear_xyz([[q[0],mod.surface_height_at(record,*q),q[1]] for q in piece])
      for a,b,c in fan(verts):
       den=(b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0])
       if abs(den)<=1e-10:continue
       if material_classifier is None:tri(material,a,b,c)
       else:
        # Split color boundaries on the existing rendered triangle's plane.
        # This cannot create a new cliff or change the original terrain profile.
        regions=material_classifier.classify_material_regions(record,[[v[0],v[2]] for v in (a,b,c)])
        for region in regions:
         mat={'stone':'ground_stone','earth':'ground_earth','grass':'ground_grass'}.get(region['material'],region['material'])
         if mat not in palette:raise ValueError('Unknown classified material: '+str(mat))
         vv=[]
         for x,z in region['polygon_xz_m']:
          u=((x-a[0])*(c[2]-a[2])-(z-a[2])*(c[0]-a[0]))/den
          v=((b[0]-a[0])*(z-a[2])-(b[2]-a[2])*(x-a[0]))/den
          vv.append([x,a[1]+u*(b[1]-a[1])+v*(c[1]-a[1]),z])
         for aa,bb,cc in fan(vv):tri(mat,aa,bb,cc)
    for interface in mod.retaining_interfaces([x,z,x+step,z+step],records):
     if interface['id'] in interface_ids:continue
     interface_ids.add(interface['id']);a,b,c,d=interface['vertices_xyz_m'];groups.setdefault('bank',[]).extend([a,b,c,a,c,d])
   else:
    for piece in water_cut.subtract(tile):
     for a,b,c in fan(piece):tri(key,xyz(*a),xyz(*b),xyz(*c))
 # Finite supplemental triangles preserve the validated source plane and exact
 # shared knots. They replace explicit owner cuts, never a second offset overlay.
 supplemental_count=0;supplemental_side_count=0
 if hasattr(mod,'supplemental_surface_domains'):
  for record in mod.supplemental_surface_domains(bounds):
   if not record.get('render_surface',True):continue
   material=record.get('material','road')
   if material not in palette:material='road'
   for a,b,c in fan(record['vertices_xyz_m']):
    if abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))>1e-10:tri(material,a,b,c);supplemental_count+=1
 if hasattr(mod,'supplemental_side_records'):
  seen=set()
  for record in mod.supplemental_side_records(bounds):
   if record['id'] in seen:continue
   seen.add(record['id']);a,b,c,d=record['vertices_xyz_m'];groups.setdefault('bank',[]).extend([a,b,c,a,c,d]);supplemental_side_count+=1
 road_audits=[]
 def ribbon(points,width,material,height_fn=None,offset=.055):
  pts=samples(points,2)
  for a,b in zip(pts,pts[1:]):
   dx,dz=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dz)
   if L<1e-8:continue
   nx,nz=-dz/L*width/2,dx/L*width/2
   q=[[a[0]+nx,a[1]+nz],[b[0]+nx,b[1]+nz],[b[0]-nx,b[1]-nz],[a[0]-nx,a[1]-nz]]
   for piece in floor_cut.subtract(q):
    for aa,bb,cc in fan(piece):
     tri(material,*[[p[0],(height_fn(*p) if height_fn else h(*p))+offset,p[1]] for p in [aa,bb,cc]])
  return pts
 for r in plan.get('roads',[]):
  rh=(lambda x,z,rid=r['id']:mod.road_height_at(rid,x,z)) if hasattr(mod,'road_height_at') else h
  pts=samples(path(r),2) if exact_ownership else ribbon(path(r),float(r['width_m']),'alley' if float(r['width_m'])<4 else 'road',rh,0)
  grades=[abs(rh(*a)-rh(*b))/math.dist(a,b) for a,b in zip(pts,pts[1:]) if math.dist(a,b)>1e-8]
  road_audits.append({'id':r['id'],'length_m':round(length(pts),2),'max_sample_grade':round(max(grades,default=0),4),'class':r.get('kind','road'),'grade_policy':'candidate measurement, controller/nav validation follows'})
 for pp in ([] if exact_ownership else plan.get('paths',[])):
  ph=(lambda x,z,pid=pp['id']:mod.path_height_at(pid,x,z)) if hasattr(mod,'path_height_at') else h
  ribbon(path(pp),float(pp['width_m']),'alley',ph,0)
 # Water graph author provides finite visible channels; water heads are independent of land.
 water=terrain_contract.get('water_surfaces',[])
 if water_domains:
  for wd in water_domains:
   sid=wd['surface_id'];si=wd.get('segment_index',0)
   for a,b,c in fan(wd['polygon_xz_m']):
    tri('water',*[ [p[0],mod.water_height_at(sid,p[0],p[1],si),p[1]] for p in [a,b,c] ])
 else:raise ValueError('Finite water domains required; no thin-feeder coarse-grid workaround.')
 # Explicit finite bank faces close visible cut edges; internal water partitions
 # do not acquire duplicate bank walls. This is a review mesh, not a hydraulic proof.
 bank_face_count=0
 if terrain_contract.get('water_support'):
  omitted_bank_indices=set(terrain_contract.get('omitted_water_bank_indices',[]))
  native_bed_masks=terrain_contract.get('omit_source_waterbed_polygons',[])
  bed_cuts={sid:DomainCut([r for r in native_bed_masks if r['surface_id']==sid]) for sid in {r['surface_id'] for r in native_bed_masks}}
  for bank_index,bank in enumerate(terrain_contract['water_support']['exterior_banks']):
   if bank_index in omitted_bank_indices:continue
   a,b,c,d=bank['vertices_xyz_m'];groups.setdefault('bank',[]).extend([a,b,c,a,c,d]);bank_face_count+=1
  for bed in terrain_contract['water_support']['beds']:
   cut=bed_cuts.get(bed['surface_id']);pieces=cut.subtract(bed['polygon_xz_m']) if cut else [bed['polygon_xz_m']]
   for piece in pieces:
    for a,b,c in fan(piece):
     tri('bank',*[[p[0],mod.water_height_at(bed['surface_id'],*p)-bed['bed_depth_m'],p[1]] for p in [a,b,c]])
 elif hasattr(mod,'water_samples_at'):

  for wd in water_domains:
   ring=wd['polygon_xz_m'];sid=wd['surface_id'];si=wd.get('segment_index',0)
   for aa,bb in zip(ring,ring[1:]+ring[:1]):
    dx,dz=bb[0]-aa[0],bb[1]-aa[1];ll=math.hypot(dx,dz)
    if ll<1e-8:continue
    nx,nz=-dz/ll*.025,dx/ll*.025;nn=max(1,math.ceil(ll/2))
    for j in range(nn):
     a=[aa[k]+(bb[k]-aa[k])*j/nn for k in (0,1)];b=[aa[k]+(bb[k]-aa[k])*(j+1)/nn for k in (0,1)];mid=[(a[k]+b[k])/2 for k in (0,1)]
     left=bool(mod.water_samples_at(mid[0]+nx,mid[1]+nz));right=bool(mod.water_samples_at(mid[0]-nx,mid[1]-nz))
     if left==right:continue
     ox,oz=(-nx,-nz) if left else (nx,nz)
     topa=land_h(a[0]+ox,a[1]+oz);topb=land_h(b[0]+ox,b[1]+oz)
     lowa=mod.water_height_at(sid,*a,si)-wd.get('bed_depth_m',1);lowb=mod.water_height_at(sid,*b,si)-wd.get('bed_depth_m',1)
     if max(topa-lowa,topb-lowb)<.01:continue
     # Vertical faces use an explicit two-sided material in the review scene.
     groups.setdefault('bank',[]).extend([[a[0],lowa,a[1]],[b[0],lowb,b[1]],[b[0],topb,b[1]],[a[0],lowa,a[1]],[b[0],topb,b[1]],[a[0],topa,a[1]]])
     bank_face_count+=1
 palette['bank']='7c7a65'
 boxes=[]; supports=[]; counts=collections.Counter()
 role_colors={'noble':'b9b09c','clergy':'b7b6aa','merchant':'c0ae91','craft':'a28f73','poor':'8f7e65','port':'9c9480','castle':'aaa99b','monastery':'b9b5a0'}
 did={d['id']:d for d in districts}
 landmark_groups=plan.get('landmark_components',[])
 suppressed={bid for g in landmark_groups for bid in g.get('replaces_source_building_ids',[])}
 suppressed.update(plan.get('landmark_component_suppressed_building_ids',[]))
 for b in plan['buildings']:
  if b['id'] in suppressed:continue
  p=b.get('position_xz_m',b.get('center_xz_m')); w,d=float(b['width_m']),float(b['depth_m']);yaw=float(b.get('yaw_rad',0)); base=h(*p);height=float(b['height_m']);role=did.get(b['district_id'],{}).get('role','merchant');role={'merchants':'merchant','cathedral':'clergy','old_town':'craft','civic':'merchant'}.get(role,role)
  corners=[]
  for x,z in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]:corners.append([p[0]+x*math.cos(yaw)+z*math.sin(yaw),p[1]-x*math.sin(yaw)+z*math.cos(yaw)])
  base=max(h(*q) for q in corners+[p]); low=min(h(*q) for q in corners+[p]); counts[role]+=1
  color=b.get('massing_color',role_colors.get(role,'b4a58b'));palette['mass_'+role]=color
  boxes.append({'id':b['id'],'position_m':[p[0],base+height/2,p[1]],'size_m':[w,height,d],'yaw_rad':yaw,'material':'mass_'+role,'source_base_y_m':base,'assembly_intent':b.get('assembly_intent',{}),'replacement_state':'spatial_mass_only'})
  if base-low>.08:supports.append({'id':b['id']+':support','position_m':[p[0],(base+low)/2,p[1]],'size_m':[w,base-low,d],'yaw_rad':yaw,'material':'support'})
 for foundation in terrain_contract.get('ordinary_foundations',[]):
  ring=foundation['polygon_xz_m'];a,b,c,d=ring;w=math.dist(a,b);depth=math.dist(b,c);center=[sum(q[k] for q in ring)/4 for k in (0,1)];top=foundation['top_y_m'];bottom=foundation['bottom_y_m']
  supports.append({'id':foundation['source_mass_id']+':owned_foundation','position_m':[center[0],(top+bottom)/2,center[1]],'size_m':[w,top-bottom,depth],'yaw_rad':math.atan2(-(b[1]-a[1]),b[0]-a[0]),'material':'support','source_mass_id':foundation['source_mass_id'],'replacement_state':'finite_owned_foundation_review_solid_not_common_compiled'})
 landmark_count=0
 palette.update({'landmark_stone':'b7b3a1','landmark_roof':'69706e','landmark_wood':'8c7557','landmark_clay':'a86c50','stair':'b0a48b'})
 for group in landmark_groups:
  anchor=group['world_anchor_xyz_m']
  for component in group['masses']:
   local=component['position_local_xyz_m'];size=component['size_xyz_m'];role=component['semantic_role']
   material={'slate_gray':'landmark_roof','clay_red':'landmark_clay','warm_stone':'landmark_stone'}.get(component.get('color_role'), 'landmark_roof' if role=='roof' else 'landmark_wood' if role in ('timber','crane','boat') else 'landmark_stone')
   boxes.append({'id':'landmark:'+group['id']+':'+component['id'],'position_m':[anchor[i]+local[i] for i in range(3)],'size_m':size,'yaw_rad':math.radians(component.get('yaw_degrees',0)),'material':material,'source_operation_ids':component.get('source_operation_ids',[]),'source_detail_id':component.get('source_detail_id'),'replacement_state':'component_envelope_only_not_collision','semantic_role':role})
   landmark_count+=1
 # Walls are honest placeholders split at source gates. Source openings are never guessed from images.
 boundary=plan.get('boundary_xz_m',plan.get('city_boundary',{}).get('polygon_xz_m',[]));gates=plan.get('gates',[])
 wall_count=0
 wall_levels=plan.get('wall_registration',{}).get('levels_m',[])
 for wi,(a,b) in enumerate(zip(boundary,boundary[1:]+boundary[:1])):
  L=math.dist(a,b); n=max(1,math.ceil(L/4));dx,dz=(b[0]-a[0])/L,(b[1]-a[1])/L
  for i in range(n):
   x=a[0]+dx*L*(i+.5)/n;z=a[1]+dz*L*(i+.5)/n
   if any(math.dist([x,z],g.get('position_xz_m',g.get('center_xz_m',[1e9,1e9])))<g.get('opening_width_m',g.get('width_m',10))/2+L/n/2 for g in gates):continue
   t=(i+.5)/n;base=(wall_levels[wi]*(1-t)+wall_levels[(wi+1)%len(wall_levels)]*t) if len(wall_levels)==len(boundary) else h(x,z)
   bottom=min(base,land_h(x,z));wallheight=base+8-bottom
   boxes.append({'id':f'wall:{wall_count}','position_m':[x,bottom+wallheight/2,z],'size_m':[2,wallheight,L/n+.03],'yaw_rad':math.atan2(dx,dz),'material':'wall','declared_curtain_base_y_m':base,'foundation_depth_m':base-bottom});wall_count+=1
 for pp in plots:
  if pp.get('property_type') not in ('noble_estate','noble_estate_registered'):continue
  ring=poly(pp);gate=pp.get('gate_position_xz_m',[1e9,1e9])
  for ei,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
   L=math.dist(a,b);n=max(1,math.ceil(L/3));dx,dz=(b[0]-a[0])/L,(b[1]-a[1])/L
   for j in range(n):
    x=a[0]+dx*L*(j+.5)/n;z=a[1]+dz*L*(j+.5)/n
    if math.dist([x,z],gate)<3+L/n/2:continue
    boxes.append({'id':f'{pp["id"]}:boundary:{ei}:{j}','position_m':[x,h(x,z)+1.2,z],'size_m':[.6,2.4,L/n+.01],'yaw_rad':math.atan2(dx,dz),'material':'boundary','source_plot_id':pp['id']})
 retaining_count=0
 for record in terrain_contract.get('neighborhood_terraces',[])+terrain_contract.get('compound_pads',[]):
  for w in record.get('retaining_segments',[]):
   a,b=w['from_xz_m'],w['to_xz_m'];L=math.dist(a,b);bottom=w['bottom_y_m'];bottom=min(bottom) if isinstance(bottom,list) else bottom;top=w['top_y_m']
   if L<.01 or top-bottom<.05:continue
   boxes.append({'id':f'retaining:{retaining_count}','position_m':[(a[0]+b[0])/2,(top+bottom)/2,(a[1]+b[1])/2],'size_m':[w.get('thickness_m',.5),top-bottom,L],'yaw_rad':math.atan2(b[0]-a[0],b[1]-a[1]),'material':'support'});retaining_count+=1
 stair_count=0
 for stair in terrain_contract.get('neighborhood_stair_geometry',[]):
  for tread in stair['treads']:
   pp=tread['polygon_xz_m'];xs=[p[0] for p in pp];zs=[p[1] for p in pp];top=tread['top_y_m'];bottom=tread['bottom_y_m']
   boxes.append({'id':stair['id']+':tread:'+str(tread['index']),'position_m':[(min(xs)+max(xs))/2,(top+bottom)/2,(min(zs)+max(zs))/2],'size_m':[max(xs)-min(xs),top-bottom,max(zs)-min(zs)],'yaw_rad':0,'material':'stair','replacement_state':'source_step_geometry_proxy'})
   stair_count+=1
 cameras=plan.get('inspection_cameras',{})
 cameras.setdefault('overview',{'position_m':[850,820,1160],'target_m':[0,5,0],'ortho_size_m':1040})
 cameras.setdefault('noble',{'position_m':[-100,160,-30],'target_m':[-230,15,-200]})
 cameras.setdefault('poor',{'position_m':[400,105,390],'target_m':[260,5,230]})
 cameras.setdefault('market',{'position_m':[125,85,155],'target_m':[20,7,30]})
 cameras.setdefault('north',{'position_m':[250,180,35],'target_m':[45,12,-200]})
 # A real reserved interior alley, rather than a camera invented inside a building.
 eligible=[r for r in plan['roads'] if r.get('kind')=='connected_block_interior_alley' and any(p[0]>100 and p[1]>90 for p in path(r))]
 if eligible:
  alley=eligible[len(eligible)//2];line=path(alley);a=line[0];b=line[1];L=math.dist(a,b);t=min(.25,2/max(L,1));pos=[a[i]+(b[i]-a[i])*t for i in range(2)]
  cameras['alley_human']={'position_m':[pos[0],mod.road_height_at(alley['id'],*pos)+1.65,pos[1]],'target_m':[b[0],mod.road_height_at(alley['id'],*b)+1.65,b[1]],'source_road_id':alley['id'],'eye_height_m':1.65}
 cameras.setdefault('terrace',{'position_m':[-315,25,-35],'target_m':[-326,15,-57]})
 if integration:
  remove_proxy_ids=set(integration.get('remove_proxy_ids',[]));replace_plot_ids=set(integration.get('replace_plot_ids',[]));replace_groups=set(integration.get('replace_landmark_groups',[]))
  supports=[b for b in supports if b['id'] not in remove_proxy_ids]
  boxes=[b for b in boxes if b['id'] not in remove_proxy_ids and not (b.get('source_plot_id') in replace_plot_ids) and not any(b['id'].startswith('landmark:'+gid+':') for gid in replace_groups)]
 scene={'schema' :'riverstone.concept_city.blockout.v3','status':'whole_city_spatial_review_not_final_voxel','source_plan':str(source.relative_to(ROOT)),'source_plan_sha256':source_hash,'landmark_proxy_overlay':landmark_overlay,'terrain_contract':terrain_contract,'materials':palette,'surfaces':groups,'boxes':boxes+supports,'inspection_cameras':cameras,'counts':{'building_masses':len(plan['buildings']),'by_social_role':dict(counts),'wall_segments':wall_count,'support_proxies':len(supports),'terrain_sample_pitch_m':step,'retaining_proxy_segments':retaining_count,'landmark_components':landmark_count,'suppressed_landmark_envelopes':len(suppressed),'stair_tread_proxies':stair_count,'finite_water_domains':len(water_domains),'finite_bank_face_segments':bank_face_count,'exact_owned_domains':owned_domains_count,'exact_retaining_interfaces':len(interface_ids)},'limits':['Simple masses and sampled terrain only; common-source replacement follows.','No final character/nav/interior or hydraulic simulation claim.','Small render-only road overlay offsets are blockout legibility, not final ground ownership.']}
 if integration:
  scene['common_instances']=integration['common_instances'];scene['common_assets']=integration['common_assets'];scene['integration_provenance']=integration.get('provenance',{});scene['integration_sha256']=sha(Path(args['integration']));scene['status']='common_exterior_candidate_ground_and_access_under_validation';scene['counts']['common_instances']=len(scene['common_instances']);scene['counts']['common_unique_assets']=len(scene['common_assets']);scene['counts']['owned_floor_masks']=len(floor_records);scene['counts']['actual_remaining_proxy_boxes']=len(scene['boxes']);scene['counts']['remaining_landmark_proxy_boxes']=sum(b['id'].startswith('landmark:') for b in scene['boxes'])
 scene['counts']['supplemental_preview_triangles']=supplemental_count;scene['counts']['supplemental_preview_side_quads']=supplemental_side_count
 output=Path(args.get('out',HERE/'generated/blockout.scene.json'));audit=Path(args.get('audit-out',HERE/'evidence/blockout_source_audit.json'))
 write(output,scene);write(audit,{'source_sha256':source_hash,'counts':scene['counts'],'road_grade_samples':road_audits,'water_surface_count':len(water),'generated_scene_sha256':sha(output)})
 print(json.dumps(scene['counts'],indent=2))
if __name__=='__main__':main()
