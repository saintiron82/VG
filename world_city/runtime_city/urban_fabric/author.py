"""Finite property/land-use authoring through unchanged common master JSON.

No meshing, sampling, city compilation or engine. All XZ edits are declarative;
source IDs remain in provenance and every repurposed reservation is explicit.
"""
from __future__ import annotations
import argparse, copy, hashlib, heapq, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from world_city.runtime_city.checks.placement import (
    _SpatialIndex, convex_polygon_contains, point_in_convex_polygon,
    positive_area_overlap, polygon_area, convex_intersection, convex_difference, road_ribbon, transformed_aabb_xz_m,
)
from world_city.runtime_city.infrastructure.author import PALETTE as INFRA_PALETTE, _river_outline
from world_city.runtime_city.urban_fabric.inspect_compounds import hull, center

HERE = Path(__file__).parent
SCHEMA = 'riverstone.voxel.master.v1'
IDENTITY = [[1,0,0],[0,1,0],[0,0,1]]
PITCH = .25
WALL_LENGTHS = [6.,4.,2.]
HOLDINGS = [
    {'id':'UF_ESTATE_01','district_id':'D04','property_type':'older_stone_manor',
     'main_class':'older_stone_manor','plot_ids':['P0142','P0143','P0144'],
     'roof_material_family':'slate_gray','era':'crossing_fort'},
    {'id':'UF_ESTATE_02','district_id':'D04','property_type':'merchant_palazzo',
     'main_class':'merchant_palazzo','plot_ids':['P0537','P0538','P0539'],
     'roof_material_family':'clay_red','era':'market_rebuilding'},
    {'id':'UF_ESTATE_03','district_id':'D08','property_type':'timber_courtyard_house',
     'main_class':'timber_courtyard_house','plot_ids':['P0435','P0436','P0437'],
     'roof_material_family':'wood_brown','era':'chartered_market'},
]
QUOTAS = {'D03':12,'D04':40,'D05':10,'D06':36,'D07':40,'D08':12,'D10':8,'S01':8}
PROPERTY = {'D03':'market_shop_court','D04':'merchant_shop_warehouse_court','D05':'quay_loading_yard',
            'D06':'craft_workyard','D07':'dense_poor_row_yard','D08':'productive_garden_plot',
            'D10':'monastic_service_court','S01':'cart_garden_holding'}


def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def vec(a,b): return [b[0]-a[0], b[1]-a[1]]
def unit(a,b):
    d=vec(a,b);n=math.hypot(*d)
    if n<1e-8: raise ValueError('degenerate line')
    return [d[0]/n,d[1]/n]
