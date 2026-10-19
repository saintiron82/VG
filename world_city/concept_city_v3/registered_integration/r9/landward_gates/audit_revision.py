import json,math,sys,hashlib
from pathlib import Path
H=Path(__file__).parent;name=sys.argv[1];prev=sys.argv[2]if len(sys.argv)>2 else None;C=H/name
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=read(C/'surface_patch.json');r=read(C/'routes.json');grades=[]
for route in r['routes'][:2]:
 seg=[]
 for i,(a,b)in enumerate(zip(route['points'],route['points'][1:])):
  ll=math.hypot(b[0]-a[0],b[2]-a[2]);dy=b[1]-a[1];seg.append(dict(index=i,from_xyz_m=a,to_xyz_m=b,length_xz_m=ll,height_change_m=dy,absolute_grade=abs(dy)/ll))
 high=[s for s in seg if s['absolute_grade']>.1];grades.append(dict(route_id=route['id'],peak=max(seg,key=lambda s:s['absolute_grade']),above_10_percent_length_m=sum(s['length_xz_m']for s in high),above_10_percent_absolute_height_change_m=sum(abs(s['height_change_m'])for s in high),external_max_grade=max(s['absolute_grade']for s in seg[route['gate_waypoint_index']:]),route_length_m=sum(s['length_xz_m']for s in seg)))
d=dict(candidate=name,base_scene_sha256=p['base_scene_sha256'],postfilter_counts=dict(source_triangle_edits=len(p['surface_edits']),replacement_triangles=sum(len(e['replacement_triangles_xyz_m'])for e in p['surface_edits']),appended_triangles=sum(len(v)//3 for v in p['appended_surfaces'].values()),water_edits=0),float32_fragment_correction=p['float32_fragment_correction'],grade_analysis=grades)
if prev:
 P=H/prev;old=read(P/'surface_patch.json');a={(e['material'],e['triangle_index']):e for e in old['surface_edits']};b={(e['material'],e['triangle_index']):e for e in p['surface_edits']};sourcechanges=[list(k)for k in sorted(set(a)|set(b))if a.get(k)!=b.get(k)];tops={}
 for m in set(old['appended_surfaces'])|set(p['appended_surfaces']):
  aa=old['appended_surfaces'].get(m,[]);bb=p['appended_surfaces'].get(m,[]);changed=[]
  for i in range(max(len(aa),len(bb))//3):
   if aa[i*3:i*3+3]!=bb[i*3:i*3+3]:changed.append(i)
  tops[m]=dict(previous_triangle_count=len(aa)//3,new_triangle_count=len(bb)//3,changed_indices=changed,index_shift_possible=len(aa)!=len(bb))
 d['previous_candidate']=prev;d['change_ledger']=dict(source_edit_changes=sourcechanges,appended_surface_changes=tops,native_pack_content_unchanged={n:sha(P/n)==sha(C/n)for n in ['gate_pack.json','bridge_pack.json','farm_pack.json','upper_retirement_pack.json']},ownership_xz_unchanged=read(P/'ground_ownership.json')==read(C/'ground_ownership.json'),affected_runtime_cases='Both full gate routes and both affected existing-road junctions, both directions; all throat offset/turn probes; retained controls. No inherited pass across unresolved geometry change.')
(C/'final_source_accounting_and_grades.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'candidate':name,'counts':d['postfilter_counts'],'peak_grades':{g['route_id']:g['peak']['absolute_grade']for g in grades},'source_changes':len(d.get('change_ledger',{}).get('source_edit_changes',[]))}))
