"""Read-only result integrity audit; writes a new report without rewriting failures."""
import pathlib,json,hashlib,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=H.parents[2]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def main():
 raw=pathlib.Path(sys.argv[1]).resolve();output=pathlib.Path(sys.argv[2]).resolve();p=read(H/'prepared.json');r=read(raw);issues=[]
 for label,source in p['sources'].items():
  if sha(source['path'])!=source['sha256']:issues.append(['changed_source',label])
 for name,h in p['implementation_hashes'].items():
  if sha(ROOT/name)!=h:issues.append(['changed_implementation',name])
 for key,a in p['assets'].items():
  if sha(ROOT/a['render_path'])!=a['render_sha256']:issues.append(['changed_collision_resource',key])
 if r.get('prepared_sha256')!=sha(H/'prepared.json'):issues.append(['wrong_prepared_manifest'])
 expected={x['id']:x for x in p['routes']};actual={x['id']:x for x in r.get('routes',[])}
 if len(actual)!=6 or set(actual)!=set(expected):issues.append(['missing_or_duplicate_cases'])
 if r.get('settings',{}).get('physics_hz')!=60:issues.append(['wrong_physics_rate'])
 for ident,item in actual.items():
  if item.get('within_route_teleports')!=0:issues.append(['teleport_record',ident])
  if item.get('source_road_ids')!=expected[ident]['source_road_ids']:issues.append(['route_mismatch',ident])
 result={'schema':'riverstone.r5.capsule_independent_result_integrity.v1','integrity_status':'pass' if not issues else 'fail','physics_status':r.get('status'),'raw_report':{'path':str(raw),'sha256':sha(raw)},'prepared_sha256':sha(H/'prepared.json'),'auditor_sha256':sha(__file__),'issues':issues,'summary':r.get('summary'),'cases':[{'id':x['id'],'status':x.get('status'),'pass':x.get('pass'),'feet_y_min':x.get('min_feet_y_m'),'ground_ray_misses':x.get('ground_ray_miss_frames'),'floor_state_misses':x.get('not_on_floor_frames'),'obstacle_contacts':x.get('obstacle_contact_ids'),'failed_target_index':x.get('failed_target_index')} for x in r.get('routes',[])],'limits':p['assumptions']}
 with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'integrity_status':result['integrity_status'],'physics_status':result['physics_status'],'issues':issues,'summary':result['summary']},indent=2))
 if issues:raise SystemExit(2)
if __name__=='__main__':main()
