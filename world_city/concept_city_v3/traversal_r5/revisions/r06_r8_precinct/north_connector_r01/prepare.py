"""Actual composed north-approach regression, original controller and common loader."""
import copy,hashlib,importlib.util,json,math,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5'
spec=importlib.util.spec_from_file_location('network_source',H.parent/'network_batch_r01/prepare_batch.py');n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);b=n.b
SCENE=CITY/'evidence/r8_north_water_r01/scene.json';SHA='71b5ea925945fbc6ca9427fcd5f18f8f482befe310f3506eb6eb5107f43b0d2b'
NORTH=CITY/'assemblies/waterworks/registered_bridge/north_approach_r03'
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':b.sha(p)}
def write(p,v):
    with p.open('x') as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
    assert b.sha(SCENE)==SHA;scene=b.read(SCENE);profile=b.read(NORTH/'profile.json');prior=b.read(H.parent/'network_batch_r01/prepared_runtime.json')
    for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(H/name).write_bytes((BASE/name).read_bytes())
    (H/'geometry').mkdir(exist_ok=True);(H/'evidence').mkdir(exist_ok=True)
    frame={'transform':profile['bridge_frame'],'position_m':profile['bridge_frame']['translation']}
    def world(p):return b.transform(p,frame)
    def local(p):
        t=profile['bridge_frame'];v=[p[i]-t['translation'][i] for i in range(3)]
        return [sum(t['basis'][j][i]*v[j] for j in range(3)) for i in range(3)]
    routes=[]
    def pair(id,points,scope,group=None,**kw):
        r=b.route(id,points,['MAIN_BRIDGE'],scope);r.update(group=group or id,**kw);routes.append(r)
        q=copy.deepcopy(r);q.update(id=id+'_REVERSE',points=list(reversed(points)));routes.append(q)
    knots=profile['cross_section_knots_local_z_m']
    def section_at(section,z):
        for i,(a,c) in enumerate(zip(knots,knots[1:])):
            if a-1e-10<=z<=c+1e-10:
                f=(z-a)/(c-a);return [section[i][j]+f*(section[i+1][j]-section[i][j]) for j in range(3)]
        raise ValueError('Lane outside exact section')
    for lane in [-1.5,0.,1.5]:
        local_points=[section_at(s,lane) for s in profile['sections_local_xyz_m']]
        # Actual old road and native fixed approach are each entered by 0.5m.
        local_points=[[local_points[0][0]-.5,local_points[0][1],lane]]+local_points+[[local_points[-1][0]+.5,local_points[-1][1],lane]]
        pair('NORTH_LANE_'+str(lane),[world(p) for p in local_points],'Measured profile lane through actual main gate, old road seam and actual fixed-deck seam.',group='NORTH_CONNECTOR',source_width_m=6.)
    for id in ['AUTHORITATIVE_SOUTH_TERMINAL_COUNTRY','BRIDGE_CLOSED_LEAF_HINGE']:
        old=next(r for r in prior['routes'] if r['id']==id);pair(id,old['points'],old['test_scope'],group=id,source_width_m=6.)
    # The previously valid approach from the seated leaf side reaches each barrier directly.
    for side in [-1,1]:
        r=b.route('NEGATIVE_SECURED_BARRIER_'+str(side),[world([side*11,4.,0]),world([side*15,3.75,0])],['MAIN_BRIDGE'],'Actual ROAD_SECURED native half-panels; standing on the leaf side avoids fixed-deck approach risers.')
        r.update(group='BARRIER_SECURED',bridge_state='ROAD_SECURED',expected_failure='blocked',expected_contact_id=f'BRIDGE_STATE:ROAD_SECURED:BARRIER_{side}_-1');routes.append(r)
    gate=next(p for p in scene['common_instances'] if p['id']==profile['main_gate_id'])
    for side in [-1,1]:
        start=b.transform([0,2.5-gate['position_m'][1],0],gate);target=b.transform([side*4.4,2.5-gate['position_m'][1],0],gate)
        r=b.route('NEGATIVE_GATE_JAMB_'+str(side),[start,target],['MAIN_BRIDGE'],'Walk from the actual clear throat toward the actual native jamb; no synthetic floor under the side edge.')
        r.update(group='NORTH_CONNECTOR',expected_failure='blocked',expected_contact_id=profile['main_gate_id']);routes.append(r)
    for side in [-1,1]:
        r=b.route('NEGATIVE_NORTH_CAUSEWAY_EDGE_'+str(side),[world([-78,2.05,0]),world([-78,2.05,side*8])],['MAIN_BRIDGE'],'Leave the finite causeway lateral edge; no support plane outside the actual native/profile bounds.')
        r.update(group='NORTH_CONNECTOR',expected_failure='ground_lost',minimum_allowed_feet_y_m=1.45);routes.append(r)
    for id in ['NEGATIVE_UNBRIDGED_RIVER','NEGATIVE_ACTUAL_SOLID_WALL']:
        r=copy.deepcopy(next(r for r in prior['routes'] if r['id']==id));r['group']='isolated_control';routes.append(r)
    assert len(routes)==18
    allpoints=[p for r in routes if r['group']!='isolated_control' for p in r['points']];globalbox=b.bounds(allpoints);globalbox=[globalbox[0]-7,globalbox[1]-7,globalbox[2]+7,globalbox[3]+7]
    scene_tris=[]
    for mat,vs in scene['surfaces'].items():
        if mat=='water':continue
        for i in range(0,len(vs),3):
            tri=vs[i:i+3];bb=b.bounds(tri)
            if b.overlaps(bb,globalbox):scene_tris.append((mat,i//3,tri,bb))
    contracts=scene['collision_contracts'];disabled={pid for c in contracts for pid in c.get('disable_native_mesh_collider_ids',[])}
    bound_cache={}
    def asset_bounds(key):
        if key not in bound_cache:
            a=scene['common_assets'][key]
            if a.get('bounds'):bound_cache[key]=a['bounds']
            else:
                path=ROOT/a['render_path'];assert b.sha(path)==a['render_sha256'];bound_cache[key]=b.read(path)['bounds']
        return bound_cache[key]
    native=[(p,b.instance_bounds(p,asset_bounds(p['asset_key']))) for p in scene['common_instances']]
    movable={}
    for state in ['ROAD_OPEN','ROAD_SECURED']:
        movable[state]=[]
        for p in scene['bridge_mechanism']['states'][state]['movable_placements']:
            transform=n.compose(scene['bridge_mechanism']['bridge_to_world'],p['transform_bridge_local'])
            q={'id':'BRIDGE_STATE:'+state+':'+p['id'],'asset_key':p['asset_key'],'transform':transform,'position_m':transform['translation'],'category':'actual_native_bridge_'+state,'collision_layer':3}
            movable[state].append((q,b.instance_bounds(q,asset_bounds(q['asset_key']))))
    assets={};placements={};buildings={};groups={};audits=[]
    for r in routes:
        if r['group']!='isolated_control':groups.setdefault(r['group'],[]).append(r)
    for group,rs in groups.items():
        boxes=[box for r in rs for box in n.boxline(r['points'])];state=rs[0].get('bridge_state','ROAD_OPEN')
        selected=[t for t in scene_tris if any(b.overlaps(t[3],box) for box in boxes)]
        key='SCENE:NORTH_REPLAY:'+group;path=H/'geometry'/(group+'.json');write(path,{'scene_sha256':SHA,'source_face_indices':[[t[0],t[1]] for t in selected],'triangles':[[t[2][0],t[2][2],t[2][1]] for t in selected],'whole_triangles_only':True})
        assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':b.sha(path),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'actual_north_scene_surface','collision_layer':1};ids=[key];boxids=[]
        for p,bb in native+movable[state]:
            if p['id'] in disabled or not any(b.overlaps(bb,box) for box in boxes):continue
            a=scene['common_assets'][p['asset_key']];assert b.sha(ROOT/a['render_path'])==a['render_sha256']
            assets[p['asset_key']]={'render_path':a['render_path'],'render_sha256':a['render_sha256']};placements[p['id']]=dict(p,category=p.get('category','actual_native_common_mesh'),collision_layer=3,yaw_deg=math.degrees(p.get('yaw_rad',0)));ids.append(p['id'])
        for c in contracts:
            triangles=[t for t in c['add_triangles_world_xyz_m'] if any(b.overlaps(b.bounds(t),box) for box in boxes)]
            if not triangles:continue
            key='CONTRACT:'+c['id']+':'+group;path=H/'geometry'/('contract_'+c['id']+'_'+group+'.json');write(path,{'contract_id':c['id'],'triangles':triangles,'direct_godot_collision_winding':True})
            assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':b.sha(path),'collision_format':'source_grade_proxy_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'declared_exact_collision_contract','collision_layer':3};ids.append(key)
        for p in scene['boxes']:
            bounds={'min':[-v/2 for v in p['size_m']],'max':[v/2 for v in p['size_m']]}
            if any(b.overlaps(b.instance_bounds(p,bounds),box) for box in boxes):buildings[p['id']]={'id':p['id'],'position_m':p['position_m'],'yaw_rad':p.get('yaw_rad',0),'boxes':[bounds],'collision_layer':3};boxids.append(p['id'])
        for r in rs:r.update(placement_ids=ids,building_ids=boxids,bridge_state=state)
        audits.append({'group':group,'native_ids':[pid for pid in ids if not pid.startswith(('SCENE:','CONTRACT:'))],'scene_triangles':len(selected),'contract_ids':[pid for pid in ids if pid.startswith('CONTRACT:')],'box_ids':boxids,'bridge_state':state})
    for r in routes:
        if r['group']!='isolated_control':continue
        for pid in r['placement_ids']:
            p=prior['placements'][pid];assets[p['asset_key']]=prior['assets'][p['asset_key']];placements[pid]=p
    sources={'scene':ref(SCENE),'north_profile':ref(NORTH/'profile.json'),'north_contract':ref(NORTH/'collision_contract.json'),'north_native_pack':ref(NORTH/'resolved_placements.json'),
             'north_full_cell_audit':ref(NORTH/'full_cell_audit.json'),'prior_failed_network':ref(H.parent/'network_batch_r01/freeze_manifest.json'),
             'prior_prepared':ref(H.parent/'network_batch_r01/prepared_runtime.json'),'original_controller':ref(BASE/'Traversal.gd'),'common_loader':ref(ROOT/'voxel_character/common/preview/RenderData.gd')}
    implementations={str(p.relative_to(ROOT)):b.sha(p) for p in [H/n for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare.py']]+[BASE/'prepare.py',H.parent/'network_batch_r01/prepare_batch.py']}
    write(H/'prepared.json',{'schema':'riverstone.actual_north_connector_regression.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':implementations,'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,
          'coverage':{'cases':18,'positive_cases':10,'negative_cases':8,'lane_offsets_m':[-1.5,0,1.5],'collision_audit':audits,'actual_scene_contracts_used':True},
          'assumptions':['Original no-step controller and common native mesh loader unchanged.','Exact composed scene surfaces, native nearby meshes and all finite collision substitutions.','Positive north routes cross the finite seams by0.5m; unrelated northwest road defects remain outside this bounded repair.','Central leaves and secured barriers are static native poses; no moving actor integration claim.','Gate-side controls may expose unsupported side footing rather than block; their exact failures will be retained.']})
    print(json.dumps({'prepared':ref(H/'prepared.json'),'cases':len(routes),'positive_cases':10,'assets':len(assets),'placements':len(placements),'audit':audits}))
if __name__=='__main__':main()
