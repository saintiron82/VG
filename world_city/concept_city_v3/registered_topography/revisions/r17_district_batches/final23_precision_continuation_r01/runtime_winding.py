"""Ten recognized source-row-bound rendering precision exceptions only.

Binding uses exact source XYZ and one unique final-scene row per approved case.
Only the derived runtime scene is changed. All precise physical ownership and
support reports continue to refer to the authored source, not rounded normals.
"""
import copy,hashlib,json,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent

def canonical_sha(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def normal(t):
 u=[t[1][k]-t[0][k]for k in range(3)];v=[t[2][k]-t[0][k]for k in range(3)];return[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
def contract():return json.loads((HERE/'runtime_winding_contract.json').read_bytes())
def validate_contract(c):
 if len(c['cases'])!=10:raise ValueError('Expected exactly ten recognized source cases')
 for r in c['cases']:
  if canonical_sha(r['precise_source_vertices_xyz_m'])!=r['source_triangle_sha256']:raise ValueError('Changed precise source')
  before=[[f32(x)for x in v]for v in r['precise_source_vertices_xyz_m']];after=r['runtime_after_vertices_xyz_m']
  if before!=r['runtime_before_vertices_xyz_m'] or sorted(map(tuple,before))!=sorted(map(tuple,after)):raise ValueError('Changed runtime vertex set')
  if normal(before)[1]>=0 or normal(after)[1]<=0:raise ValueError('Not a recognized nonzero inversion')

def bind_scene(scene,source_scene_ref=None):
 c=contract();validate_contract(c);by= {};matches={r['id']:[]for r in c['cases']}
 for r in c['cases']:by.setdefault((r['material'],r['source_triangle_sha256']),[]).append(r)
 for material,vs in scene['surfaces'].items():
  if material not in {r['material']for r in c['cases']}:continue
  for i in range(len(vs)//3):
   t=vs[3*i:3*i+3]
   for r in by.get((material,canonical_sha(t)),[]):
    if t==r['precise_source_vertices_xyz_m']:matches[r['id']].append(i)
 rows=[]
 for r in c['cases']:
  if len(matches[r['id']])!=1:raise ValueError('Source case is missing or ambiguous: '+r['id']+' '+str(matches[r['id']]))
  rows.append(dict(case_id=r['id'],material=r['material'],scene_triangle_index=matches[r['id']][0],source_producer=c['source_producer'],producer_row=r['producer_row'],source_triangle_sha256=r['source_triangle_sha256'],precise_source_vertices_xyz_m=r['precise_source_vertices_xyz_m'],runtime_before_vertices_xyz_m=r['runtime_before_vertices_xyz_m'],runtime_after_vertices_xyz_m=r['runtime_after_vertices_xyz_m']))
 return dict(schema='riverstone.final23.runtime_precision_binding.v1',implementation_refs=[dict(path=str((HERE/n).relative_to(HERE.parents[5])),sha256=hashlib.sha256((HERE/n).read_bytes()).hexdigest())for n in ('runtime_winding.py','apply_file.py','runtime_winding_contract.json','source_retriangulation_ledger.json')],source_scene=source_scene_ref,source_scene_canonical_sha256=canonical_sha(scene),contract_sha256=hashlib.sha256((HERE/'runtime_winding_contract.json').read_bytes()).hexdigest(),rows=rows,policy=c['policy'])

def apply_runtime(scene,binding):
 c=contract();validate_contract(c)
 for r in binding['implementation_refs']:
  if hashlib.sha256((HERE.parents[5]/r['path']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed bound precision implementation')
 if canonical_sha(scene)!=binding['source_scene_canonical_sha256']:raise ValueError('Changed bound authored scene')
 if hashlib.sha256((HERE/'runtime_winding_contract.json').read_bytes()).hexdigest()!=binding['contract_sha256']:raise ValueError('Changed precision contract')
 if len(binding['rows'])!=10 or {r['case_id']for r in binding['rows']}!={r['id']for r in c['cases']}:raise ValueError('Incomplete or unrecognized override set')
 known={r['id']:r for r in c['cases']};out=copy.deepcopy(scene);seen=set()
 for r in binding['rows']:
  k=known[r['case_id']];key=(r['material'],r['scene_triangle_index']);vs=scene['surfaces'][r['material']];i=r['scene_triangle_index']
  if key in seen:raise ValueError('Repeated scene row')
  seen.add(key)
  if r['producer_row']!=k['producer_row']or r['source_producer']!=c['source_producer']:raise ValueError('Changed producer ownership')
  if vs[3*i:3*i+3]!=k['precise_source_vertices_xyz_m']or r['source_triangle_sha256']!=k['source_triangle_sha256']:raise ValueError('Changed bound source row')
  if r['runtime_after_vertices_xyz_m']!=k['runtime_after_vertices_xyz_m']:raise ValueError('Changed runtime override')
  out['surfaces'][r['material']][3*i:3*i+3]=copy.deepcopy(k['runtime_after_vertices_xyz_m'])
 return out
