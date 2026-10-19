"""Independent unchanged common polygon-union proof of Godot planner output."""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
from collections import Counter
import road_surface_index as reference

here = Path(__file__).resolve().parent
payload = json.loads((here/'generated/godot_support_oracle_cases.json').read_text())
failures = []
counts = Counter()
for index, case in enumerate(payload['cases']):
    counts[case['label']] += 1
    if not reference.footprint_supported(case['corners_xyz_m'], case['contributing_faces'], tolerance=2e-5):
        failures.append({'case':index,'label':case['label'],'corners':case['corners_xyz_m']})
output = {'status':'PASS' if not failures else 'FAIL','checked_modules':len(payload['cases']),
          'counts':dict(counts),'failures':failures,'source':'unchanged common finite convex-union subtraction',
          'area_tolerance_m2':1e-8,'float32_plane_tolerance_m':2e-5,'whole_city_coverage_pass':False}
(here/'godot_support_oracle_report.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output))
sys.exit(bool(failures))
