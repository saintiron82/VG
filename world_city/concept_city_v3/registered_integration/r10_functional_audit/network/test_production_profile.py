import unittest,pathlib,json,hashlib
from route_support_profile import Hit,ProfileError,guard_support_ray
N=pathlib.Path(__file__).resolve().parent;O=N/'port_full_chain';read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class ProductionTests(unittest.TestCase):
 def test_exact_consumer_arrays(self):
  p=read(O/'production_routes_r01.json');r=read(O/'replay_r01/prepared_production_r04.json');rows={x['id']:x for x in r['routes']}
  self.assertEqual(len(p['routes']),4)
  for x in p['routes']:self.assertEqual(x,rows[x['id']])
 def test_all_guard_queries_accounted(self):
  for r in read(O/'production_profile_ledger_r01.json')['routes']:
   g=r['analytical_support_input_guard'];self.assertEqual(g['status'],'PASS');self.assertEqual(g['failures'],[]);self.assertEqual(g['support_queries'],4*g['poses_checked'])
 def test_source_bindings(self):
  d=read(O/'production_routes_r01.json')
  for r in list(d['sources'].values())+list(d['surface_sources'].values()):self.assertEqual(sha(pathlib.Path(r['path'])),r['sha256'])
 def test_reverse_parity(self):
  d={r['id']:r for r in read(O/'production_routes_r01.json')['routes']}
  for k,r in d.items():
   if not k.endswith('_REVERSE'):self.assertEqual(d[k+'_REVERSE']['points'],r['points'][::-1])
 def test_actual_original_bad_rays_rejected(self):
  count=0
  for r in read(O/'height_hint_diagnostic.json')['results']:
   for s in r['supports']:
    if not s['ray_starts_below_contract']:continue
    h=Hit('contract',s['exact_contract_surface']['triangle_index'],s['exact_contract_surface']['y_m'],1,'source-bound-in-diagnostic')
    with self.assertRaisesRegex(ProfileError,'RAY_START_NOT_ABOVE'):guard_support_ray(r['original_pose_hint_xyz_m'][1],h)
    count+=1
  self.assertEqual(count,6)
if __name__=='__main__':unittest.main()
