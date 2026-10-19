"""Validate resolved route handoffs without inventing connections or acceptance."""
import copy,math,pathlib,hashlib,json,re
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir())
CLASSES={'public_corridor','junction_turn','ordinary_entry','precinct_entry','bridge_approach','native_bridge','canal_crossing','common_entry','design_grade_probe','blocked_native_negative','water_edge_negative','secured_bridge_negative','isolated_control','ordinary_court_to_door'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(ref):
 p=pathlib.Path(ref['path']);p=p if p.is_absolute()else ROOT/p
 if not p.is_file()or sha(p)!=ref['sha256']:raise ValueError('Changed or missing route source: '+str(p))
 return p

def validate(doc,check_sources=True):
 if doc.get('schema')!='riverstone.ordinary61_diagnostic_catalog.v1':raise ValueError('Wrong resolved route catalog schema')
 if doc.get('status')!='READY_FOR_ACTUAL_SCENE_REPLAY':raise ValueError('Route catalog is not released')
 if check_sources:
  for ref in doc['sources'].values():source(ref)
 routes=[];seen=set();forward=set()
 for raw in doc['routes']:
  rid=raw['id'];points=raw['points_xyz_m'];cls=raw['case_class']
  if not re.fullmatch(r'[A-Za-z0-9_.:+-]+',rid)or rid in seen or cls not in CLASSES:raise ValueError('Duplicate route ID or unsupported case class: '+rid)
  if len(points)<2 or any(len(p)!=3 or not all(math.isfinite(float(x))for x in p)for p in points):raise ValueError('Invalid finite route points: '+rid)
  if any(math.dist(p,q)<1e-8 for p,q in zip(points,points[1:])):raise ValueError('Duplicate successive route points: '+rid)
  if not raw.get('source_road_ids')and cls not in{'isolated_control','blocked_native_negative','water_edge_negative','design_grade_probe'}:raise ValueError('Missing named public ownership: '+rid)
  if cls=='design_grade_probe'and not raw.get('source_plane_owner_ids'):raise ValueError('Grade probe lacks finite public plane ownership: '+rid)
  if not raw.get('provenance'):raise ValueError('Missing authoritative route provenance: '+rid)
  if check_sources:
   for ref in raw['provenance']:source(ref)
  if not raw.get('expected_failure')and not raw.get('resolved_geometry_proof'):raise ValueError('Unresolved source centerline is not accepted: '+rid)
  if check_sources and raw.get('resolved_geometry_proof'):source(raw['resolved_geometry_proof'])
  if raw.get('expected_failure')not in{None,'blocked','ground_lost'}:raise ValueError('Unsupported negative acceptance: '+rid)
  if raw.get('expected_failure')=='blocked'and not any(k in raw for k in['expected_contact_id','expected_contact_prefix']):raise ValueError('Blocked control lacks exact native owner: '+rid)
  if raw.get('expected_failure')=='ground_lost'and 'minimum_allowed_feet_y_m'not in raw:raise ValueError('Water/edge control requires its original finite failure datum: '+rid)
  if raw.get('bridge_state','ROAD_OPEN')not in{'ROAD_OPEN','ROAD_SECURED','NAVIGATION_OPEN'}:raise ValueError('Unreviewed bridge pose: '+rid)
  row=copy.deepcopy(raw);row['points']=row.pop('points_xyz_m');row['group']=rid;routes.append(row);seen.add(rid);forward.add(rid)
  if raw.get('bidirectional'):
   q=copy.deepcopy(row);q['id']=rid+'_REVERSE';q['points']=list(reversed(row['points']))
   if q['id']in seen:raise ValueError('Duplicate reverse route')
   routes.append(q);seen.add(q['id'])
 if any(r.get('holding_id')for r in routes)and not doc.get('activation_requirements',{}).get('native_packs'):raise ValueError('Released holding routes lack exact native activation requirements')
 coverage=doc['coverage']
 if check_sources:
  inventory=json.loads(source(doc['sources']['primary_inventory']).read_bytes());candidates=json.loads(source(doc['sources']['ordinary_entry_candidates']).read_bytes());b15=json.loads(source(doc['sources']['b15_entries']).read_bytes())
  exact=dict(public_roads={r['id']for r in inventory['roads']},primary_network_goals={r['id']for r in inventory['primary_network_goals']},ordinary_entries={r['id']for r in candidates['entries']}|{r['id']for r in b15['roots']})
  for key,ids in exact.items():
   if set(coverage['required_'+key+'_ids'])!=ids:raise ValueError('Coverage differs from bound authoritative inventory: '+key)
  ready_holdings=set()
  for name in['ready_entries','ready_entries_next18','ready_entries_next20']:
   if name in doc['sources']:ready_holdings.update(json.loads(source(doc['sources'][name]).read_bytes())['accepted_holding_ids'])
  if ready_holdings:
   expected={r['id']for r in candidates['entries']if r['holding_id']in ready_holdings}
   if {r['id']for r in coverage['ordinary_entries']if r['status']=='accepted'}!=expected:raise ValueError('Accepted entry coverage differs from released holding lists and fixed B15 roots')
 for name in['public_roads','primary_network_goals','ordinary_entries']:
  rows=coverage[name];ids=set()
  for row in rows:
   if row['id']in ids:raise ValueError('Duplicate coverage owner: '+row['id'])
   ids.add(row['id'])
   if row['status']=='accepted':
    if not row.get('route_ids')or not set(row['route_ids'])<=forward:raise ValueError('Accepted coverage has no resolved routes: '+row['id'])
   elif row['status']in{'held','retired'}:
    if not row.get('reason')or not row.get('source'):raise ValueError('Held or retired coverage lacks reason and authority')
    if check_sources:source(row['source'])
   else:raise ValueError('Unrecognized coverage state')
  if set(coverage['required_'+name+'_ids'])!=ids:raise ValueError('Coverage ledger omits required '+name)
 for row in routes:
  if row['case_class']in{'public_corridor','junction_turn','ordinary_entry','precinct_entry','bridge_approach','native_bridge','canal_crossing','common_entry','design_grade_probe','ordinary_court_to_door'}and not row.get('bidirectional'):raise ValueError('Positive public route must be bidirectional: '+row['id'])
 return routes
