from author_plan import *
def main():
 plan=load(HERE/'design_plan.json');pack=load(HERE/'resolved_placements.json');out=[]
 for h in plan['holdings']:
  spec=next(s for s in plan['sources']if s['id'].endswith('estate_boundary'if h['id'].startswith('B03')else'abbey_boundary'));s=load(ROOT/spec['source']['path']);e=s['extensions'];regions=e['shared_existing_native_edge_omissions_xz_m'];interfaces=[]
  if regions:
   m,x,z=p1.grid_for(regions);lab,n=ndimage.label(m,np.ones((3,3)))
   for i in range(1,n+1):
    zz,xx=np.where(lab==i);bb=[float(x+min(xx)*.5),float(z+min(zz)*.5),float(x+(max(xx)+1)*.5),float(z+(max(zz)+1)*.5)];poly=rect(*bb);ids=sorted(set(r['id']for r in plan['native_reservations']if geo.positive_area_overlap(poly,r['polygon_xz_m'],0)));interfaces.append({'bounds_xz_m':bb,'omitted_source_band_area_m2':len(xx)*.25,'preserved_native_owner_ids':ids,'purpose':'Preserve inherited estate access/infrastructure crossing; new boundary terminates outside its conservative1.5m reservation. No new gate or inherited clearance certification.'})
  m,x,z=p1.grid_for(h['polygon_parts_xz_m']);walk=next(r for r in plan['internal_routes']if r['holding_id']==h['id'])['ribbon_polygons_xz_m'];foot=[r['polygon_xz_m']for r in h['native_boundary_source_regions']];classes=collections.Counter();edges=[]
  for iz,ix in np.argwhere(m):
   p=rect(x+ix*.5,z+iz*.5,x+(ix+1)*.5,z+(iz+1)*.5)
   for dz,dx,ii,jj in[(0,-1,3,0),(0,1,1,2),(-1,0,0,1),(1,0,2,3)]:
    zz,xx=iz+dz,ix+dx
    if 0<=zz<m.shape[0]and 0<=xx<m.shape[1]and m[zz,xx]:continue
    if any(geo.positive_area_overlap(p,q,0)for q in foot):kind='new_native_boundary_band'
    elif any(geo.positive_area_overlap(p,q,0)for q in regions):kind='preserved_existing_infrastructure_interface'
    elif any(geo.positive_area_overlap(p,q,0)for q in e['removed_small_source_tips_xz_m']+e.get('collar_gate_full_span_omission_xz_m',[])):kind='deliberate_open_terminal_cap'
    elif any(geo.positive_area_overlap(p,q,0)for q in walk+[plan['selected_stair_fit']['candidate']['polygon_xz_m']]):kind='designed_gate_or_service_opening'
    else:kind='UNRESOLVED'
    classes[kind]+=.5;edges.append({'segment_xz_m':[p[ii],p[jj]],'class':kind})
  out.append({'holding_id':h['id'],'source_raster_perimeter_m':sum(classes.values()),'perimeter_by_function_m':dict(classes),'inherited_interfaces':interfaces,'perimeter_edges':edges,'unsupported_boundary_spans':e['uncovered_boundary_spans'],'new_boundary_requires_closed_loop':False,'boundary_intent':'Connected productive margins retain five inherited estate infrastructure crossings; new abbey garden has its explicit open gate. No continuous enclosure is claimed across preserved access interfaces.'});assert not classes['UNRESOLVED'],classes
 write(HERE/'boundary_coverage.json',{'source_plan':ref(HERE/'design_plan.json'),'native_pack':ref(HERE/'resolved_placements.json'),'method':'Exact0.5m source-domain perimeter ledger; native common face/edge continuity is checked independently in native_tests.json. Existing interfaces remain baseline-owned.','rows':out,'all_source_perimeter_accounted':True});print([{k:v for k,v in r.items()if k!='perimeter_edges'}for r in out])
if __name__=='__main__':main()
