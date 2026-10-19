#!/usr/bin/env python3
"""Audit separate landmark envelopes against public road/path/access volumes.

Envelopes are conservative blockout masses, not actual collision shapes.
Overhead and below-deck intersections remain explicit records, never hidden
by suppressing an entire assembly envelope.
"""
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
import geometry as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1]
sys.path.insert(0,str(ROOT))

def rectangle(lo,hi):return [[lo[0],lo[2]],[hi[0],lo[2]],[hi[0],hi[2]],[lo[0],hi[2]]]

def check(plan_path,author_path,proposal_path=None):
 raw=Path(plan_path).read_bytes();sha=hashlib.sha256(raw).hexdigest();plan=json.loads(raw)
 author_raw=Path(author_path).read_bytes();spec=importlib.util.spec_from_file_location('landmark_road_height_target',author_path);author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 issues=[];overhead=[];below=[];access=[];crossings=[];masters={};masses=[];superseded=set();proposal_record=None;proposal_links=[];proposal_connections=[]
 if proposal_path:
  proposal_raw=Path(proposal_path).read_bytes();proposal=json.loads(proposal_raw)
  proposal_record={'path':str(proposal_path),'sha256':hashlib.sha256(proposal_raw).hexdigest(),'applied_to_source':False}
  if proposal['source_plan']['sha256']!=sha:issues.append({'code':'proposal_source_hash_mismatch'})
  old_ids={p['id'] for p in proposal['obsolete_parent_paths']};plan['paths']=[p for p in plan['paths'] if p['id'] not in old_ids]
  for p in proposal['primary_opening_link_proposals']:
   link={'id':p['id'],'polyline_xz_m':p['path_xz_m'],'width_m':p['width_m'],'proposal_group':p['group']};plan['paths'].append(link);proposal_links.append(link)
  for road in plan['roads']:
   if road['id']==proposal['road_proposal']['id']:road['polyline_xz_m']=proposal['road_proposal']['proposed_polyline_xz_m']
 for assembly in plan.get('landmark_components',[]):
  anchor=assembly['world_anchor_xyz_m'];master=assembly['source_master'];path=ROOT/master['path'];actual=hashlib.sha256(path.read_bytes()).hexdigest();masters[master['path']]=actual
  superseded.update(assembly.get('replaces_source_building_ids',[]))
  if actual!=master['sha256']:issues.append({'code':'landmark_master_hash_mismatch','assembly_id':assembly['id'],'path':master['path']})
  for mass in assembly['masses']:
   if mass.get('bounds_baked_to_anchor_axes'):
    lo=[mass['bounds_local_m']['min'][i]+anchor[i] for i in range(3)];hi=[mass['bounds_local_m']['max'][i]+anchor[i] for i in range(3)];polygon=rectangle(lo,hi)
   else:
    center=[mass['position_local_xyz_m'][i]+anchor[i] for i in range(3)];size=mass['size_xyz_m'];yaw=math.radians(mass.get('yaw_degrees',0));polygon=[]
    for x,z in [(-size[0]/2,-size[2]/2),(size[0]/2,-size[2]/2),(size[0]/2,size[2]/2),(-size[0]/2,size[2]/2)]:polygon.append([center[0]+x*math.cos(yaw)+z*math.sin(yaw),center[2]-x*math.sin(yaw)+z*math.cos(yaw)])
    box=g.bounds(polygon);lo=[box[0],center[1]-size[1]/2,box[1]];hi=[box[2],center[1]+size[1]/2,box[3]]
   record={'assembly_id':assembly['id'],'component_id':mass['id'],'semantic_role':mass.get('semantic_role'),'minimum_xyz_m':lo,'maximum_xyz_m':hi,'polygon_xz_m':polygon,'source_cut_id':mass.get('source_cut_id'),'source_detail_id':mass.get('source_detail_id')};masses.append(record)
  for reservation in assembly.get('access_reservations',[]):
   box=reservation['clearance_box_local_m'];lo=[box['min'][i]+anchor[i] for i in range(3)];hi=[box['max'][i]+anchor[i] for i in range(3)]
   access.append({'assembly_id':assembly['id'],'reservation_id':reservation['id'],'min':lo,'max':hi,'polygon_xz_m':rectangle(lo,hi)})
 for link in proposal_links:
  connected=[road['id'] for road in plan['roads'] if g.line_distance(link['polyline_xz_m'],road['polyline_xz_m'])[0]<=(link['width_m']+road['width_m'])/2-.6]
  proposal_connections.append({'path_id':link['id'],'connected_public_roads_after_capsule_erosion':connected})
  if not connected:issues.append({'code':'proposed_landmark_link_disconnected','path_id':link['id']})
  for segment,(a,b) in enumerate(zip(link['polyline_xz_m'],link['polyline_xz_m'][1:])):
   strip=g.ribbon(a,b,link['width_m'])
   for building in plan['buildings']:
    if building['id'] in superseded or not g.bbox_overlap(g.bounds(strip),g.bounds(building['footprint_xz_m'])):continue
    overlap=g.intersection_area(strip,building['footprint_xz_m'])
    if overlap>1e-5:issues.append({'code':'proposed_landmark_link_other_building_conflict','path_id':link['id'],'segment':segment,'building_id':building['id'],'overlap_area_m2':overlap})
 lines=[dict(line,route_class='public_road') for line in plan['roads']]+[dict(line,route_class='superseded_parent_mass_path' if line.get('owner_building_id') in superseded else 'declared_access_path') for line in plan['paths']]
 for line in lines:
  for segment,(a,b) in enumerate(zip(line['polyline_xz_m'],line['polyline_xz_m'][1:])):
   strip=g.ribbon(a,b,line['width_m'])
   if not strip:continue
   strip_bounds=g.bounds(strip)
   for mass in masses:
    if not g.bbox_overlap(strip_bounds,g.bounds(mass['polygon_xz_m'])):continue
    overlap=g.convex_intersection(strip,mass['polygon_xz_m']);area=g.area(overlap)
    if area<1e-5:continue
    sample=list(overlap)+[[(p[k]+q[k])/2 for k in (0,1)] for p,q in zip(overlap,overlap[1:]+overlap[:1])]+[[sum(p[k] for p in overlap)/len(overlap) for k in (0,1)]]
    heights=[author.road_height_at(line['id'],*p) if line['route_class']=='public_road' else author.path_height_at(line['id'],*p) for p in sample]
    record={'assembly_id':mass['assembly_id'],'component_id':mass['component_id'],'semantic_role':mass['semantic_role'],'route_id':line['id'],'route_class':line['route_class'],'segment':segment,'overlap_area_m2':area,'component_y_range_m':[mass['minimum_xyz_m'][1],mass['maximum_xyz_m'][1]],'sampled_route_y_range_m':[min(heights),max(heights)],'sampled_minimum_headroom_m':mass['minimum_xyz_m'][1]-max(heights),'source_cut_id':mass['source_cut_id'],'source_detail_id':mass['source_detail_id']}
    if mass['maximum_xyz_m'][1]<=min(heights)+.05:
     record['classification']='below_or_at_walk_deck';below.append(record)
    elif mass['minimum_xyz_m'][1]>=max(heights)+1.9:
     record['classification']='overhead_envelope_sampled_clearance';overhead.append(record)
    else:
     record['classification']='capsule_height_band_envelope_overlap';issues.append({'code':'landmark_envelope_public_access_conflict',**record})
    crossings.append(record)
 access_records=[]
 for reservation in access:
  for mass in masses:
   if not g.bbox_overlap(g.bounds(reservation['polygon_xz_m']),g.bounds(mass['polygon_xz_m'])):continue
   overlap=g.intersection_area(reservation['polygon_xz_m'],mass['polygon_xz_m'])
   height=min(reservation['max'][1],mass['maximum_xyz_m'][1])-max(reservation['min'][1],mass['minimum_xyz_m'][1])
   if overlap>1e-5 and height>1e-5:
    record={'reservation_assembly_id':reservation['assembly_id'],'reservation_id':reservation['reservation_id'],'component_assembly_id':mass['assembly_id'],'component_id':mass['component_id'],'overlap_area_m2':overlap,'vertical_overlap_m':height,'source_cut_id':mass['source_cut_id']};access_records.append(record)
    issues.append({'code':'landmark_envelope_reserved_access_volume_conflict',**record})
 if Path(plan_path).read_bytes()!=raw or Path(author_path).read_bytes()!=author_raw:issues.append({'code':'input_changed_during_audit'})
 snapshot=HERE/'evidence'/'sources'/('plan_'+sha+'.json');snapshot.write_bytes(raw)
 author_sha=hashlib.sha256(author_raw).hexdigest();author_snapshot=HERE/'evidence'/'sources'/('author_'+author_sha+'.py');author_snapshot.write_bytes(author_raw)
 return {'schema':'riverstone.concept_city.independent_landmark_envelopes.v1','status':'pass' if not issues else 'fail','source':{'path':str(plan_path),'sha256':sha,'snapshot':str(snapshot)},'candidate_proposal':proposal_record,'height_api_sha256':author_sha,'height_api_snapshot':str(author_snapshot),'master_hashes':masters,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'counts':{'assemblies':len(plan.get('landmark_components',[])),'components':len(masses),'access_reservations':len(access),'road_path_envelope_intersections':len(crossings),'overhead_intersections':len(overhead),'below_deck_intersections':len(below),'issues':len(issues)},'issues':issues,'overhead_intersections':overhead,'below_deck_intersections':below,'reserved_access_conflicts':access_records,'candidate_public_connections':proposal_connections,
  'scope':['Checks every plan.landmark_components mass independently at its explicit world anchor.','Roads and declared entrance paths use full source width.','Original parent mass pass remains separate from this component audit.','Access reservation boxes are tested as exact finite 3D AABBs against baked component envelopes.'],
  'limitations':['Conservative blockout envelopes can include intended doorway voids; conflicts need actual source cuts reviewed rather than automatic removal.','Overhead clearance uses sampled route heights and does not certify actual capsule, fine detail or arch clearances.','Internal assembly union is intentional; component-component overlaps are not treated as independent-building conflicts.','No collision shapes, renderer changes, source modifications or common voxel completion are claimed.']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--proposal',type=Path);args=ap.parse_args();r=check(CITY/'source/plan.json',CITY/'topography/author.py',args.proposal);fingerprint=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()[:12];out=HERE/'evidence'/(('landmark_proposal_' if args.proposal else 'landmarks_')+r['source']['sha256'][:12]+'_'+fingerprint+'.json');out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({'status':r['status'],'counts':r['counts'],'issues':r['issues'],'output':str(out)},indent=2));raise SystemExit(0 if not r['issues'] else 2)
