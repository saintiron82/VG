import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('join_vg',ROOT/'Reassemble-VG.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class VolumeTests(unittest.TestCase):
 def make(self,p):
  data=[b'abc',b'defg'];parts=[]
  for i,b in enumerate(data,1):
   f=p/f'part{i}';f.write_bytes(b);parts.append(dict(name=f.name,order=i,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
  mf=p/'manifest.json';mf.write_text(json.dumps({'volumes':parts,'archive':{'sha256':hashlib.sha256(b''.join(data)).hexdigest(),'bytes':7}}));return mf
 def test_join_and_existing_rejection(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);mf=self.make(p);r=m.reassemble(mf,p,p/'out');self.assertEqual((p/'out').read_bytes(),b'abcdefg');self.assertEqual(r['status'],'pass')
   with self.assertRaises(ValueError):m.reassemble(mf,p,p/'out')
 def test_bad_part_no_output(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);mf=self.make(p);(p/'part2').write_bytes(b'bad!')
   with self.assertRaises(ValueError):m.reassemble(mf,p,p/'out')
   self.assertFalse((p/'out').exists())
 def test_order_and_path_rejection(self):
  for key,value in [('order',2),('name','../unsafe')]:
   with tempfile.TemporaryDirectory()as td:
    p=Path(td);mf=self.make(p);data=json.loads(mf.read_text());data['volumes'][0][key]=value;mf.write_text(json.dumps(data))
    with self.assertRaises(ValueError):m.reassemble(mf,p,p/'out')
    self.assertFalse((p/'out').exists())
if __name__=='__main__':unittest.main()