def add(a,b,s=1): return [a[0]+s*b[0],a[1]+s*b[1]]
def mix(a,b,t): return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
def yaw_basis(yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return [[c,0,s],[0,1,0],[-s,0,c]]
def rect(pos,w,d,yaw=0,margin=0):
    return transformed_aabb_xz_m({'min':[-w/2-margin,0,-d/2-margin], 'max':[w/2+margin,1,d/2+margin]},[pos[0],0,pos[1]],yaw)
def frame(poly,yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return [[c*p[0]-s*p[1],s*p[0]+c*p[1]] for p in poly]
def world(local,yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return [c*local[0]+s*local[1],-s*local[0]+c*local[1]]
def module_size(spec):
    kind=spec['kind']; w,d,h = spec.get('width_m',1),spec.get('depth_m',1),spec.get('height_m',1)
    return float(w),float(d),float(h)


def make_master(spec):
    """Small cached source modules only; compile via common.coordinate_planes."""
    spec=copy.deepcopy(spec); k=spec.get('kind');w,d,h=module_size(spec)
    if k not in {'boundary_wall','workbench','loading_platform','timber_stack','garden_bed','market_stall','tree','grave_marker','surface'}:
        raise ValueError('unsupported urban fabric module')
    if not all(math.isfinite(v) and 0<v<=12 for v in (w,d,h)):raise ValueError('module dimensions must be positive and <= 12 m')
    palette=dict(INFRA_PALETTE)
    source=json.loads((ROOT/'voxel_character/common/assets/house/master.json').read_text())
    palette.update({k:v for k,v in source['materials'].items() if k in ('plaster','plaster_light','timber','timber_light','timber_dark','stone','stone_light','stone_dark')})
    ops=[]
    def box(lo,hi,mat,feature):
        if not all(a<b for a,b in zip(lo,hi)):raise ValueError(('degenerate module',spec,lo,hi))
        ops.append({'id':f'op_{len(ops):03d}','part':'solid','action':'paint','material':mat,
                    'shape':{'kind':'box','min':lo,'max':hi},'feature':feature})
    if k=='boundary_wall':
        box([-w/2,-.5,-d/2],[w/2,h-.25,d/2],'stone_dark' if spec.get('rough') else 'stone','footing_and_masonry')
        box([-w/2,h-.25,-d/2],[w/2,h,d/2],'stone_light','flush_coping')
        if spec.get('rough') and w>=4:box([-w/2,h-.5,-d/2],[0,h-.25,d/2],'stone_dark','older_repair_course')
    elif k=='workbench':
        box([-w/2,h-.25,-d/2],[w/2,h,d/2],'timber_light','work_surface')
        for x in (-w/2+.125,w/2-.375):box([x,-.25,-d/2],[x+.25,h-.25,d/2],'timber_dark','bench_support')
    elif k=='loading_platform':
        box([-w/2,-.25,-d/2],[w/2,h,d/2],'stone','loading_stone')
        box([-w/2,h-.25,-d/2],[0,h,d/2],'stone_light','scale_platform')
    elif k=='timber_stack':
        for z in (-d/2,d/2-.25):box([-w/2,0,z],[w/2,h,z+.25],'timber','stacked_work_stock')
        box([-w/2,h-.25,-d/2],[w/2,h,d/2],'timber_light','top_course')
    elif k=='garden_bed':
        box([-w/2,-.25,-d/2],[w/2,.25,d/2],'earth','cultivated_soil')
        for x in (-w/2,w/2-.25):box([x,0,-d/2],[x+.25,.5,d/2],'stone_dark','bed_border')
        for z in (-d/2,d/2-.25):box([-w/2,0,z],[w/2,.5,z+.25],'stone_dark','bed_border')
        for x in (-w/4,w/4):box([x-.125,.25,-d/2+.5],[x+.125,h,d/2-.5],'grass','productive_plant_row')
    elif k=='market_stall':
        for x in (-w/2,w/2-.25):
            for z in (-d/2,d/2-.25):box([x,-.5,z],[x+.25,h-.25,z+.25],'timber','canopy_post')
        box([-w/2,h-.25,-d/2],[w/2,h,d/2],'plaster_light' if spec.get('cloth') else 'timber_light','market_canopy')
        box([-w/2,.75,d/2-.75],[w/2,1.0,d/2],'timber_light','trading_counter')
        for x in (-w/2+.25,0):box([x,1,d/2-.65],[min(x+1,w/2-.25),1.5,d/2-.1],'earth' if spec.get('cloth') else 'grass','wares_in_trays')
    elif k=='tree':
        trunk=.5 if spec.get('fruit') else .75
        box([-trunk/2,-.75,-trunk/2],[trunk/2,h*.7,trunk/2],'timber_dark','rooted_trunk')
        # Three joined broad masses; actual voxel solids, no billboards or particle leaves.
        box([-w*.3,h*.35,-d*.3],[w*.3,h*.86,d*.3],'grass','lower_crown')
        box([-w/2,h*.5,-d/2],[w/2,h*.75,d/2],'grass','broad_crown')
        box([-w*.25,h*.75,-d*.25],[w*.25,h,d*.25],'grass','upper_crown')
    elif k=='grave_marker':
        box([-w/2,0,-d/2],[w/2,.25,d/2],'earth','grave_bed')
        box([-w/4,0,-d/2],[w/4,h,-d/2+.25],'stone_light','headstone')
    else:
        box([-w/2,-.25,-d/2],[w/2,0,d/2],spec.get('material','stone_dark'),'flush_working_surface')
    return {'schema':SCHEMA,'id':'urban_'+k+'_'+digest(spec)[:16],'revision':1,
            'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':palette,
            'components':[{'id':'module','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':ops}],
            'instances':[{'id':'module_0','component':'module'}],
            'metadata':{'authoring':'bounded_common_master_only','spec':spec,
                        'ground_datum_y_m':0,'support_embed_m':.75 if k=='tree' else .5 if k in ('boundary_wall','market_stall') else .25,
                        'palette_sources':['voxel_character/common/assets/house/master.json','world_city/runtime_city/infrastructure/author.py']}}


class Context:
    def __init__(self,plan,scene,removed=(),repurposed=()):
        self.plan,self.scene=plan,scene;self.index=_SpatialIndex(32);self.obstacles={};self.access=[]
        self.repurposed=set(repurposed);self.removed=set(removed)
        def put(k,poly,kind):
            self.obstacles[k]={'polygon':poly,'kind':kind};self.index.add(k,poly)
        for b in plan['building_plans']:
            if b['id'] not in self.removed:put(b['id'],b['footprint_xz_m'],'building')
        n={x['id']:[x['position_m'][0],x['position_m'][2]] for x in plan['road_nodes']}
        for r in plan['roads']:put(r['id'],road_ribbon(n[r['from_node']],n[r['to_node']],r['width_m']+.5),'road')
        for p in plan['plots']:
            if p['id'] not in self.repurposed and p.get('courtyard_xz_m'):put('court:'+p['id'],p['courtyard_xz_m'],'reserved_courtyard')
        river=plan['river_reservation']
        # Segmented river checks conservatively reserve the exact design width.
        for i,(a,b) in enumerate(zip(river['centerline_xz_m'],river['centerline_xz_m'][1:])):
            put('river:'+str(i),road_ribbon(a,b,river['width_candidate_m']+1),'river')
        for f in plan['site_features']:
            if f['id']=='F_MARKET_FOUNTAIN':
                pos=f['position_m'];put(f['id'],rect([pos[0],pos[2]],14,14),'fountain')
        for b in plan['building_plans']:
            if b['id'] in self.removed:continue
            a=b['entrance']['position_xz_m'];z=b['road_access']['connection_xz_m']
            if math.dist(a,z)>.01:self.add_access('source_entrance:'+b['id'],[a,z],2.0,'source_entrance',owner=b['id'])
        self.placed_index=_SpatialIndex(32);self.placed={}
    def add_obstacle(self,key,poly,kind):
        self.obstacles[key]={'polygon':poly,'kind':kind};self.index.add(key,poly)
    def add_access(self,key,path,width,kind,owner=None):
        polys=[road_ribbon(a,b,width) for a,b in zip(path,path[1:]) if math.dist(a,b)>.01]
        rec={'id':key,'polyline_xz_m':path,'width_m':width,'ribbon_polygons_xz_m':polys,'kind':kind,'owner_id':owner}
        self.access.append(rec)
        for i,p in enumerate(polys):self.add_obstacle(key+':'+str(i),p,'access')
        return rec
    def hits(self,poly,ignore=(),allow=(),other_placements=True):
        for key in self.index.candidates(poly):
            ob=self.obstacles[key]
            if key in ignore or ob['kind'] in allow:continue
            if positive_area_overlap(poly,ob['polygon'],.002):return key,ob['kind']
        if other_placements:
            for key in self.placed_index.candidates(poly):
                ob=self.placed[key]
                if ob['blocking'] and positive_area_overlap(poly,ob['polygon'],.002):return key,'urban_fabric'
        return None
    def route(self,start,end,width=1.5,extra_polys=(),max_length=100):
        """Visibility-graph source route with swept-width exact polygon checks."""
        if math.dist(start,end)<.01:return [start,end]
        bounds=rect(center([start,end]),abs(start[0]-end[0])+40,abs(start[1]-end[1])+40)
        obs=[v['polygon'] for k,v in self.obstacles.items() if v['kind']=='building' and k in self.index.candidates(bounds)] + list(extra_polys)
        def clear(a,b):
            if math.dist(a,b)<.01:return False
            poly=road_ribbon(a,b,width)
            return not any(positive_area_overlap(poly,self.obstacles[k]['polygon'],.001) for k in self.index.candidates(poly) if self.obstacles[k]['kind']=='building') and not any(positive_area_overlap(poly,q,.001) for q in extra_polys)
        if clear(start,end):return [start,end] if math.dist(start,end)<=max_length else None
        nodes=[start,end]
        for p in obs:
            c=center(p)
            for v in p:
                u=unit(c,v);nodes.append(add(v,u,width+1))
        edges=defaultdict(list)
        for i,a in enumerate(nodes):
            for j,b in enumerate(nodes[:i]):
                length=math.dist(a,b)
                if length<=max_length and clear(a,b):edges[i].append((j,length));edges[j].append((i,length))
        queue=[(0,0)];best={0:0};prev={}
        while queue:
            cost,i=heapq.heappop(queue)
            if cost>best[i]+1e-8:continue
            if i==1:
                path=[1]
                while path[-1]!=0:path.append(prev[path[-1]])
                return [nodes[v] for v in reversed(path)]
            for j,l in edges[i]:
                nc=cost+l
                if nc<best.get(j,math.inf) and nc<=max_length:best[j]=nc;prev[j]=i;heapq.heappush(queue,(nc,j))
        return None


def fit_rect(region,desired,widths,depths,yaw,obstacles=(),margin=.5):
    local=frame(region,yaw);aim=frame([desired],yaw)[0]
    minx,maxx=min(p[0] for p in local),max(p[0] for p in local)
    minz,maxz=min(p[1] for p in local),max(p[1] for p in local)
    for w in widths:
        for d in depths:
            candidates=[]
            for x in range(math.ceil(minx+w/2+margin),math.floor(maxx-w/2-margin)+1,2):
                for z in range(math.ceil(minz+d/2+margin),math.floor(maxz-d/2-margin)+1,2):
                    pos=world([x,z],yaw);poly=rect(pos,w,d,yaw,margin)
                    if not convex_polygon_contains(region,poly,0):continue
                    if any(positive_area_overlap(poly,p,.001) for p in obstacles):continue
                    candidates.append((math.dist([x,z],aim),pos,rect(pos,w,d,yaw),w,d))
            if candidates:return min(candidates,key=lambda q:q[0])[1:]
    return None


def author_holdings(plan,scene):
    plots={p['id']:p for p in plan['plots']};buildings={b['id']:b for b in plan['building_plans']};inst={i['id']:i for i in scene['instances']}
    properties=[];overrides=[];superseded=[]
    for definition in HOLDINGS:
        ps=[plots[k] for k in definition['plot_ids']];bs=[buildings[p['front_building_id']] for p in ps]
        bs.sort(key=lambda b:polygon_area(b['footprint_xz_m']),reverse=True)
        region=hull([v for p in ps for v in p['footprint_xz_m']]);yaw=inst[bs[0]['id']]['yaw_rad']
        property_rec={**definition,'source_plot_ids':definition['plot_ids'],'source_building_ids':[b['id'] for b in bs],
                      'footprint_xz_m':region,'area_m2':polygon_area(region),'retained_primary_id':bs[0]['id'],
                      'courtyard_policy':'explicit_reparcel_with_reserved_entrance_and_service_routes','building_override_ids':[]}
        occupied=[]
        classes=[definition['main_class'],'stable','servant_lodge']
        main_dims={'older_stone_manor':([18,16],[18,16]),'merchant_palazzo':([16,14],[18,16]),'timber_courtyard_house':([16,14],[16,14])}[definition['property_type']]
        dims=[main_dims,([8,6],[12,10,8]),([6,5],[8,6])]
        for j,b in enumerate(bs):
            fit=fit_rect(region,center(b['footprint_xz_m']),*dims[j],yaw,occupied,1.0 if j==0 else .65)
            if fit is None:
                if j==0:raise ValueError(('no manor hall fit',definition['id']))
                superseded.append({'source_building_id':b['id'],'source_footprint_xz_m':b['footprint_xz_m'],'reason':'consolidated_garden_land','property_id':definition['id'],'replacement_id':None});continue
            pos,poly,w,d=fit;occupied.append(rect(pos,w,d,yaw,1.0))
            front=[math.sin(yaw),math.cos(yaw)];entrance=add(pos,front,d/2)
            oid=b['id']
            override={'id':oid,'source_building_ids':[b['id']],'source_plot_ids':definition['plot_ids'],
                      'retained_primary_id':bs[0]['id'],'property_id':definition['id'],'property_type':definition['property_type'],
                      'assembly_class':classes[j], 'style':('institutional' if classes[j]=='older_stone_manor' else 'merchant' if classes[j]=='merchant_palazzo' else 'old_timber' if classes[j]=='timber_courtyard_house' else 'port' if classes[j]=='stable' else 'garden'),
                      'roof_form':'hip' if classes[j] in ('older_stone_manor','merchant_palazzo') else 'gable','district_id':definition['district_id'],'footprint_xz_m':poly,
                      'position_m':[pos[0],0,pos[1]],'yaw_rad':yaw,'width_m':w,'depth_m':d,
                      'floors':2 if j==0 else 1,'floor_height_m':3.4 if j==0 else 2.8,
                      'roof_pitch_degrees':({'older_stone_manor':50,'merchant_palazzo':48,'timber_courtyard_house':52}[definition['property_type']] if j==0 else 42),
                      'roof_material_family':definition['roof_material_family'] if j==0 else 'wood_brown',
                      'era_id':definition['era'],'entrances':[{'position_xz_m':entrance,'road_connection_xz_m':b['road_access']['connection_xz_m'],'road_id':b['road_access']['road_id']}],
                      'ground_anchor':{'policy':'sample_footprint_corners_on_terrain','support_points_xz_m':poly,'datum_y_m':0,'preserve_xz':True},
                      'provenance':{'source_footprint_xz_m':b['footprint_xz_m'],'reason':'authorized_adjacent_property_consolidation'}}
            overrides.append(override);property_rec['building_override_ids'].append(oid)
            superseded.append({'source_building_id':b['id'],'source_footprint_xz_m':b['footprint_xz_m'],'reason':'replaced_by_property_specific_assembly','property_id':definition['id'],'replacement_id':oid})
        property_rec['land_use']={'roofed_building_m2':sum(polygon_area(o['footprint_xz_m']) for o in overrides if o['property_id']==definition['id']),
                                  'remaining_court_garden_and_access_m2':polygon_area(region)-sum(polygon_area(o['footprint_xz_m']) for o in overrides if o['property_id']==definition['id'])}
        properties.append(property_rec)
    return properties,overrides,superseded


def build_urban_fabric(plan,scene,history):
    """Return placements/specs + explicit building and courtyard replacement API."""
    plan,scene=copy.deepcopy(plan),copy.deepcopy(scene)
    if len({i['id'] for i in scene['instances']})!=len(scene['instances']):raise ValueError('duplicate source instance IDs')
    properties,overrides,superseded=author_holdings(plan,scene)
    plots={p['id']:p for p in plan['plots']};buildings={b['id']:b for b in plan['building_plans']};instances={i['id']:i for i in scene['instances']}
    merged={p for h in properties for p in h['source_plot_ids']};removed={v['source_building_id'] for v in superseded}
    # Candidate selection is spatially concentrated by original district anchor, not random density.
    anchors={d['id']:d['anchor_xz_m'] for d in plan['districts']}
    candidates=[]
    for did,quota in QUOTAS.items():
        ps=[p for p in plan['plots'] if p['district_id']==did and p['id'] not in merged and p.get('courtyard_xz_m') and polygon_area(p['courtyard_xz_m'])>=35]
        ps.sort(key=lambda p:(math.dist(center(p['courtyard_xz_m']),anchors[did]),p['id']))
        candidates.extend(ps[:quota])
    repurposed=merged|{p['id'] for p in candidates}
    ctx=Context(plan,scene,removed,repurposed)
    for o in overrides:ctx.add_obstacle(o['id'],o['footprint_xz_m'],'building')
    for o in overrides:
        ent=o['entrances'][0];end=ent['road_connection_xz_m'];options=[]
        for turn in (0,2,1,3):
            y=o['yaw_rad']+turn*math.pi/2; w,d=(o['depth_m'],o['width_m']) if turn%2 else (o['width_m'],o['depth_m'])
            a=add([o['position_m'][0],o['position_m'][2]],[math.sin(y),math.cos(y)],d/2)
            start=add(a,[math.sin(y),math.cos(y)],1.25)
            path=ctx.route(start,end,1.8,max_length=120)
            if path: options.append((sum(math.dist(x,z) for x,z in zip([a]+path,path)),y,w,d,a,path))
        if not options:raise ValueError(('new property entrance disconnected',o['id']))
        _,y,w,d,a,path=min(options,key=lambda x:x[0]);o.update(yaw_rad=y,width_m=w,depth_m=d);ent['position_xz_m']=a
        path=[a]+path;ctx.add_access('override_entrance:'+o['id'],path,1.8,'property_entrance',owner=o['id'])
        ent['access_polyline_xz_m']=path
        if o['assembly_class']=='stable':
            pos=[o['position_m'][0],o['position_m'][2]];front=[math.sin(o['yaw_rad']),math.cos(o['yaw_rad'])];right=[math.cos(o['yaw_rad']),-math.sin(o['yaw_rad'])]
            mid=add(pos,front,o['depth_m']/2+.8)
            ctx.add_access('frontage:'+o['id'],[add(mid,right,-o['width_m']/2+.4),add(mid,right,o['width_m']/2-.4)],1.4,'shared_frontage_access',owner=o['id'])
    placements=[];specs={};rejections=Counter()
    def place(pid,spec,pos,yaw=0,category=None,property_id=None,region=None,allowed=(),blocking=True,source_ids=()):
        w,d,h=module_size(spec);poly=rect(pos,w,d,yaw);swept=rect(pos,w,d,yaw,.18)
        if region and not convex_polygon_contains(region,swept,.002):rejections['outside_property']+=1;return None
        ignore_kinds=list(allowed)
        if not blocking:ignore_kinds+=['access']
        hit=ctx.hits(swept,allow=ignore_kinds,other_placements=blocking)
        if hit:rejections[hit[1]]+=1;return None
        key='uf_'+spec['kind']+'_'+digest(spec)[:14];specs.setdefault(key,spec)
        p={'id':pid,'asset_key':key,'master_key':key,'position_m':[pos[0],0,pos[1]],'yaw_rad':yaw,'yaw_deg':math.degrees(yaw),
           'transform':{'translation':[pos[0],0,pos[1]],'basis':yaw_basis(yaw)},'category':category or spec['kind'],
           'property_id':property_id,'source_ids':list(source_ids),'requested_pitch_m':PITCH,
           'footprint_xz_m':poly,'conservative_sample_envelope_xz_m':swept,'collision_enabled':blocking,
           'local_bounds':{'min':[-w/2,-.75 if spec['kind']=='tree' else -.5,-d/2],'max':[w/2,h,d/2]},
           'stream_chunk_xz':[math.floor(pos[0]/64),math.floor(pos[1]/64)],
           'ground_anchor':{'policy':'project_y_only_sample_center_and_support_points','datum_y_m':0,'preserve_xz':True,
                            'sample_center_xz_m':pos,'support_points_xz_m':(rect(pos,.5 if spec.get('fruit') else .75,.5 if spec.get('fruit') else .75,yaw) if spec['kind']=='tree' else poly),
                            'support_footprint_kind':'trunk_root' if spec['kind']=='tree' else 'full_module_base',
                            'footing_embed_m':.75 if spec['kind']=='tree' else .5 if spec['kind'] in ('boundary_wall','market_stall') else .25,
                            'maximum_support_height_delta_m':.35 if spec['kind'] in ('surface','garden_bed','market_stall') else .75,
                            'exceedance_action':'re_author_stepped_common_modules_or_omit_do_not_float'},
           'reservation_exception_kinds':list(allowed)}
        placements.append(p);ctx.placed[pid]={'polygon':swept,'blocking':blocking};ctx.placed_index.add(pid,swept);return p
    def wall_line(pid,a,b,height,property_id,region=None,rough=False):
        length=math.dist(a,b)
        if length<2:return []
        u=unit(a,b);yaw=math.atan2(-u[1],u[0]);cursor=.2;out=[]
        while length-cursor>=2.2:
            size=next((s for s in WALL_LENGTHS if s<=length-cursor-.2),None)
            if size is None:break
            pos=add(a,u,cursor+size/2)
            p=place(pid+':'+str(len(out))+':'+str(round(cursor,2)),{'kind':'boundary_wall','width_m':size,'depth_m':.5,'height_m':height,'rough':rough},pos,yaw,'property_boundary',property_id,region)
            if p:out.append(p['id'])
            cursor+=size+.05
        return out
    # Wealth is visible in joined ownership, broad hall + low service masses, garden, and gates.
    for prop in properties:
        region=prop['footprint_xz_m'];c=center(region);ids=[]
        for i,(a,b) in enumerate(zip(region,region[1:]+region[:1])):
            mid=mix(a,b,.5);toward=unit(mid,c);aa=add(a,toward,.6);bb=add(b,toward,.6)
            ids+=wall_line(prop['id']+':wall:'+str(i),aa,bb,1.75 if prop['property_type']=='older_stone_manor' else 1.5,prop['id'],region,prop['property_type']=='older_stone_manor')
        # The empty quarter becomes productive/ornamental land, bounded by explicit access routes.
        minx,maxx=min(x[0] for x in region),max(x[0] for x in region);minz,maxz=min(x[1] for x in region),max(x[1] for x in region)
        count=0
        for x in range(math.ceil(minx/5)*5,math.floor(maxx),5):
            for z in range(math.ceil(minz/7)*7,math.floor(maxz),7):
                if count>=12:break
                p=place(prop['id']+':bed:'+str(count),{'kind':'garden_bed','width_m':2,'depth_m':4,'height_m':.75},[x,z],property_id=prop['id'],region=region,source_ids=prop['source_plot_ids'])
                if p:ids.append(p['id']);count+=1
        prop['placement_ids']=ids;prop['physical_cues']=['property_specific_main_hall','low_service_stable','bounded_garden','gated_masonry_perimeter']
    # Retained plots get functional, partially occupied courts, each with a proven route to its road.
    realized=[]
    for plot in candidates:
        bid=plot['front_building_id'];b=buildings[bid];court=plot['courtyard_xz_m'];region=plot['footprint_xz_m'];c=center(court)
        route=ctx.route(c,b['road_access']['connection_xz_m'],1.4,max_length=110)
        if not route:
            rejections['disconnected_source_court']+=1;continue
        propid='UF_'+plot['id'];did=plot['district_id'];ptype=PROPERTY[did]
        ctx.add_access(propid+':road_link',route,1.4,'court_to_public_road',owner=propid)
        # Two full-width crossing ribbons ensure the working court cannot be sealed by dressing.
        for j in (0,1):
            a=mix(court[j],court[(j+1)%4],.5);z=mix(court[(j+2)%4],court[(j+3)%4],.5)
            u=unit(a,z);ctx.add_access(propid+':cross:'+str(j),[add(a,u,-1.5),add(z,u,1.5)],1.8,'cross_courtyard',owner=propid)
        ids=[]
        front_c=center(b['footprint_xz_m']);skip=min(range(4),key=lambda i:math.dist(mix(court[i],court[(i+1)%4],.5),front_c))
        for i,(a,z) in enumerate(zip(court,court[1:]+court[:1])):
            if i==skip:continue
            u=unit(a,z);mid=mix(a,z,.5)
            for part,aa,zz in [('a',a,add(mid,u,-1.3)),('b',add(mid,u,1.3),z)]:
                ids+=wall_line(propid+':wall:'+str(i)+part,aa,zz,1.25 if did in ('D03','D04','D05') else .75,propid,region,did=='D07')
        # Pairs of purposeful facilities occupy separated corners, never the crossing aisles.
        for n,v in enumerate(court):
            pos=mix(v,c,.35)
            if did in ('D08','D10','S01','D07'):
                spec={'kind':'garden_bed','width_m':2,'depth_m':3,'height_m':.75}
            elif did=='D06':
                spec={'kind':'workbench' if n%2==0 else 'timber_stack','width_m':2.5,'depth_m':1,'height_m':1}
            else:spec={'kind':'loading_platform','width_m':2.5,'depth_m':1.5,'height_m':.5}
            p=place(propid+':facility:'+str(n),spec,pos,instances[bid]['yaw_rad'],ptype,propid,region)
            if p:ids.append(p['id'])
        # A cached flush surface physically differentiates goods/work courts from gardens.
        if did in ('D03','D04','D05','D06'):
            cyaw=instances[bid]['yaw_rad'];lc=frame(court,cyaw)
            for xi,x in enumerate(range(math.ceil(min(v[0] for v in lc))+2,math.floor(max(v[0] for v in lc))-1,4)):
                for zi,z in enumerate(range(math.ceil(min(v[1] for v in lc))+2,math.floor(max(v[1] for v in lc))-1,4)):
                    p=place(propid+f':work_floor:{xi}:{zi}',{'kind':'surface','width_m':4,'depth_m':4,'height_m':.25,'material':'stone_dark' if did=='D06' else 'stone'},world([x,z],cyaw),cyaw,'flush_work_surface',propid,court,blocking=False)
                    if p:ids.append(p['id'])
        if ids:
            record={'id':propid,'property_type':ptype,'district_id':did,'source_plot_ids':[plot['id']],'source_building_ids':[bid],
                    'footprint_xz_m':region,'area_m2':polygon_area(region),'repurposed_courtyard_xz_m':court,
                    'court_area_m2':polygon_area(court),'placement_ids':ids,'access_reservation_ids':[propid+':road_link',propid+':cross:0',propid+':cross:1'],
                    'physical_cues':['broken_boundary_with_access_gaps','functional_corner_facilities','unobstructed_cross_court'],
                    'land_use':{'working_or_garden_court_m2':polygon_area(court)}}
            properties.append(record);realized.append(plot['id'])
    # Bounded old-town replacement: several smaller attached households share party walls.
    poor=[p for p in properties if p['property_type']=='dense_poor_row_yard'][:8]
    for p in poor:
        b=buildings[p['source_building_ids'][0]];i=instances[b['id']];poly=b['footprint_xz_m'];yaw=i['yaw_rad'];local=frame(poly,yaw)
        w=max(v[0] for v in local)-min(v[0] for v in local)-.8;d=max(v[1] for v in local)-min(v[1] for v in local)-.8;pos=center(poly);original_poly=poly;poly=rect(pos,w,d,yaw)
        row={'id':b['id'],'source_building_ids':[b['id']],'source_plot_ids':p['source_plot_ids'],'retained_primary_id':b['id'],
             'property_id':p['id'],'property_type':'dense_poor_row','assembly_class':'poor_row','style':'old_timber','roof_form':'gable','district_id':'D07','footprint_xz_m':poly,
             'position_m':[pos[0],0,pos[1]],'yaw_rad':yaw,'width_m':w,'depth_m':d,'floors':2,'floor_height_m':2.7,'roof_pitch_degrees':48,
             'attached_units':max(2,min(4,int(w/4))),'roof_material_family':'wood_brown','era_id':'chartered_market',
             'entrances':[{'position_xz_m':add(pos,[math.sin(yaw),math.cos(yaw)],d/2),'road_connection_xz_m':b['road_access']['connection_xz_m'],'road_id':b['road_access']['road_id']}],
             'ground_anchor':{'policy':'sample_footprint_corners_on_terrain','support_points_xz_m':poly,'datum_y_m':0,'preserve_xz':True},
             'provenance':{'source_footprint_xz_m':original_poly,'reason':'bounded_small_attached_household_repartition_with_0.4m_road_margin_inset'}}
        newent=row['entrances'][0]['position_xz_m'];oldent=b['entrance']['position_xz_m'];endpoint=b['road_access']['connection_xz_m']
        ctx.add_access('override_entrance:'+b['id'],[newent,oldent,endpoint],1.4,'property_entrance',owner=b['id'])
        row['entrances'][0]['access_polyline_xz_m']=[newent,oldent,endpoint]
        right=[math.cos(yaw),-math.sin(yaw)];mid=add(newent,[math.sin(yaw),math.cos(yaw)],.8)
        ctx.add_access('frontage:'+b['id'],[add(mid,right,-w/2+.4),add(mid,right,w/2-.4)],1.4,'shared_frontage_access',owner=b['id'])
        overrides.append(row);superseded.append({'source_building_id':b['id'],'source_footprint_xz_m':original_poly,'reason':'smaller_attached_household_row','property_id':p['id'],'replacement_id':b['id']})
    # Market groups occupy the edge band only; central civic/fountain space stays clear.
    square=next(f['footprint_xz_m'] for f in plan['site_features'] if f['id']=='F_MARKET_OPEN')
    market_core=[[-48,-38],[58,-38],[58,28],[-48,28]]
    ctx.add_obstacle('market_civic_core',market_core,'protected_market_core')
    for key,a,z in [('east_west',[-60,0],[70,0]),('north_south',[0,-50],[0,40])]:ctx.add_access('market:'+key,[a,z],7,'market_crossing')
    market_groups=[]
    for side in ('north','south','west','east'):
        for block in (0,1):
            coords=[-44,-38,-32,-26] if block==0 else [22,28,34,40]
            if side in ('west','east'):coords=[-30,-24,-18] if block==0 else [14,20,26]
            gid='UF_MARKET_'+side+'_'+str(block);ids=[]
            for j,t in enumerate(coords):
                pos=[t,-44] if side=='north' else [t,34] if side=='south' else [-54,t] if side=='west' else [64,t]
                yaw={'north':0,'south':math.pi,'west':math.pi/2,'east':-math.pi/2}[side]
                q=place(gid+':'+str(j),{'kind':'market_stall','width_m':4,'depth_m':3,'height_m':3,'cloth':block==0},pos,yaw,'market_stall',gid,square)
                if q:ids.append(q['id'])
            market_groups.append({'id':gid,'edge':side,'placement_ids':ids,'function':'bounded_trading_row','servicing':'inward_facing_counter_from_clear_civic_space'})
    # Named institutional grounds use the authored land-use reservations.
    features={f['id']:f for f in plan['site_features']}
    garden=features['F_GARDEN_1']['footprint_xz_m'];grounds=[]
    for name,region,kind,grid in [
        ('UF_MONASTERY_HERBS',garden,'garden_bed',(-445,-405,8,210,247,7)),
        ('UF_CATHEDRAL_CEMETERY',[[299,-376],[325,-376],[325,-338],[299,-338]],'grave_marker',(302,324,5,-372,-340,6)),
        ('UF_CATHEDRAL_GARDEN',[[375,-400],[401,-400],[401,-365],[375,-365]],'garden_bed',(379,398,6,-395,-368,7)),
    ]:
        ids=[];x0,x1,dx,z0,z1,dz=grid
        for x in range(x0,x1,dx):
            for z in range(z0,z1,dz):
                spec={'kind':kind,'width_m':2 if kind=='garden_bed' else 1.25,'depth_m':4 if kind=='garden_bed' else 2.5,'height_m':.75 if kind=='garden_bed' else 1.25}
                q=place(name+':'+str(len(ids)),spec,[x,z],category=kind,property_id=name,region=region)
                if q:ids.append(q['id'])
        grounds.append({'id':name,'function':kind,'footprint_xz_m':region,'area_m2':polygon_area(region),'placement_ids':ids})
    # Productive orchard inside the existing garden reservation, woodland strictly outside walls.
    orchard=features['F_GARDEN_0']['footprint_xz_m'];forest_patches=[
        ('UF_FOREST_NW',[[-750,-640],[-595,-640],[-595,-450],[-750,-450]],10),
        ('UF_FOREST_NE',[[490,-640],[740,-640],[740,-510],[490,-510]],10),
        ('UF_FOREST_E',[[700,-330],[775,-330],[775,-55],[700,-55]],10)]
    vegetation=[]
    for name,region,spacing,fruit in [('UF_NORTH_ORCHARD',orchard,12,True)]+[(a,b,c,False) for a,b,c in forest_patches]:
        ids=[];minx,maxx=min(v[0] for v in region),max(v[0] for v in region);minz,maxz=min(v[1] for v in region),max(v[1] for v in region)
        for row,z in enumerate(range(math.ceil(minz)+5,math.floor(maxz)-4,spacing)):
            for col,x in enumerate(range(math.ceil(minx)+5,math.floor(maxx)-4,spacing)):
                # Ordered orchard rows; coherent grove edges/offsets outside, not random city clutter.
                xx=x if fruit else x+(row%2)*spacing*.35+.45*math.sin(col*.7+row)
                zz=z if fruit else z+.5*math.sin(col*.8)
                edge=min(xx-minx,maxx-xx,zz-minz,maxz-zz)
                core=edge>=20;pos=[xx,zz];w=5 if fruit else 9 if core else 7;h=5 if fruit else 11 if core else 9
                if not fruit and any(point_in_convex_polygon(v,plan['wall_outline_xz_m'],0) for v in rect(pos,w,w)):continue
                q=place(name+':'+str(len(ids)),{'kind':'tree','width_m':w,'depth_m':w,'height_m':h,'fruit':fruit},pos,category='orchard_tree' if fruit else 'outer_woodland_tree',property_id=name,region=region)
                if q:ids.append(q['id'])
        core_poly=rect([(minx+maxx)/2,(minz+maxz)/2],maxx-minx-40,maxz-minz-40) if not fruit else None
        vegetation.append({'id':name,'wooded_core_xz_m':core_poly,'land_use':'productive_orchard' if fruit else 'outside_wall_woodland','footprint_xz_m':region,
                           'area_m2':polygon_area(region),'placement_ids':ids,'planting_pattern':'rows' if fruit else 'staggered_bounded_groves'})
    # All routes now exist. Reconcile early props against later neighboring access
    # ribbons and restore every unused candidate court reservation.
    repurposed=merged|set(realized)
    finalctx=Context(plan,scene,{s['source_building_id'] for s in superseded},repurposed)
    for o in overrides:finalctx.add_obstacle(o['id'],o['footprint_xz_m'],'building')
    for a in ctx.access:
        for n,q in enumerate(a['ribbon_polygons_xz_m']):finalctx.add_obstacle(a['id']+':final:'+str(n),q,'access')
    finalctx.add_obstacle('market_civic_core',market_core,'protected_market_core')
    kept=[]
    for p in placements:
        allow=[] if p['collision_enabled'] else ['access']
        if finalctx.hits(p['conservative_sample_envelope_xz_m'],allow=allow,other_placements=False):
            rejections['final_all_access_or_restored_court_preflight']+=1;continue
        kept.append(p)
    placements=kept;kept_ids={p['id'] for p in placements}
    for group in properties+market_groups+grounds+vegetation:
        group['placement_ids']=[p for p in group.get('placement_ids',[]) if p in kept_ids]
    by_id={p['id']:p for p in placements}
    for v in vegetation:
        polys=[by_id[k]['footprint_xz_m'] for k in v['placement_ids']]
        crown_area=sum(polygon_area(p) for p in polys);v['projected_crown_area_m2']=round(crown_area,3);v['canopy_fraction']=round(crown_area/v['area_m2'],5)
        if v['wooded_core_xz_m']:
            cp=v['wooded_core_xz_m'];ca=sum(polygon_area(convex_intersection(p,cp)) for p in polys)
            v['wooded_core_area_m2']=polygon_area(cp);v['wooded_core_crown_area_m2']=round(ca,3);v['wooded_core_canopy_fraction']=round(ca/polygon_area(cp),5)
    active_keys={p['asset_key'] for p in placements};specs={k:v for k,v in specs.items() if k in active_keys}
    result={'schema':'riverstone.city.urban_fabric.v1','revision':'property_fabric_r2_source','source_plan_id':plan['id'],
            'sources':{'plan_sha256':digest(plan),'scene_instance_xz_sha256':digest([{k:i[k] for k in ('id','position_m','yaw_rad','source_footprint_xz_m')} for i in scene['instances']]),'history_sha256':digest(history)},
            'placements':placements,'master_specs':specs,'properties':properties,'building_override_specs':overrides,
            'source_building_supersessions':superseded,'repurposed_courtyard_plot_ids':sorted(repurposed),
            'access_reservations':ctx.access,'market_groups':market_groups,'market_protected_core_xz_m':market_core,
            'institutional_grounds':grounds,'vegetation_land_use':vegetation,
            'rejection_counts':dict(rejections),'source_geometry_policy':'roads_and_active_entrance_clearance_immutable; explicit_property_reparcel_manifest_for_buildings_and_courts',
            'integration_contract':{'remove_source_scene_instance_ids':sorted({s['source_building_id'] for s in superseded}),
                'replacement_buildings_api':'building_override_specs require property-specific ordinary assembly by city orchestrator',
                'module_master_api':'make_master(master_specs[asset_key]) -> unchanged riverstone.voxel.master.v1',
                'y_projection':'replace placement position_m[1] and transform.translation[1] together; source XZ never changes',
                'terrain_support':'sample ground_anchor points; re-author/omit on support delta exceedance; do not scale, float, or use global flat plane'},
            'limitations':['Source-only deliverable; no compiled meshes or visual approval claimed.',
                'Access is checked as swept XZ ribbons, not a physics/navmesh or cart turning simulation.',
                'Terrain Y remains an explicit projection interface pending topography integration.',
                'Property-specific main/service/poor-row buildings are override specs, not duplicate rendered houses.']}
    for override in result['building_override_specs']:
        override['construction_era']=override['era_id']
    result['checks']=validate_urban_fabric(result,plan,scene)
    result['coverage']=coverage(result)
    return result


def coverage(data):
    union_pieces=[]
    for prop in data['properties']:
        pieces=[prop['footprint_xz_m']]
        for old in union_pieces:
            pieces=[q for p in pieces for q in (convex_difference(p,old) if positive_area_overlap(p,old) else [p])]
            if not pieces:break
        union_pieces.extend(pieces)
    return {'source_placements':len(data['placements']),'cached_module_specs':len(data['master_specs']),
            'property_count':len(data['properties']),'property_types':dict(Counter(p['property_type'] for p in data['properties'])),
            'building_override_count':len(data['building_override_specs']),'source_buildings_superseded':len(data['source_building_supersessions']),
            'repurposed_plot_courtyards':len(data['repurposed_courtyard_plot_ids']),
            'placement_categories':dict(Counter(p['category'] for p in data['placements'])),
            'property_record_area_sum_m2':round(sum(p['area_m2'] for p in data['properties']),2),
            'property_area_union_m2':round(sum(polygon_area(p) for p in union_pieces),2),
            'physical_blocking_footprint_area_m2':round(sum(polygon_area(p['footprint_xz_m']) for p in data['placements'] if p['collision_enabled']),2),
            'flush_working_surface_area_m2':round(sum(polygon_area(p['footprint_xz_m']) for p in data['placements'] if p['category']=='flush_work_surface'),2),
            'institutional_grounds_m2':round(sum(p['area_m2'] for p in data['institutional_grounds']),2),
            'orchard_woodland_m2':round(sum(p['area_m2'] for p in data['vegetation_land_use']),2),
            'market_stalls':sum(len(g['placement_ids']) for g in data['market_groups']),
            'market_civic_core_m2':polygon_area(data['market_protected_core_xz_m']),
            'access_reservations':len(data['access_reservations'])}


def validate_urban_fabric(data,plan,scene):
    """Independent reconstruction of immutable reservations and physical overlaps."""
    errors=[];removed={s['source_building_id'] for s in data['source_building_supersessions']}
    ctx=Context(plan,scene,removed,data['repurposed_courtyard_plot_ids'])
    overrides=data['building_override_specs'];source={b['id']:b for b in plan['building_plans']}
    props={p['id']:p for p in data['properties']}
    # Building replacement envelope + explicit provenance, never silently lose an old ID.
    for o in overrides:
        if not all(s in source for s in o['source_building_ids']):errors.append({'id':o['id'],'check':'unknown_source_building'})
        allow=['access'] if o['assembly_class']=='poor_row' else []
        hit=ctx.hits(o['footprint_xz_m'],allow=allow,other_placements=False)
        if hit:errors.append({'id':o['id'],'check':'building_override_intersection','target':hit})
        ctx.add_obstacle(o['id'],o['footprint_xz_m'],'building')
    # Reuse exact saved accesses, including source entrances; strip auto-created duplicates.
    for a in data['access_reservations']:
        for i,p in enumerate(a['ribbon_polygons_xz_m']):ctx.add_obstacle(a['id']+':saved:'+str(i),p,'access')
        if a['kind'] in ('court_to_public_road','property_entrance','shared_frontage_access'):
            for poly in a['ribbon_polygons_xz_m']:
                for key in ctx.index.candidates(poly):
                    ob=ctx.obstacles[key]
                    if ob['kind']=='building' and positive_area_overlap(poly,ob['polygon'],.003):
                        errors.append({'id':a['id'],'check':'access_intersects_building','target':key});break
    ctx.add_obstacle('market_civic_core',data['market_protected_core_xz_m'],'protected_market_core')
    ids=set();supported=set(data['master_specs'])
    for p in data['placements']:
        if p['id'] in ids:errors.append({'id':p['id'],'check':'duplicate_id'})
        ids.add(p['id'])
        if p['asset_key'] not in supported:errors.append({'id':p['id'],'check':'missing_master_spec'})
        spec=data['master_specs'].get(p['asset_key'],{});w,d,h=module_size(spec)
        expected=rect([p['position_m'][0],p['position_m'][2]],w,d,p['yaw_rad'],.18)
        if digest(expected)!=digest(p['conservative_sample_envelope_xz_m']):errors.append({'id':p['id'],'check':'stale_sample_envelope'})
        allowed=p.get('reservation_exception_kinds',[])+([] if p['collision_enabled'] else ['access'])
        hit=ctx.hits(expected,allow=allowed,other_placements=p['collision_enabled'])
        if hit:errors.append({'id':p['id'],'check':'reserved_geometry_intersection','target':hit})
        if not p.get('ground_anchor',{}).get('preserve_xz'):errors.append({'id':p['id'],'check':'missing_terrain_anchor'})
        if p['category']=='outer_woodland_tree' and any(point_in_convex_polygon(v,plan['wall_outline_xz_m'],0) for v in expected):errors.append({'id':p['id'],'check':'forest_inside_walls'})
        ctx.placed[p['id']]={'polygon':expected,'blocking':p['collision_enabled']};ctx.placed_index.add(p['id'],expected)
    return {'valid':not errors,'errors':errors,'checks':{
        'roads_and_source_buildings_rebuilt_from_authoritative_plan':True,'reserved_unreparcelled_courtyard_count':sum(bool(p.get('courtyard_xz_m')) and p['id'] not in data['repurposed_courtyard_plot_ids'] for p in plan['plots']),
        'authored_sample_guard_m':.18,'positive_area_overlap_tolerance_m':.002,'active_source_entrance_width_m':2,
        'cross_court_width_m':1.8,'source_building_ids_auditable':True,'source_scene_mutated':False,
        'building_override_realization':'external_ordinary_assembly_required','actual_navigation_simulated':False}}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=HERE/'generated/urban_fabric.json');args=ap.parse_args()
    plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text());scene=json.loads((ROOT/'world_city/runtime_city/generated/r1/scene.json').read_text());history_path=ROOT/'world_city/runtime_city/revisions/r2/city_history.r2.candidate.json';history=json.loads((history_path if history_path.exists() else ROOT/'world_city/city_history.json').read_text())
    data=build_urban_fabric(plan,scene,history);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    (args.output.parent/'coverage.json').write_text(json.dumps({'coverage':data['coverage'],'checks':data['checks'],'rejections':data['rejection_counts']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'coverage':data['coverage'],'checks':data['checks'],'rejections':data['rejection_counts']},ensure_ascii=False,indent=2))
    if not data['checks']['valid']:raise SystemExit(1)
if __name__=='__main__':main()
