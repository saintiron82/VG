"""Bounded original common replay and exact cap-column evidence. No cuts."""
import hashlib,importlib.util,json,math,pathlib,resource,sys,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
spec=importlib.util.spec_from_file_location('inspect_lane_contacts',H/'inspect_contacts.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(p,v):
    with p.open('x') as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
    contact=read(H/'contact_polygons.json');out=[];(H/'baseline').mkdir(exist_ok=True)
    for record in contact['records']:
        pid=record['property_id'];mp=ROOT/contact['sources'][pid+'_master']['path'];rp=ROOT/contact['sources'][pid+'_render']['path']
        assert sha(mp)==contact['sources'][pid+'_master']['sha256'] and sha(rp)==contact['sources'][pid+'_render']['sha256']
        master=read(mp);budget=candidate_budget(master);assert budget['within_candidate_cap']
        start=time.monotonic();compiled=coordinate_planes.compile_master(master,{'pitch':.5},max_candidate_cells=300000,max_output_cells=100000);render=render_data.make_render_data(compiled);old=read(rp)
        assert compiled['valid'] and render['groups']==old['groups'] and render['cell_count']==old['cell_count'] and render['bounds']==old['bounds']
        write(H/'baseline'/(pid+'.compiled.json'),compiled)
        origin=record['placement']['position_m'];columns={}
        for face in record['contacts']:
            poly=face['native_face_polygon_xz_m'];bb=a.bounds(poly)
            for ix in range(round((bb[0]-origin[0])*2),round((bb[2]-origin[0])*2)):
                for iz in range(round((bb[1]-origin[2])*2),round((bb[3]-origin[2])*2)):
                    x=origin[0]+ix*.5;z=origin[2]+iz*.5;square=[[x,z],[x+.5,z],[x+.5,z+.5],[x,z+.5]]
                    hits=a.disjoint_intersections(square,record['traffic_polygons_xz_m'])
                    if hits:columns[(ix,iz)]={'grid_xz':[ix,iz],'polygon_xz_m':square,'traffic_clip_polygons_xz_m':hits,'traffic_area_m2':sum(a.geo.polygon_area(q) for q in hits),'cells':[]}
        for cell in compiled['cells']:
            key=(cell[0],cell[2])
            if key in columns:columns[key]['cells'].append({'grid_xyz':cell[:3],'instance':cell[3],'part':cell[4],'material':cell[5],'source_feature':cell[6],
                                                         'world_y_interval_m':[origin[1]+cell[1]*.5,origin[1]+(cell[1]+1)*.5]})
        rows=list(columns.values());features=sorted({c['source_feature'] for r in rows for c in r['cells']})
        outside=sum(.25-r['traffic_area_m2'] for r in rows)
        result={'property_id':pid,'master':ref(mp),'original_render':ref(rp),'original_cell_snapshot':ref(H/'baseline'/(pid+'.compiled.json')),
                'original_render_groups_exactly_replayed':True,'candidate_visits':compiled['candidate_cells'],'occupied_cells':len(compiled['cells']),
                'wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'candidate_columns':rows,'column_count':len(rows),'entire_column_footprint_area_m2':len(rows)*.25,
                'traffic_intersection_area_m2':sum(r['traffic_area_m2'] for r in rows),'outside_traffic_cell_fraction_area_m2':outside,
                'features_in_contact_columns':features,'non_access_skin_features':[f for f in features if not f.startswith('r1_access_skin_')],
                'cut_performed':False,'pending':'Exact road-plane/domain binding determines which cap cells protrude and which buried bearing cells can remain.'}
        out.append(result);print(json.dumps({k:result[k] for k in ['property_id','candidate_visits','occupied_cells','wall_seconds','column_count','outside_traffic_cell_fraction_area_m2','non_access_skin_features']}),flush=True)
    write(H/'baseline/cap_columns.json',{'schema':'riverstone.public_lane_cap_columns.v1','contact_source':ref(H/'contact_polygons.json'),'records':out,
          'policy':'Whole sampled cell cuts may extend outside the traffic union. This evidence explicitly reports that finite fraction; no extension or cut is accepted here.'})
    print(json.dumps({'report':ref(H/'baseline/cap_columns.json')}))
if __name__=='__main__':main()
