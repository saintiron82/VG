"""Atomic local top/bank wrappers and exact dependency rebind; no source mutation."""
import json,copy,collections,math
from .author import *
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
from ...r17_district_batches.side_clearance import area3d

def main():
 bp=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/activation_binding.json';binding=json.loads(bp.read_bytes());patches=[]
 for r in binding['patches']:
  path=ROOT/r['path'];assert sha(path)==r['sha256'];patches.append(json.loads(path.read_bytes()))
 bdpath=HERE/'boundary_candidate.json';bd=json.loads(bdpath.read_bytes());assert bd['sources'][0]['sha256']=='dbdd470b6d496c9828e64e018ba78a6de42cc70480e89c49632c9f4cc53ec2f1'
 target={r['source_triangle_sha256']:r for r in bd['side_surface_edits']};matches=collections.defaultdict(list)
 for pi,src in enumerate(patches):
  vs=src.get('appended_surfaces',{}).get('bank',[])
  for i in range(0,len(vs),3):
   h=a.canonical_sha(vs[i:i+3])
   if h in target:matches[h].append((pi,i//3))
 assert all(len(matches[h])==1 for h in target);assert set(i for v in matches.values()for i,j in v)=={6,16,20}
 final=copy.deepcopy(patches);final[15]=json.loads((HERE/'public_top_rebound.json').read_bytes());ledger=[]
 for pi in [6,16,20]:
  src=patches[pi];out=[];rows=[];vs=src['appended_surfaces']['bank']
  for i in range(0,len(vs),3):
   t=vs[i:i+3];h=a.canonical_sha(t);r=target.get(h)
   if r is None:out.extend(t);continue
   replacement=r['replacement_triangles_xyz_m'];rows.append(dict(source_appended_triangle_index=i//3,source_triangle_sha256=h,source_scene_triangle_index=r['triangle_index'],source_triangle_xyz_m=t,replacement_triangles_xyz_m=replacement));out.extend(v for tr in replacement for v in tr)
  final[pi]['appended_surfaces']['bank']=out;final[pi]['north_junction_side_retirement']=dict(source=binding['patches'][pi],source_scene=bd['sources'][0],retired_appended_triangle_count=len(rows),exact_original_source_edits_preserved=True);ledger.append(dict(patch_index=pi,patch_id=src['id'],source=binding['patches'][pi],rows=rows))
 # Explicit retained deck edge, independently diagnosed before this repair.
 assert len(bd['unknown_exterior_segments'])==1
 edge=bd['unknown_exterior_segments'][0];assert edge['owner_id']=='R18_FINITE:9604:2:NORTH_TRANSITION:1'
 logical=json.loads((HERE/'physical_owners.json').read_bytes())['records'];byid={r['id']:r for r in logical};pl=byid[edge['owner_id']]['plane_y_xz_m'];u,v=edge['edge_xz_m'];assert math.dist(u,v)<.003394
 known=dict(**edge,other_owner=['accepted_native_deck','MARKET_NORTH'],owned_y_m=[p.val(pl,x)for x in[u,v]],outside_y_m=[15.6,15.6],kind='nonwalking_retaining',maximum_delta_m=max(abs(p.val(pl,x)-15.6)for x in[u,v]),evidence=ref(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_r01/market_north_guard_edge_diagnostic.json'))
 seams=bd['boundary_seams']+[known];new=[]
 for r in seams:
  if r['kind']!='nonwalking_retaining':continue
  u,v=r['edge_xz_m'];ys,zs=r['owned_y_m'],r['outside_y_m'];poly=byid[r['owner_id']]['polygon_xz_m'];sgn=1 if g.signed_area(poly)>0 else-1;dx,dz=v[0]-u[0],v[1]-u[1];outward=[sgn*dz,-sgn*dx];lowdirection=outward if sum(ys)>sum(zs)else[-q for q in outward];verts=[[u[0],ys[0],u[1]],[v[0],ys[1],v[1]],[v[0],zs[1],v[1]],[u[0],zs[0],u[1]]]
  for t in [[verts[0],verts[1],verts[2]],[verts[0],verts[2],verts[3]]]:
   if area3d(t)<=0:continue
   a1=[t[1][k]-t[0][k]for k in range(3)];b1=[t[2][k]-t[0][k]for k in range(3)];normal=[a1[1]*b1[2]-a1[2]*b1[1],a1[2]*b1[0]-a1[0]*b1[2],a1[0]*b1[1]-a1[1]*b1[0]]
   if normal[0]*lowdirection[0]+normal[2]*lowdirection[1]<0:t=[t[0],t[2],t[1]]
   new.append(t)
 final[16]['appended_surfaces']['bank'].extend(v for t in new for v in t);final[16]['north_junction_new_boundary']=dict(source=ref(bdpath),triangle_count=len(new),all_numerically_positive_3d_area_preserved=True,explicit_native_edge=known)
 # Preserve stable producer IDs and update only dependent canonical hashes.
 ids={x['id']:i for i,x in enumerate(final)};done=set();active=set()
 def rebind(i):
  if i in done:return
  assert i not in active;active.add(i)
  for pid in final[i].get('requires_patch_canonical_sha256',{}):
   j=ids[pid];rebind(j);final[i]['requires_patch_canonical_sha256'][pid]=merger.canonical_sha(final[j])
  active.remove(i);done.add(i)
 for i in range(len(final)):rebind(i)
 outbinding=copy.deepcopy(binding);changed=[]
 for i,(old,newp)in enumerate(zip(patches,final)):
  assert old['surface_edits']==newp['surface_edits'];assert old['source_surface_hashes']==newp['source_surface_hashes']
  if newp==old:continue
  fp=HERE/f'producer_{i:02d}.json';outbinding['patches'][i]=dump(fp,newp);changed.append(dict(patch_index=i,id=newp['id'],source=binding['patches'][i],replacement=outbinding['patches'][i],old_canonical_sha256=merger.canonical_sha(old),new_canonical_sha256=merger.canonical_sha(newp),geometry_changed=i in [6,15,16,20]))
 for x in final:
  for pid,h in x.get('requires_patch_canonical_sha256',{}).items():assert merger.canonical_sha(final[ids[pid]])==h
 outbinding['north_junction_transition']=dict(sources=[ref(bp),ref(HERE/'physical_owners.json'),ref(HERE/'profile_screen.json')],status='SOURCE_GEOMETRY_READY_ACTUAL_SCENE_REPLAY_PENDING');dump(HERE/'activation_binding.json',outbinding);dump(HERE/'bank_retirement_ledger.json',dict(sources=[ref(bp),ref(bdpath)],rows=ledger,new_retaining_triangles_xyz_m=new,explicit_native_deck_edge=known));dump(HERE/'integration_handoff.json',dict(schema='riverstone.north_junction_transition_handoff.v1',status='SOURCE_READY_PENDING_ACTUAL_COMPOSED_REPLAY',binding=ref(HERE/'activation_binding.json'),sources=[ref(bp),ref(HERE/'profile_screen.json'),ref(HERE/'physical_owners.json')],producer_replacements=changed,top_retirement=ref(HERE/'appended_top_retirement_ledger.json'),bank_retirement=ref(HERE/'bank_retirement_ledger.json'),entry_profiles=ref(HERE/'c006_public_planes.json'),required_replays=['ROAD:MARKET_NORTH both directions','ROAD:NORTH_BACK_LANE both directions','NORTH_TWO_BRIDGE_INTERIOR_TURN_R03 both directions','full-width lanes across all three corrected contacts','actual native guard and water controls'],limits=['Only the local public road field and its finite bank closure are replaced. Fixed water fields, native caches, terrain coordinates outside the exact polygons and controller are unchanged.','Outer nonwalking land retains its measured height and is connected by explicit banks; those banks are not walking floor.','Existing unrelated public route failures remain separate.']))
 print('wrapped',[(r['patch_index'],r['geometry_changed'])for r in changed],'retired banks',len(target),'new banks',len(new));print(ref(HERE/'integration_handoff.json'))
if __name__=='__main__':main()
