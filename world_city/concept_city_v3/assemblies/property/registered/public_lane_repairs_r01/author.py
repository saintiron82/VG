"""Append bounded, feature-selected common cuts to preserved estate masters."""
import copy,hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(p,v):
    raw=json.dumps(v,separators=(',',':'),allow_nan=False)+'\n'
    if p.exists():
        assert p.read_text()==raw, 'Refusing to overwrite different candidate bytes: '+str(p)
    else:p.write_text(raw)
def main():
    (H/'sources').mkdir(exist_ok=True);cols=read(H/'baseline/cap_columns.json');records=[]
    for record in cols['records']:
        pid=record['property_id'];mp=ROOT/record['master']['path'];cp=ROOT/record['original_cell_snapshot']['path']
        assert sha(mp)==record['master']['sha256'] and sha(cp)==record['original_cell_snapshot']['sha256']
        original=read(mp);compiled=read(cp);master=copy.deepcopy(original);ops=master['components'][0]['operations'];count=len(ops)
        expected=[]
        for column in record['candidate_columns']:
            cells=column['cells'];assert cells and all(c['source_feature'].startswith('r1_access_skin_') for c in cells)
            features=sorted({c['source_feature'] for c in cells});ix,iz=column['grid_xz'];ys=[c['grid_xyz'][1] for c in cells]
            ops.append({'id':f'public_lane_access_skin_cut_{pid}_{ix}_{iz}','part':'solid','action':'cut',
                        'shape':{'kind':'box','min':[ix*.5,min(ys)*.5,iz*.5],'max':[(ix+1)*.5,(max(ys)+1)*.5,(iz+1)*.5]},
                        'selector':{'feature':features}})
            expected.extend(c['grid_xyz'] for c in cells)
        assert len(expected)==len({tuple(c) for c in expected})
        key='registered_estate_public_lane_r1_'+pid.lower()+'_'+canonical({'original':record['master'],'cut_operations':ops[count:]})[:16]
        master['id']=key;master['revision']=int(master.get('revision',0))+1
        master.setdefault('metadata',{})['public_lane_cap_repair']={'original_master':record['master'],'original_render':record['original_render'],
            'column_evidence':ref(H/'baseline/cap_columns.json'),'only_appended_cut_operations':len(ops)-count,
            'expected_removed_cell_count':len(expected),'protected_features':'Every feature except the explicit r1_access_skin IDs selected per exact column.',
            'activation':'Held pending terrain restoration, native-difference proof and unchanged-controller replay.'}
        budget=candidate_budget(master);assert budget['within_candidate_cap']
        path=H/'sources'/(pid+'.master.json');write(path,master)
        records.append({'property_id':pid,'asset_key':key,'source_master':ref(path),'original_master':record['master'],
                        'original_render':record['original_render'],'original_cell_snapshot':record['original_cell_snapshot'],
                        'original_operation_count':count,'appended_cut_count':len(ops)-count,'expected_removed_grid_cells':sorted(expected),
                        'expected_retained_cell_count':compiled['cell_count']-len(expected) if 'cell_count' in compiled else len(compiled['cells'])-len(expected),
                        'candidate_budget':budget,'preserve_pose':True,'preserve_sampling_pitch_m':.5,
                        'entire_column_footprint_area_m2':record['entire_column_footprint_area_m2'],
                        'outside_traffic_cell_fraction_area_m2':record['outside_traffic_cell_fraction_area_m2']})
    write(H/'source_candidates.json',{'schema':'riverstone.estate_public_lane_native_cut_sources.v1','status':'SOURCE_CANDIDATE_NOT_COMPILED_OR_ACTIVATED',
          'contact_source':ref(H/'contact_polygons.json'),'column_source':ref(H/'baseline/cap_columns.json'),'records':records,
          'required_terrain_binding':'Finite restoration must cover exact removed cap footprints, retain original outside-traffic native top heights and match surviving public planes. No source hole may be hidden by a collision-only support.',
          'original_native_cache_files_changed':False,'controller_changed':False})
    print(json.dumps({'sources':ref(H/'source_candidates.json'),'records':[{'property_id':r['property_id'],'removed_cells':len(r['expected_removed_grid_cells']),'candidate_visits':r['candidate_budget']['exact_candidate_visits_without_cell_sampling']} for r in records]}))
if __name__=='__main__':main()
