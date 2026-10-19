import json,types
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite
from ..noble_terminal_diagnosis_r01 import diagnose
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
source=a.HERE/'final_district_profiles_r02/BLOCK_001_R8_C003.json';d=json.loads(source.read_bytes());c=d['candidate'];solver=types.FunctionType(finite.solve.__code__,dict(finite.solve.__globals__,regeneration=diagnose),argdefs=finite.solve.__defaults__);r=solver(d['private_domain_polygons_xz_m'],d['court_fixed_regions']+d['public_fixed_regions'],lambda p:c['floor_y_m'],pitch=1.,seam_points=[p for r in d['court_fixed_regions']+d['public_fixed_regions']for p in r['polygon_xz_m']]);write(HERE/'BLOCK_001_R8_C003.json',dict(source=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),result=r,activation=False));print(r['status'],r.get('diagnostic'))
