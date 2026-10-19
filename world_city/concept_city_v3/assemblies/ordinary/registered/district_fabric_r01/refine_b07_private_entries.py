"""Keep upper B07 rise on private land until its actual higher public terminal."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config,PublicSamples
from .finalize_coherent import overlap
import types

def run():
 src=SOURCE/'b07_terrace_refit_r01/BLOCK_007';out=SOURCE/'b07_terrace_refit_r02/BLOCK_007';out.mkdir(parents=True,exist_ok=True);g.HERE=out;l=g.load(src/'selected_layout.json');l['supersedes_source']=g.ref(src/'selected_layout.json');plan=g.CITY/'registered_integration/r8/coverage_plan';block=next(b for b in g.load(plan/'baseline_blocks.json')['blocks']if b['block_id']=='BLOCK_007');config(block);scene=g.load(g.R7);sample=PublicSamples(scene);manifest=g.load(SOURCE/'effective_city_manifest_r01.json');retired=set(l['retired_source_ids'])|set(manifest['replaced_placement_ids']);proj=g.load(plan/'native_projection.json')['instances'];retained=[q for p in proj if p['id']not in retired for q in p['native_owner_parts_xz_m']];special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];native=[q for p in l['placements']for q in p['native_walking_obstacles_xz_m']];vs=scene['surfaces']['water'];water=[[[v[0],v[2]]for v in vs[i:i+3]]for i in range(0,len(vs),3)];domain=g.raster(g.triangulate(block['polygon_xz_m']));roads=g.load(g.CITY/'registered_source/plan.json')['roads'];roadpolys=[g.geo.road_ribbon(a,b,r['width_m'])for r in roads for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])];base=g.np.load(plan/'baseline_masks.npz');x=((g.XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);z=((g.ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int);ms={k:base[k][g.np.ix_(z,x)]for k in base.files if base[k].ndim==2};hard=g.raster(retained+native+special+water+roadpolys,True)|ms['spaces']|ms['estates']|ms['wall'];upper=['BLOCK_007:R8_C001','BLOCK_007:R8_C005','BLOCK_007:R8_C006','BLOCK_007:R8_C007'];fail=[];proof=[]
 for h in l['holdings']:
  if h['id']not in upper:continue
  if h['id'].endswith(('C006','C007')):
   old=next(p for p in l['placements']if p['holding_id']==h['id']);center=list(g.np.mean(h['holding_polygon_xz_m'],axis=0));h['gate_position_xz_m']=g.xform([9.5,6],center,old['yaw_rad'])
  gate=h['gate_position_xz_m'];floor=h['floor_y_m'];w=2.;roadid='EAST_WALL_SERVICE'if h['id'].endswith(('C006','C007'))else'UPPER_CONTOUR';road=next(r for r in roads if r['id']==roadid);free=domain&~hard
  for oh in l['holdings']:
   if oh['id']!=h['id']:free&=~g.raster([oh['holding_polygon_xz_m']],True)
  clear=g.ndimage.distance_transform_edt(free)*g.GRID>=w/2+.15;start=g.nearest(clear,gate,3);candidates=[]
  for si,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   for tt in g.np.linspace(0,1,max(2,int(g.math.ceil(g.math.dist(a,b)/1.5))+1)):
    q=[a[k]+float(tt)*(b[k]-a[k])for k in[0,1]];d=g.math.dist(q,gate);e=sample.at(q)
    if not e or not 5<d<85:continue
    if abs(floor-e['y_m'])>max(1,d*.10):continue
    candidates.append((d+abs(floor-e['y_m'])*4,q,e,si))
  candidates.sort(key=lambda x:x[0]);found=None
  for _,q,e,si in candidates[:100]:
   end=g.nearest(clear,q,road['width_m']/2+w+1);goals=g.np.zeros(g.SHAPE,bool)
   if end:goals[end]=True
   ll=g.astar(clear,start,goals)if start and end else None
   if not ll:continue
   ll=[gate]+ll+[q];ll=[v for j,v in enumerate(ll)if not j or g.math.dist(v,ll[j-1])>1e-7];length=sum(g.math.dist(a,b)for a,b in zip(ll,ll[1:]));private_budget=length-(road['width_m']/2+w+1);grade=abs(floor-e['y_m'])/max(private_budget,1)
   if grade>.105:continue
   polys=g.ribbons(ll,w);cc={k:overlap(polys,ps)for k,ps in [('retained_native',retained),('new_native',native),('special',special),('water',water)]}
   if any(v>1e-7 for v in cc.values()):continue
   # All centerline search segments are in reserved private land. Only the final
   # tail/cap may touch a named public strip; exact transverse seam is R17/R18.
   early=g.ribbons(ll[:-2],w)if len(ll)>3 else[]
   if overlap(early,roadpolys)>1e-6:continue
   found=(ll,polys,e,si,length,private_budget,grade,cc);break
  if not found:fail.append(dict(id=h['id'],reason='Higher public terminal/private-only corridor not yet found'));h.update(external_route=[],external_route_polygons_xz_m=[]);print('HELD',h['id'],flush=True);continue
  ll,polys,e,si,length,pb,grade,cc=found;h.update(external_route=ll,external_route_polygons_xz_m=polys,public_road_id=roadid,public_target_xz_m=ll[-1],public_target_evidence=e,external_width_m=w);h['court_datum_evidence'].update(chosen_public_anchor=dict(e,public_road_id=roadid,segment=si),profile_centerline_grade=grade);proof.append(dict(holding_id=h['id'],public_road_id=roadid,total_route_length_m=length,conservative_private_rise_length_m=pb,private_rise_grade=grade,exact_native_protected_overlap_m2=cc,preterminal_public_overlap_m2=0));print(proof[-1],flush=True)
 l['unresolved_external_routes']=fail;l['summary']['unresolved_external_routes']=len(fail)
 for name in ['native_local.json','compile_report.json','owner_route_source_snapshot.json']:(out/name).write_bytes((src/name).read_bytes())
 l['native_local']=g.ref(out/'native_local.json');g.write(out/'selected_layout.json',l);g.write(out/'private_entry_source_audit.json',dict(source=g.ref(src/'selected_layout.json'),entries=proof,held=fail,status='Private-only XZ corridor source. Actual public seam/profile/retained-side proof remains R17/R18.'))
 for name in['access','furnish']:
  text=(SOURCE/(name+'.py')).read_text()
  if name=='access':text=text.replace("allowed=raster([h['holding_polygon_xz_m']]+", "allowed=raster(h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])+")
  else:text=text.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
  mod=types.ModuleType(__package__+'.b07_private_'+name);mod.__package__=__package__;exec(compile(text,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
 proposal=g.load(src/'ground_proposal.json');proposal.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'))
 for cl in proposal['clusters']:
  h=next(h for h in l['holdings']if h['id']in cl['holding_ids']);cl.update(datum=h['court_datum_evidence'],entry_routes=[dict(id=h['id']+':ENTRY',width_m=h['external_width_m'],polyline_xz_m=h['external_route'],polygons_xz_m=h['external_route_polygons_xz_m'],public_road_id=h['public_road_id'],public_target=h.get('public_target_evidence'))])
 g.write(out/'ground_proposal.json',proposal)
if __name__=='__main__':run()
