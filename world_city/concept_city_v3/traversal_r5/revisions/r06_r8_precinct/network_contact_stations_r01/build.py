"""Exact contact-face candidates and source-road station ranges, without geometry edits."""
import collections, hashlib, importlib.util, json, math, pathlib, sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;B=H.parent/'network_batch_r01'
spec=importlib.util.spec_from_file_location('diagnosis',B/'diagnose_results.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=m.b;ROOT=m.ROOT
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def read(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def xz(v):return [v[0],v[2]] if len(v)==3 else v
def cumulative(points):
    values=[0.]
    for a,c in zip(points,points[1:]):values.append(values[-1]+math.dist(xz(a),xz(c)))
    return values
def station(points,point):
    sums=cumulative(points);p=xz(point);best=None
    for i,(aa,cc) in enumerate(zip(points,points[1:])):
        a,c=xz(aa),xz(cc);v=[c[j]-a[j] for j in range(2)];vv=sum(q*q for q in v)
        t=max(0,min(1,sum((p[j]-a[j])*v[j] for j in range(2))/vv)) if vv else 0
        q=[a[j]+t*v[j] for j in range(2)];distance=math.dist(p,q)
        row={'segment_index':i,'segment_station_interval_m':[sums[i],sums[i+1]],'segment_fraction':t,'station_m':sums[i]+t*(sums[i+1]-sums[i]),'distance_to_source_polyline_m':distance,'projected_xz_m':q}
        if best is None or distance<best['distance_to_source_polyline_m']:best=row
    return best
def main():
    p=read(B/'prepared_runtime.json');report=read(B/'evidence/network_initial.json');inv=read(H.parent/'primary_inventory/inventory.json')
    owners=read(H.parent/'network_failure_owners_r01/failure_owner_ledger.json')
    pp={r['id']:r for r in p['routes']};rr={r['id']:r for r in report['routes']};roads={r['id']:r for r in inv['roads']};cache={};out=[]
    for record in owners['failures']:
        rid=record['case_id'];r=rr[rid];route=pp[rid];hits=r['obstacle_contact_samples'];face_hits=[]
        for pid in sorted({h['collider_id'] for h in hits}):
            placement=p['placements'].get(pid)
            if placement is None:continue
            asset=p['assets'][placement['asset_key']];path=ROOT/asset['render_path']
            if path not in cache:cache[path]=read(path)
            data=cache[path];localhits=[h for h in hits if h['collider_id']==pid]
            lo=[min(h['position'][j] for h in localhits)-.02 for j in range(3)];hi=[max(h['position'][j] for h in localhits)+.02 for j in range(3)]
            if asset.get('collision_format') in ['actual_scene_triangles','source_grade_proxy_triangles']:
                iterator=[(i,t) for i,t in enumerate(data['triangles'])]
            else:
                iterator=[((gi,qi),[b.transform(q[j],placement) for j in ix]) for gi,g in enumerate(data['groups']) for qi,q in enumerate(g['quads']) for ix in [[0,2,1],[0,3,2]]]
            for ident,tri in iterator:
                if any(max(v[j] for v in tri)<lo[j] or min(v[j] for v in tri)>hi[j] for j in range(3)):continue
                matching=[]
                for h in localhits:
                    distance=m.distance(h['position'],tri)
                    if distance<=.02:matching.append({'frame':h['frame'],'distance_to_contact_m':distance,'normal':h['normal'],'contact_position':h['position']})
                if not matching:continue
                source=data.get('source_face_indices',[None]*len(data.get('triangles',[])))[ident] if isinstance(ident,int) else {'group_index':ident[0],'quad_index':ident[1]}
                face_hits.append({'collider_id':pid,'source_face_key':source,'asset':asset,'triangle_godot_xyz_m':tri,'matched_persisted_contacts':matching})
        sums=cumulative(route['points']);fi=r['failed_target_index']
        interval=[sums[max(0,fi-1)],sums[fi]] if fi is not None else [0.,sums[-1]]
        source_records=[]
        anchors=[('end',r['end_position'])]
        if r['failed_target'] is not None:anchors.append(('failed_target',r['failed_target']))
        anchors.extend(('contact_frame_'+str(h['frame']),h['position']) for h in hits)
        for roadid in route['source_road_ids']:
            if roadid not in roads:continue
            road=roads[roadid];stations=[{'kind':name,**station(road['polyline_xz_m'],point)} for name,point in anchors]
            localized=fi is not None
            interval_source=[min(q['station_m'] for q in stations),max(q['station_m'] for q in stations)] if localized else [0.,cumulative(road['polyline_xz_m'])[-1]]
            source_records.append({'canonical_road_id':roadid,'source_polyline_xz_m':road['polyline_xz_m'],
                                   'affected_station_interval_m':interval_source,'source_segment_indices':sorted({q['segment_index'] for q in stations}),
                                   'station_scope':'Nearest-source station of actual end/target/contact anchors; not a proven full extent of the defect.' if localized else 'Whole source route only: strict floor-state miss frames were not localized by sparse logs.',
                                   'stations':stations,'bridge_source_is_alignment_hypothesis':roadid=='MAIN_BRIDGE'})
        face_keys=sorted({tuple(h['source_face_key']) for h in face_hits if isinstance(h['source_face_key'],list)}|
                         {tuple(q['scene_face']) for sample in record['end_and_target_actual_scene_samples'] for q in sample['actual_scene_top_hits']})
        out.append({'case_id':rid,'canonical_test_chain':route['group'],'status':r['status'],'route_points_xyz_m':route['points'],
                    'tested_chain_segment_index':max(0,fi-1) if fi is not None else None,'tested_chain_station_interval_m':interval,
                    'source_road_station_records':source_records,'all_localized_actual_scene_face_keys':[list(k) for k in face_keys],
                    'all_persisted_contact_triangle_candidates':face_hits,'end_and_target_actual_scene_samples':record['end_and_target_actual_scene_samples'],
                    'unlocalized_strict_support_failure':fi is None,'native_collider_ids':[q for q in record['obstacle_contact_counts'] if not q.startswith('SCENE:NETWORK:')],
                    'interpretation_limit':'Contact triangle candidates are within2cm of actual reported contacts. They preserve all matches; proximity alone cannot choose a unique native triangle at an edge.'})
    assert len(out)==38
    write(H/'failure_stations_faces.json',{'schema':'riverstone.network_failure_stations_faces.v1','scene':p['sources']['scene'],
          'sources':{'batch_seal':ref(B/'freeze_manifest.json'),'owner_ledger':ref(H.parent/'network_failure_owners_r01/failure_owner_ledger.json'),'inventory':ref(H.parent/'primary_inventory/inventory.json')},
          'cases':out,'source_face_index_convention':'Original scene.surfaces[material] offset divided by3; actual Godot collision triangle order is separately retained.',
          'missing_information':['Per-frame coordinates for every strict support miss are unavailable in the unchanged sparse logger.','Source owner labels and analytic grade are not substituted for actual scene face evidence.']})
    write(H/'freeze_manifest.json',{'schema':'riverstone.network_failure_stations_faces_freeze.v1','files':{str(q.relative_to(ROOT)):ref(q)['sha256'] for q in sorted(H.glob('*')) if q.is_file()}})
    print(json.dumps({'report':ref(H/'failure_stations_faces.json'),'seal':ref(H/'freeze_manifest.json'),'cases':len(out),'all_matched_face_triangles':sum(len(r['all_persisted_contact_triangle_candidates']) for r in out)}))
if __name__=='__main__':main()
