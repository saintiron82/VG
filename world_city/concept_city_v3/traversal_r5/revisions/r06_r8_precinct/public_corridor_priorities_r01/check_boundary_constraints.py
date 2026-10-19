import hashlib,importlib.util,json,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3'
spec=importlib.util.spec_from_file_location('cap_geometry',CITY/'assemblies/property/registered/public_lane_repairs_r01/inspect_contacts.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
p=read(H/'priorities.json');inv=read(H.parent/'primary_inventory/inventory.json');cp=CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json';c=read(cp)
roads={r['id']:r for r in inv['roads']};water=[]
for rid in p['minimum_public_ground_corridors']:
 r=roads[rid];masks=list(g.ownership.corridor(r['polyline_xz_m'],r['width_m']));rr=[]
 for w in c['water_domain_polygons']:
  assert g.geo.is_convex_polygon(w['polygon_xz_m'])
  hits=g.disjoint_intersections(w['polygon_xz_m'],masks)
  if hits:rr.append({'surface_id':w['surface_id'],'water_segment_index':w.get('segment_index'),'intersection_polygons_xz_m':hits,'unique_pair_area_m2':sum(g.geo.polygon_area(q)for q in hits)})
 if rr:water.append({'road_id':rid,'width_m':r['width_m'],'water_intersections':rr,'unique_water_area_m2':sum(q['unique_pair_area_m2']for q in rr),'classification':'Finite water domain conflict to reconcile against actual deck/bridge/bed ownership. This is not permission to fill water.'})
retained=[q for q in p['full_width_shared_domains']if q['a_is_regeneration_candidate']!=q['b_is_regeneration_candidate']];ded=[q['roads']for q in retained if 'MAIN_BRIDGE'in q['roads']or'PORT_BRIDGE_TIE'in q['roads']]
seams=[]
for h in c['property_terminal_handoffs']:
 for rid in p['minimum_public_ground_corridors']:
  masks=list(g.ownership.corridor(roads[rid]['polyline_xz_m'],roads[rid]['width_m']));hits=g.disjoint_intersections(h['polygon_xz_m'],masks)
  if hits:seams.append({'road_id':rid,'property_id':h['property_id'],'owner_id':h['owner_id'],'triangle_xyz_m':h['triangle_xyz_m'],'full_width_overlap_polygons_xz_m':hits})
out={'schema':'riverstone.public_corridor_boundary_constraints.v1','sources':{'priorities':ref(H/'priorities.json'),'canonical_contract':ref(cp),'actual_inventory':ref(H.parent/'primary_inventory/inventory.json'),'finite_clip_implementation':ref(pathlib.Path(g.__file__))},'repair_to_not_regenerated_road_pairs':len(retained),'of_those_previously_passing_pairs':len(retained)-len(ded),'of_those_dedicated_bridge_interface_pairs':ded,'finite_water_constraints':water,'retained_property_terminal_triangles':seams,'scope':'Read-only exact traffic footprint intersections. Water record areas are disjoint within each finite water polygon; no support, grade or traversal acceptance. Property records are shared public triangles from sealed r14, additional later r15/r16/r17 interfaces remain required by the actual composed scene.'}
with(H/'boundary_constraints.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps({'report':ref(H/'boundary_constraints.json'),'water':[(q['road_id'],q['unique_water_area_m2'])for q in water],'existing_property_handoff_intersections':len(seams),'repair_to_previously_passed_pairs':out['of_those_previously_passing_pairs']}))
