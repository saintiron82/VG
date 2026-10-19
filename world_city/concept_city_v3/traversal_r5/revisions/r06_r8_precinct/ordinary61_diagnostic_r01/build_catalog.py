"""Create source-exact ordinary diagnostics. Final binding is supplied separately."""
import collections,copy,hashlib,json,pathlib,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(H));import catalog
read=lambda p:json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 source=H.parent/'public_network_r18_r01/route_catalog_61_ready_r05.json';d=read(source);d['schema']='riverstone.ordinary61_diagnostic_catalog.v1';d['sources']['whole_412_predecessor']=ref(source)
 d['routes']=[r for r in d['routes']if r['case_class']=='ordinary_entry'and r.get('holding_id')];assert len(d['routes'])==61
 selected={r['holding_id']for r in d['routes']};branches=[]
 for name in ['ready_entries','ready_entries_next18','ready_entries_next20']:
  source_ref=d['sources'][name];handoff=read(catalog.source(source_ref));entry={r['holding_id']:r for r in d['routes']};byholding=collections.defaultdict(list)
  for row in handoff['internal_door_routes']:byholding[row['holding_id']].append(row)
  for holding in sorted(handoff['accepted_holding_ids']):
   row=sorted(byholding[holding],key=lambda r:r['id'])[0];r=entry[holding]
   d['routes'].append(dict(id='DIAG_DOOR:'+holding,case_class='ordinary_court_to_door',points_xyz_m=row['polyline_xyz_m'],source_road_ids=r['source_road_ids'],test_scope='One exact source exterior door-lip to court-gate branch per released holding, both directions; no interior entry.',provenance=[source_ref],resolved_geometry_proof=source_ref,bidirectional=True,holding_id=holding,source_route_id=row['id'],door_id=row['door_id'],source_width_m=row['width_m'],source_waypoints_preserved=True))
   branches.append(dict(holding_id=holding,selected_source_route_id=row['id'],available_source_door_routes=len(byholding[holding]),selection='Lexicographically first exact source door route; not shortest or easiest.'))
 for key in ['public_roads','primary_network_goals','ordinary_entries']:
  for row in d['coverage'][key]:
   if key=='ordinary_entries'and row.get('holding_id')in selected:continue
   row.update(status='held',reason='Outside this diagnostic runtime subset. The immutable 412-case predecessor retains its original accepted/held status.',source=ref(source));row.pop('route_ids',None)
 d['activation_requirements']['native_packs']=[r for r in d['activation_requirements']['native_packs']if r!=d['sources']['noble_native_pack']]
 d['activation_requirements']['collision_contracts']=[]
 d['diagnostic_scope']=dict(ordinary_holdings=61,entry_directions=122,representative_door_directions=122,excluded='B15, noble entries, north-service and all other public/main-network paths',source_door_selection=branches,whole_network_claim=False)
 d['limits']=['Nonvisual diagnostic snapshot only; final noble/native and north repair sources are pending.','Uses the unchanged controller and loader. No geometry/controller repair occurs in this folder.','All previous runtime failures and the 412-case source catalog remain immutable.','Passing this subset cannot release the whole public network or all doors.','Source requirements must be rebound to exact approved append-normalization ledgers before actual extraction.']
 expanded=catalog.validate(d);assert len(expanded)==244
 with(H/'route_catalog_source_r01.json').open('x')as f:json.dump(d,f,indent=2);f.write('\n')
 print(json.dumps(dict(catalog=ref(H/'route_catalog_source_r01.json'),cases=len(expanded),classes=dict(collections.Counter(r['case_class']for r in expanded))),indent=2))
if __name__=='__main__':main()
