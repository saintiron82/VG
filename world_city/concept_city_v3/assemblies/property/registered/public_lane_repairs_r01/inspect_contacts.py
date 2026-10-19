"""Finite original-traffic/native-cap intersections before any source cuts."""
import hashlib,json,math,pathlib,sys
sys.dont_write_bytecode=True
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if (p/'voxel_character').is_dir())
sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r01_ownership import author as ownership
from world_city.runtime_city.checks import placement as geo
H=pathlib.Path(__file__).resolve().parent;CITY=ROOT/'world_city/concept_city_v3'
PACK=CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json';PLAN=CITY/'registered_source/plan.json'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def clean(poly):
    out=[]
    for v in poly:
        if not out or math.dist(v,out[-1])>1e-9:out.append(v)
    if len(out)>1 and math.dist(out[0],out[-1])<=1e-9:out.pop()
    return out if len(out)>=3 and geo.polygon_area(out)>1e-10 else []
def bounds(poly):return [min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)]
def overlap(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
def disjoint_intersections(poly,masks):
    remaining=[poly];hits=[]
    for mask in masks:
        mb=bounds(mask);next_remaining=[]
        for p in remaining:
            if not overlap(bounds(p),mb):next_remaining.append(p);continue
            hit=clean(geo.convex_intersection(p,mask))
            if not hit:next_remaining.append(p);continue
            hits.append(hit)
            next_remaining.extend(c for q in geo.convex_difference(p,mask) if (c:=clean(q)))
        remaining=next_remaining
        if not remaining:break
    return hits
def main():
    pack=read(PACK);plan=read(PLAN);roads={r['id']:r for r in plan['roads']};rows=[];sources={'pack':ref(PACK),'plan':ref(PLAN),'finite_corridor_implementation':ref(pathlib.Path(ownership.__file__))}
    for property_id,road_id in [('E1','NOBLE_RISE'),('E2','NORTH_BACK_LANE')]:
        placement=next(p for p in pack['placements'] if p['id']==property_id+':registered_r1:infrastructure');asset=pack['asset_manifest'][placement['asset_key']]
        rp=pathlib.Path(asset['compiled_asset_ref']);mp=pathlib.Path(asset['master_path']);assert sha(rp)==asset['render_sha256'] and sha(mp)==asset['master_file_sha256']
        sources[property_id+'_render']=ref(rp);sources[property_id+'_master']=ref(mp)
        render=read(rp);road=roads[road_id];masks=[clean(p) for p in ownership.corridor(road['polyline_xz_m'],road['width_m'])];masks=[p for p in masks if p]
        origin=placement['position_m'];assert placement.get('yaw_rad',0)==0
        contacts=[]
        for gi,g in enumerate(render['groups']):
            for qi,q in enumerate(g['quads']):
                a,b,c=q[:3];normal_y=(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
                if normal_y<=1e-10:continue
                poly=[[v[0]+origin[0],v[2]+origin[2]] for v in q];hits=disjoint_intersections(poly,masks)
                if not hits:continue
                y=q[0][1]+origin[1]
                contacts.append({'native_face_key':{'group_index':gi,'quad_index':qi},'material':g['material'],'top_y_m':y,
                                 'native_quad_xyz_m':[[v[j]+origin[j] for j in range(3)] for v in q],
                                 'native_face_polygon_xz_m':poly,'actual_traffic_contact_polygons_xz_m':hits,
                                 'traffic_overlap_area_m2':sum(geo.polygon_area(p) for p in hits),
                                 'classification':'PRIVATE_FLOOR_OR_ACCESS_CAP_CANDIDATE' if y<=origin[1]+1e-7 else 'RAISED_NATIVE_SOLID_REQUIRES_WALL_GATE_REVIEW'})
        rows.append({'property_id':property_id,'native_instance_id':placement['id'],'placement':{k:placement[k] for k in ['id','asset_key','position_m','yaw_rad']},
                     'canonical_public_road_id':road_id,'source_width_m':road['width_m'],'source_polyline_xz_m':road['polyline_xz_m'],
                     'traffic_polygons_xz_m':masks,'shoulder_included':False,'native_floor_y_m':origin[1],'contacts':contacts,
                     'total_top_projection_traffic_overlap_m2':sum(c['traffic_overlap_area_m2'] for c in contacts),
                     'protected_raised_solid_contact_count':sum(c['classification'].startswith('RAISED') for c in contacts)})
    write(H/'contact_polygons.json',{'schema':'riverstone.estate_public_lane_native_contacts.v1','status':'FINITE_CONTACTS_PENDING_SHARED_ACTUAL_PROFILE_AND_CUT_APPROVAL','sources':sources,'records':rows,
          'constraints':['Traffic uses the original exact strip plus the existing circumscribed finite round joins; 2 m shoulders are excluded.',
                         'No native source/cached mesh has been altered. Raised native wall/gate contacts are not approved for deletion.',
                         'Terrain must bind each finite cut to preserved actual scene planes or explicitly report absent support; no nearest-road analytic resampling.']})
    print(json.dumps({'report':ref(H/'contact_polygons.json'),'contacts':[{'property':r['property_id'],'faces':len(r['contacts']),'area_m2':r['total_top_projection_traffic_overlap_m2'],'raised_contacts':r['protected_raised_solid_contact_count']} for r in rows]}))
if __name__=='__main__':main()
