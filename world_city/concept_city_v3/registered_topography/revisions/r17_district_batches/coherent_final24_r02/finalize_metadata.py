"""Bind actual incident sheets and the source continuation without geometry edits."""
import json
from .prepare import HERE,REQUEST,load,write,ref
from .. import author as a

def run():
 request=json.loads(REQUEST.read_bytes());hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());risers=[]
 for hid,b in request['profile_bindings'].items():
  source=load(b);node=source;seen=set()
  while isinstance(node,dict):
   for row in node.get('vertical_risers',[]):
    key=a.canonical_sha(row)
    if key not in seen:risers.append(dict(row,holding_id=hid,source_profile=b));seen.add(key)
   node=node.get('result')
 continuation=ref(a.CITY/'assemblies/ordinary/registered/district_fabric_r01/final24_source_continuation_r01/handoff.json');data=load(continuation)
 updated=dict(hand,explicit_profile_risers=risers,source_continuation=continuation,step_collision_contract=request['step_collision_contract'],prior_identical_geometry_handoff=ref(HERE/'physical_owner_handoff_r02.json'))
 write('physical_owner_handoff_r03.json',updated);native=json.loads((HERE/'native_pack_ready_r02.json').read_bytes());native.update(terrain_handoff=ref(HERE/'physical_owner_handoff_r03.json'),source_continuation=continuation,step_collision_contract=request['step_collision_contract'],summary=hand['summary']);write('native_pack_ready_r03.json',native)
 write('incident_metadata_parity_r01.json',dict(passed=all(updated[k]==hand[k]for k in ['rendered_plane_owners','physical_earth_owners','native_holes','public_fixed_regions','retirement_records']),prior=ref(HERE/'physical_owner_handoff_r02.json'),current=ref(HERE/'physical_owner_handoff_r03.json'),explicit_private_risers=risers,source_continuation=continuation,policy='Only the omitted incident-riser metadata is corrected. No plane, polygon, XYZ, native pose or retirement changes.'))
 print('Bound',len(risers),'explicit private incident sheets',flush=True)
if __name__=='__main__':run()
