"""Synthetic file-level test only; no controller execution or city geometry edit."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile,unittest
from test_runtime_pair import fixture
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):p.write_text(json.dumps(v,separators=(',',':'))+'\n')
class FileBindingTest(unittest.TestCase):
 def test_file_level_exact_binding_without_replay(self):
  with tempfile.TemporaryDirectory(prefix='synthetic_',dir=H)as temp:
   t=pathlib.Path(temp);auth=t/'authored';auth.mkdir();s,r,l,m=fixture();write(auth/'scene.json',s);write(t/'runtime_scene.json',r);write(t/'index.json',m)
   l.update(source=ref(auth/'scene.json'),runtime_scene=ref(t/'runtime_scene.json'),retained_source_index_map=ref(t/'index.json'),implementation=ref(ROOT/'world_city/concept_city_v3/registered_integration/r8/runtime_precision.py'));write(t/'ledger.json',l)
   flat=s['surfaces']['road'];write(auth/'collision.json',dict(scene_sha256=sha(auth/'scene.json'),source_face_indices=[['road',0],['road',1]],triangles=[[flat[i],flat[i+2],flat[i+1]]for i in [0,3]],whole_triangles_only=True))
   prepared=dict(repo_root=str(ROOT),sources={'scene':dict(path=str(auth/'scene.json'),sha256=sha(auth/'scene.json'))},implementation_hashes={},implementation_snapshots={},assets={'surface':dict(render_path=str((auth/'collision.json').relative_to(ROOT)),render_sha256=sha(auth/'collision.json'),collision_format='actual_scene_triangles')},placements={'P':dict(asset_key='surface',position_m=[0,0,0])},buildings={},routes=[dict(id='synthetic',group='synthetic',points=[[0,0,0],[.1,0,.1]],placement_ids=['P'])],coverage={'collision_audit':[dict(group='synthetic',scene_triangles=2)]},assumptions=[]);write(auth/'prepared_runtime.json',prepared)
   source=H.parent/'ordinary61_diagnostic_r01'
   for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run_batch.py']:shutil.copyfile(source/name,auth/name)
   p=subprocess.run([sys.executable,str(H/'bind_runtime.py'),'--authored-prepared',str(auth/'prepared_runtime.json'),'--runtime-ledger',str(t/'ledger.json'),'--output',str(t/'runtime')],capture_output=True,text=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
   self.assertEqual(p.returncode,0,p.stdout+p.stderr);d=json.loads((t/'runtime/prepared_runtime.json').read_bytes());proof=json.loads((t/'runtime/evidence/runtime_binding.json').read_bytes());self.assertEqual(d['routes'],prepared['routes']);self.assertEqual(d['placements'],prepared['placements']);self.assertEqual(proof['whole_scene_proof']['removed_triangles'],1);self.assertEqual(d['coverage']['collision_audit'][0]['scene_triangles'],1);self.assertFalse((t/'runtime/evidence/public_network_replay.json').exists());self.assertEqual((t/'runtime/Traversal.gd').read_bytes(),(source/'Traversal.gd').read_bytes())
if __name__=='__main__':unittest.main()
