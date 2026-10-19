"""Consume one sealed atomic native datum addendum without touching old sources."""
import json,argparse,copy
from .screen import HERE,write
from .. import author as a
SOURCE=HERE.parent/'contour_bulk_r01';CONT=HERE.parent/'entry_continuation_r01'
def run():
 parser=argparse.ArgumentParser();parser.add_argument('--path',required=True);parser.add_argument('--sha256',required=True);args=parser.parse_args();path=a.ROOT/args.path
 if a.sha(path)!=args.sha256:raise ValueError('Atomic source hash changed')
 add=json.loads(path.read_bytes());assert add['status']=='ATOMIC_SOURCE_REBIND_READY_FOR_R17_COMPOSITION';audit=json.loads((a.ROOT/add['native_audit']['path']).read_bytes());assert a.sha(a.ROOT/add['native_audit']['path'])==add['native_audit']['sha256'];assert audit['status']=='PASSED_SOURCE_REBIND_COLLISION_SCREEN'
 req=json.loads((CONT/'coherent_datum_rebind_request_r02.json').read_bytes());selected=set(req['matched_next_batch_holding_ids']);assert set(add['matched_next_batch_holding_ids'])==selected;records={r['holding_id']:r for r in add['records']};assert set(records)==selected
 source_ref=dict(path=args.path,sha256=args.sha256);layout=json.loads((SOURCE/'effective_source_layout_r03.json').read_bytes());prep=json.loads((SOURCE/'effective_prepared_parcels_r03.json').read_bytes());pack=json.loads((SOURCE/'prepared_native_pack_r03.json').read_bytes());oldlayout=copy.deepcopy(layout);oldpack=copy.deepcopy(pack);poses={r['id']:r for d in records.values()for r in d['replacement_native_placements']};doors={r['id']:r for d in records.values()for r in d['replacement_actual_doors']};bearings={r['id']:r for d in records.values()for r in d['replacement_native_earth_bearings']}
 for key,replacements in [('placements',poses),('actual_doors',doors)]:layout[key]=[replacements.get(r['id'],r)for r in layout[key]];pack[key]=[replacements.get(r['id'],r)for r in pack[key]]
 layout['holdings']=[records[r['id']]['replacement_holding']if r['id']in selected else r for r in layout['holdings']];prep['parcels']=[records[r['id']]['replacement_terrain_parcel']if r['id']in selected else r for r in prep['parcels']];prep['native_earth_bearings']=[bearings.get(r['id'],r)for r in prep['native_earth_bearings']]
 for r in prep.get('logical_owners',[]):
  if r.get('holding_id')in selected and r.get('plane_y_xz_m')is not None:r['plane_y_xz_m']=[0,0,records[r['holding_id']]['new_floor_y_m']]
 for d in(layout,prep,pack):d.setdefault('source_references',[]).append(source_ref)
 for old,new in[(oldlayout,layout),(oldpack,pack)]:
  for key in('placements','actual_doors'):
   for u,v in zip(old[key],new[key]):
    if u.get('holding_id')not in selected:assert a.canonical_sha(u)==a.canonical_sha(v)
 assert all(abs(h['floor_y_m']-records[h['id']]['new_floor_y_m'])<1e-9 for h in layout['holdings']if h['id']in selected)
 write('effective_source_layout_r03.json',layout);write('effective_prepared_parcels_r03.json',prep);write('prepared_native_pack_r03.json',pack)
 groups=json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())
 byholding={h['id']:h for h in layout['holdings']}
 for g in groups['groups']:
  g['source_holding_records']=[byholding[h['id']]for h in g['source_holding_records']]
  for r in g['gate_fixed_regions']:
   hid=r['id'].split(':COURT_DATUM')[0]
   if hid in selected:r['plane_y_xz_m']=[0,0,records[hid]['new_floor_y_m']]
  for r in g['gate_targets']:
   if r['holding_id']in selected:r['floor_y_m']=records[r['holding_id']]['new_floor_y_m']
 groups.setdefault('source_references',[]).append(source_ref);write('shared_private_groups_r03.json',groups)
 write('atomic_rebind_binding_r01.json',dict(source_addendum=source_ref,native_audit=add['native_audit'],selected_holding_ids=sorted(selected),unchanged_other_native_records=True,exact_internal_routes=add['door_routes'],source_parcel_count=len(prep['parcels']),activation=False));print('Bound',len(selected),'holdings',len(poses),'native records',len(doors),'doors',flush=True)
if __name__=='__main__':run()
