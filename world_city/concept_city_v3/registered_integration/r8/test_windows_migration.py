import hashlib,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('windows_extract',ROOT/'Extract-VG-Windows.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MigrationTests(unittest.TestCase):
 def test_reversible_names(self):
  self.assertEqual(m.windows_path('tests/ROAD:A.json'),'tests/ROAD%3AA.json')
  self.assertEqual(m.windows_path('tests/ROAD%3AA.json'),'tests/ROAD%253AA.json')
  self.assertEqual(m.windows_path('CON.txt'),'%43ON.txt')
  self.assertEqual(m.windows_path('x. '),'x.%20')
 def test_extended_windows_paths(self):
  self.assertEqual(m.extended_windows_string(r'D:\Project\VG\stage'),r'\\?\D:\Project\VG\stage')
  self.assertEqual(m.extended_windows_string(r'\\server\share\stage'),r'\\?\UNC\server\share\stage')
  self.assertEqual(m.extended_windows_string(r'\\?\D:\stage'),r'\\?\D:\stage')
 def test_unsafe_and_case_collisions(self):
  for name in('/root/a','../a','a/../../b','a\\b'):
   with self.assertRaises(ValueError):m.windows_path(name)
  with self.assertRaises(ValueError):m.mapping(['File.json','file.json'])
 def test_extract_preserves_every_byte(self):
  with tempfile.TemporaryDirectory()as td:
   td=Path(td);zpath=td/'a.zip';files={'code.py':b'# source\n','geometry/ROAD:A.json':b'{"original":"ROAD:A"}\n'}
   with zipfile.ZipFile(zpath,'w')as z:
    for n,b in files.items():z.writestr(n,b)
    z.writestr(m.MANIFEST,json.dumps({'files':{n:hashlib.sha256(b).hexdigest()for n,b in files.items()}}))
   r=m.extract(zpath,td/'fresh',m.digest(zpath));self.assertTrue(r['all_file_bytes_match']);self.assertEqual(r['renamed_count'],1)
   for n,b in files.items():self.assertEqual((td/'fresh'/m.windows_path(n)).read_bytes(),b)
   with self.assertRaises(ValueError):m.extract(zpath,td/'fresh',m.digest(zpath))
 def test_bad_archive_hash_never_creates_destination(self):
  with tempfile.TemporaryDirectory()as td:
   td=Path(td);p=td/'x';p.write_bytes(b'data')
   with self.assertRaises(ValueError):m.extract(p,td/'fresh','wrong')
   self.assertFalse((td/'fresh').exists())
if __name__=='__main__':unittest.main()
