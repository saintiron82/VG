"""One finite canonical traffic domain for R18 constraints, grid and ownership.

The 16 failed corridors retain their original traffic widths and finite round
joins/caps. The accepted outer-section handoff contributes bounded pieces of
retained roads; it does not promote whole passing roads or terrain shoulders.
"""
import json
from .survey import ROAD_IDS,HERE
from ..r17_district_batches import author as a
from ..r01_ownership import author as ownership
OUTER_PATH=a.CITY/'traversal_r5/revisions/r06_r8_precinct/retained_junction_extensions_r01/fixed_interfaces_outer_r2.json'
OUTER_SHA256='84fca852a3196cf717828a13bba7c6a72b993cb4f0b4a9ed70a12a221c80497a'
INVENTORY_PATH=a.CITY/'traversal_r5/revisions/r06_r8_precinct/primary_inventory/inventory.json'

def source_ref(path):return dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path))
def outer_handoff():
 if a.sha(OUTER_PATH)!=OUTER_SHA256:raise ValueError('Changed sealed outer-section handoff')
 return json.loads(OUTER_PATH.read_bytes())
def records():
 data=json.loads(INVENTORY_PATH.read_bytes());rows=[]
 for r in data['roads']:
  if r['id']not in ROAD_IDS:continue
  for i,p in enumerate(ownership.corridor(r['polyline_xz_m'],r['width_m'])):
   rows.append(dict(id=r['id']+':CANONICAL:'+str(i),road_id=r['id'],polygon_xz_m=p,kind='original_traffic'))
 assert {r['road_id']for r in rows}==set(ROAD_IDS)
 for r in outer_handoff()['junction_extension_masks']:rows.append(dict(r,kind='bounded_retained_junction_extension'))
 return rows

def polygons():return[r['polygon_xz_m']for r in records()]
def source_refs():return[source_ref(OUTER_PATH),source_ref(INVENTORY_PATH),source_ref(__import__('pathlib').Path(ownership.__file__)),source_ref(__import__('pathlib').Path(__file__))]
