"""Explicit dry-route correction for the reconstructed, immutable B015 base pack."""
import copy,json,math,hashlib
from pathlib import Path
from ..author_density import ROOT,PLAN,ref,write
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).parent;BASE=HERE.parent/'resolved_placements.json'
ID='DENS_B15E_HOUSE_020:ACTUAL_DOOR:1'
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def disc(p,w):
 radius=w/2/math.cos(math.pi/32)
 return [[p[0]+radius*math.cos(i*math.pi/16),p[1]+radius*math.sin(i*math.pi/16)] for i in range(32)]
def apply(base,overlay):
 assert digest(base)==overlay['base_json_sha256'];out=copy.deepcopy(base)
 for change in overlay['route_replacements']:
  i=next(i for i,r in enumerate(out['access_proposals']) if r['id']==change['id']);assert digest(out['access_proposals'][i])==change['original_route_sha256'];out['access_proposals'][i]=copy.deepcopy(change['replacement'])
 out.update(access_addendum=ref(HERE/'route_addendum.json'),status='reconstructed_native_candidate_with_dry_route_pending_terrain_and_independent_review')
 return out

def run():
 base=json.loads(BASE.read_text());plan=json.loads(PLAN.read_text());old=next(r for r in base['access_proposals'] if r['id']==ID);road=next(r for r in plan['roads'] if r['id']=='EAST_RADIAL');start,oldend=old['complete_proposed_connection_xz_m'];outward=[(start[i]-oldend[i])/math.dist(start,oldend) for i in (0,1)];bend=[oldend[i]+2*outward[i] for i in (0,1)];u,v=road['polyline_xz_m'][45:47];end=[u[i]+.2*(v[i]-u[i]) for i in (0,1)];line=[start,bend,end]
 new=copy.deepcopy(old);new.update(complete_proposed_connection_xz_m=line,reserved_connection_polygons_xz_m=[g.road_ribbon(a,b,1.8) for a,b in zip(line,line[1:])],reserved_round_join_polygons_xz_m=[disc(bend,1.8)],connects_segment_index=45,connects_segment_t=.2,vertical_status='Finite dry-route candidate at +2.5; terrain-owner binding pending',repair_reason='Reach the same public street north of the finite canal interruption.')
 overlay=dict(schema='riverstone.block015_east.route_addendum.v1',author=ref(Path(__file__)),base_pack=ref(BASE),base_json_sha256=digest(base),source_plan=ref(PLAN),route_replacements=[dict(id=ID,original_route_sha256=digest(old),original=old,replacement=new)],unchanged_fields=['assets','placements','component_placements','ownership_masks','courts','court_paths','ground_ownership_records','ground_service_paths','replaced_placement_ids'],unchanged_actual_door_count=65,old_approach_owner_ids=[ID+':approach:0'],new_approach_owner_ids=[ID+':approach:0',ID+':approach:1',ID+':round_join:0'],terrain_owner_change='Replace the old approach with these two ribbons and the rounded join, all at +2.5 m; preserve the threshold stub and public/water priority. No canal fill.',public_endpoint=dict(road_id=road['id'],segment_index=45,segment_t=.2,point_xyz_m=[end[0],2.5,end[1]],width_m=1.8),length_m=sum(math.dist(a,b) for a,b in zip(line,line[1:])),runtime_ready=False)
 write(HERE/'route_addendum.json',overlay);out=apply(base,overlay);write(HERE/'effective_placements.json',out);print(json.dumps(dict(addendum=ref(HERE/'route_addendum.json'),effective_pack=ref(HERE/'effective_placements.json'),length_m=overlay['length_m']),indent=2));return overlay,out
if __name__=='__main__':run()
