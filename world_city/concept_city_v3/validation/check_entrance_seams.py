#!/usr/bin/env python3
"""Independent per-door mapping and finite transition edge regression.

Keeps body/compound retaining interfaces separate from exterior taper seams.
No actual capsule or navigability pass is inferred from a continuous edge.
"""
import hashlib,importlib.util,json,math,sys
from collections import Counter
from pathlib import Path
import geometry as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1];sys.path.insert(0,str(ROOT))

def check():
 paths={'plan':CITY/'source/plan.json','contract':CITY/'topography/contract.json','author':CITY/'topography/author.py'};raw={k:p.read_bytes() for k,p in paths.items()};sha={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()}
 plan=json.loads(raw['plan']);contract=json.loads(raw['contract']);spec=importlib.util.spec_from_file_location('entrance_seam_height_target',paths['author']);author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 issues=[];seams=[];excluded=[];entries=[];status_counts=Counter();path_index={p['id']:p for p in plan['paths']};buildings={b['id']:b for b in plan['buildings']}
 if contract.get('source_plan_sha256')!=sha['plan'] or author.SOURCE_PLAN_SHA256!=sha['plan']:issues.append({'code':'mixed_source_revision'})
 solids=[]
 for pad in contract['building_pads']:solids.append((pad['building_id'],pad.get('body_polygon_xz_m',pad['owned_polygons_xz_m'][0])))
 for pad in contract.get('compound_pads',[]):
  for poly in pad['owned_polygons_xz_m']:solids.append((pad['id'],poly))
 spatial={}
 for owner,poly in solids:
  box=g.bounds(poly)
  for ix in range(math.floor(box[0]/16),math.floor(box[2]/16)+1):
   for iz in range(math.floor(box[1]/16),math.floor(box[3]/16)+1):spatial.setdefault((ix,iz),[]).append((owner,poly))
 def solid_owners(p):return [owner for owner,poly in spatial.get((math.floor(p[0]/16),math.floor(p[1]/16)),[]) if g.point_inside(p,poly)]
 maximum_length=0;maximum_threshold=0;tested=0;max_jump=0;maximum_centerline_grade=0
 for pad in contract['building_pads']:
  building=buildings[pad['building_id']];declared=building.get('all_entrances_xz_m',[building['entrance_xz_m']]);ledger=pad['entrance_ledger']
  if len(ledger)!=len(declared):issues.append({'code':'door_ledger_count_mismatch','building_id':building['id'],'declared':len(declared),'ledger':len(ledger)})
  for entry in ledger:
   pid=entry.get('path_id');point=entry['xz_m'];path=path_index.get(pid);status=entry['routing_status'];status_counts[status]+=1
   if not any(math.dist(point,p)<1e-6 for p in declared):issues.append({'code':'ledger_door_not_in_source','building_id':building['id'],'door_index':entry['door_index']})
   if not path or math.dist(point,path['polyline_xz_m'][0])>1e-6:issues.append({'code':'door_path_start_mismatch','building_id':building['id'],'path_id':pid});continue
   a,b=entry['approach_polyline_xz_m'];length=math.dist(a,b);maximum_length=max(maximum_length,length)
   if length>2.00001:issues.append({'code':'approach_exceeds_two_metres','building_id':building['id'],'length_m':length})
   threshold=author.path_height_at(pid,*point)-pad['floor_y_m'];maximum_threshold=max(maximum_threshold,abs(threshold))
   if abs(threshold)>1e-6:issues.append({'code':'actual_threshold_height_mismatch','building_id':building['id'],'door_index':entry['door_index'],'delta_m':threshold})
   if length<1e-8:continue
   direction=[(b[k]-a[k])/length for k in (0,1)];normal=[-direction[1],direction[0]];half=entry['width_m']/2+.6;epsilon=1e-4
   samples=[]
   for fraction in (-1,-.75,-.5,0,.5,.75,1):
    p=[b[k]+normal[k]*half*fraction for k in (0,1)];samples.append(('outer',p,direction))
   for fraction in (.25,.5,.75):
    for side in (-1,1):
     p=[a[k]+direction[k]*length*fraction+normal[k]*half*side for k in (0,1)];samples.append(('side',p,[normal[k]*side for k in (0,1)]))
   max_entry_jump=0
   for edge,p,out in samples:
    inside=[p[k]-out[k]*epsilon for k in (0,1)];outside=[p[k]+out[k]*epsilon for k in (0,1)];owners=sorted(set(solid_owners(inside)+solid_owners(outside)))
    delta=abs(author.path_height_at(pid,*inside)-author.path_height_at(pid,*outside))
    if owners:
     excluded.append({'building_id':building['id'],'door_index':entry['door_index'],'edge':edge,'point_xz_m':p,'body_or_compound_owners':owners,'measured_jump_m':delta});continue
    tested+=1;max_jump=max(max_jump,delta);max_entry_jump=max(max_entry_jump,delta)
    if delta>.001:seams.append({'building_id':building['id'],'door_index':entry['door_index'],'edge':edge,'point_xz_m':p,'jump_over_0p2mm_m':delta,'routing_status':status})
   points=[[a[k]+direction[k]*length*i/40 for k in (0,1)] for i in range(41)]
   heights=[author.path_height_at(pid,*p) for p in points];grade=max(abs(y1-y0)/(length/40) for y0,y1 in zip(heights,heights[1:]));maximum_centerline_grade=max(maximum_centerline_grade,grade)
   entries.append({'building_id':building['id'],'door_index':entry['door_index'],'path_id':pid,'approach_length_m':length,'routing_status':status,'threshold_delta_m':threshold,'maximum_external_edge_jump_m':max_entry_jump,'maximum_sampled_centerline_grade':grade})
 for seam in seams:issues.append({'code':'exterior_transition_edge_discontinuity',**seam})
 if any(p.read_bytes()!=raw[k] for k,p in paths.items()):issues.append({'code':'input_changed_during_audit'})
 sources={}
 for k,data in raw.items():
  snapshot=HERE/'evidence'/'sources'/(k+'_'+sha[k]+paths[k].suffix);snapshot.write_bytes(data);sources[k]={'path':str(paths[k]),'sha256':sha[k],'snapshot':str(snapshot)}
 return {'schema':'riverstone.concept_city.independent_entrance_seams.v1','status':'fail' if issues else 'pass_mapping_and_external_seams_only','sources':sources,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'counts':{'pads':len(contract['building_pads']),'door_ledgers':len(entries),'exterior_edge_samples':tested,'body_or_compound_edge_samples_excluded':len(excluded),'issues':len(issues),'status_counts':dict(status_counts)},
 'checks':{'maximum_approach_length_m':maximum_length,'maximum_actual_threshold_delta_m':maximum_threshold,'maximum_external_edge_jump_over_0p2mm_m':max_jump,'maximum_sampled_centerline_grade':maximum_centerline_grade},
 'entries':entries,'issues':issues,'body_or_compound_interfaces':excluded,
 'limitations':['Mapping and bounded exterior seam regression only.','Body/compound retaining interfaces are listed separately, not silently treated as continuous.','Tight frontage, steep approaches and declared steps/replan exceptions remain uncertified.','Finite edge samples and source API do not establish actual capsule or common voxel traversal.']}

if __name__=='__main__':
 report=check();fingerprint=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()[:12];out=HERE/'evidence'/('entrance_seams_'+report['sources']['plan']['sha256'][:12]+'_'+fingerprint+'.json');out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'counts':report['counts'],'checks':report['checks'],'issues':report['issues'][:20],'output':str(out)},indent=2));raise SystemExit(2 if report['issues'] else 0)
