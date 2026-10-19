"""Canonical routing and actual geometry ownership for the sealed failed batch."""
import collections, hashlib, json, pathlib
H = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in H.parents if (p/'voxel_character').is_dir())
B = H.parent/'network_batch_r01'
def read(p): return json.loads(pathlib.Path(p).read_bytes())
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p): return {'path':str(p.relative_to(ROOT)), 'sha256':sha(p)}
def write(p,v):
    with p.open('x') as f: json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def y_at(t,x,z):
    a,b,c=t;ux,uz=b[0]-a[0],b[2]-a[2];vx,vz=c[0]-a[0],c[2]-a[2];det=ux*vz-uz*vx
    if abs(det)<1e-12:return None
    u=((x-a[0])*vz-(z-a[2])*vx)/det;v=(ux*(z-a[2])-uz*(x-a[0]))/det
    if min(u,v,1-u-v)<-1e-9:return None
    return a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])
def main():
    p=read(B/'prepared_runtime.json');report=read(B/'evidence/network_initial.json')
    loc=read(B/'evidence/contact_localization_final_098.json');water=read(B/'evidence/water_sample_review.json')
    pp={r['id']:r for r in p['routes']};local={r['route_id']:r for r in loc['findings']};cache={};rows=[];groups=collections.defaultdict(list)
    for r in report['routes']:
        source=pp[r['id']]
        if 'expected_failure' in source or r['pass']:continue
        first=local.get(r['id']);points={'end_center_xz':r['end_position'],'failed_target':r.get('failed_target')}
        samples=[]
        for name,point in points.items():
            if point is None:continue
            hits=[]
            for pid in source['placement_ids']:
                asset=p['assets'][p['placements'][pid]['asset_key']]
                if asset.get('collision_format')!='actual_scene_triangles':continue
                path=ROOT/asset['render_path']
                if path not in cache:cache[path]=read(path)
                for face,tri in zip(cache[path]['source_face_indices'],cache[path]['triangles']):
                    x,z=point[0],point[2]
                    if x<min(v[0] for v in tri) or x>max(v[0] for v in tri) or z<min(v[2] for v in tri) or z>max(v[2] for v in tri):continue
                    y=y_at(tri,x,z)
                    if y is not None:hits.append({'scene_face':face,'y_m':y,'height_below_capsule_center_m':point[1]-y})
            samples.append({'station':name,'xyz_m':point,'actual_scene_top_hits':hits})
        owner_ids=sorted(r['obstacle_contact_ids'])
        owner_groups=[]
        for owner in owner_ids:
            if owner.startswith('SCENE:NETWORK:'):
                owner_groups.append('ACTUAL_SCENE_SURFACES:'+','.join(sorted({f['source_face'][0] for f in first['candidate_faces_within_2cm'] if isinstance(f['source_face'],list)})) if first else 'ACTUAL_SCENE_SURFACES:UNLOCALIZED')
            else:owner_groups.append('NATIVE:'+owner)
        if not owner_groups:owner_groups=['NO_OBSTACLE_CONTACT_RECORDED:'+r['status']]
        row={'case_id':r['id'],'canonical_route_id':source['group'],'source_road_ids':source['source_road_ids'],
             'status':r['status'],'strict_pass':False,'geometry_owner_groups':owner_groups,
             'first_contact_localization':first,'obstacle_contact_counts':r['obstacle_contact_ids'],
             'ground_ray_miss_frames':r['ground_ray_miss_frames'],'not_on_floor_frames':r['not_on_floor_frames'],
             'failed_target_index':r['failed_target_index'],'spawn_position':r.get('spawn_position'),
             'last_recorded_support_samples':r['position_samples'][-3:],
             'end_and_target_actual_scene_samples':samples,
             'underwater_persisted_samples':[q for q in water['wet_samples'] if q['id']==r['id']],
             'scope_note':'Actual scene face indices are original material-array triangle indices. No-contact failures are not assigned a guessed obstacle; sparse support logs do not localize every missed frame.'}
        rows.append(row)
        for owner in owner_groups:groups[owner].append(r['id'])
    assert len(rows)==38
    output={'schema':'riverstone.network_failure_geometry_owners.v1','status':'FAILED_REGRESSION_REPAIR_INPUT_ONLY',
            'sources':{'sealed_batch':ref(B/'freeze_manifest.json'),'prepared':ref(B/'prepared_runtime.json'),
                       'result':ref(B/'evidence/network_initial.json'),'localization':ref(B/'evidence/contact_localization_final_098.json'),
                       'priority_diagnosis':ref(B/'evidence/priority_diagnosis.json')},
            'scene':p['sources']['scene'],'failure_count':38,'owner_groups':dict(groups),'failures':rows,
            'unresolved_limits':['This ledger does not authorize broad corridor reconstruction or ownership changes.',
                                 'Support loss, blocked-without-contact, and strict transient floor-state failures require exact localized follow-up.',
                                 'North bridge gap is separately assigned to the parent. Final geometry must be replayed against unchanged vectors/controller.']}
    write(H/'failure_owner_ledger.json',output)
    write(H/'freeze_manifest.json',{'schema':'riverstone.network_failure_owner_addendum.v1','files':{str(q.relative_to(ROOT)):sha(q) for q in sorted(H.glob('*')) if q.is_file()}})
    print(json.dumps({'ledger':ref(H/'failure_owner_ledger.json'),'freeze':ref(H/'freeze_manifest.json'),'groups':dict(groups)}))
if __name__=='__main__':main()
