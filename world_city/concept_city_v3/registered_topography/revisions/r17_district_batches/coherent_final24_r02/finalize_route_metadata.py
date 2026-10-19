"""Correct route provenance only; every lifted coordinate remains unchanged."""
import json
from .prepare import HERE,write,ref
from .. import author as a

def run():
 old=json.loads((HERE/'route_handoff_ready_r04.json').read_bytes())
 data=dict(old,terrain_handoff=ref(HERE/'physical_owner_handoff_r03.json'),route_geometry_source=ref(HERE/'route_handoff_ready_r04.json'),current_public_context=ref(a.CITY/'evidence/r8_district_61_noble_r02_contracts_runtime/authored_scene.json'),current_main_binding=json.loads((HERE/'accepted_source_request.json').read_bytes())['current_main_binding'],retained_public_scene_sha256='dbdd470b6d496c9828e64e018ba78a6de42cc70480e89c49632c9f4cc53ec2f1',historical_retained_public_scene_sha256=old['retained_public_scene_sha256'])
 assert data['entries']==old['entries'] and not data['failures']
 write('route_handoff_ready_r05.json',data)
if __name__=='__main__':run()
