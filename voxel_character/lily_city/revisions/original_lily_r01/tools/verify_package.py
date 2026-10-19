"""Extract a new small closure, verify hashes and deterministic source regeneration.
Never touches the source workspace. Godot runtime checks can then run in extraction.
"""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--zip',type=Path,required=True);ap.add_argument('--extract',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args()
 if a.extract.exists() or a.report.exists():raise FileExistsError('New extraction and report required')
 dest=a.extract.resolve();dest.mkdir(parents=True)
 with zipfile.ZipFile(a.zip) as z:
  for name in z.namelist():
   if not (dest/name).resolve().is_relative_to(dest):raise ValueError('Unsafe archive member')
  z.extractall(dest)
 manifest=json.loads((dest/'CLOSURE_MANIFEST.json').read_text());bad=[n for n,v in manifest['files'].items() if not (dest/n).is_file() or (dest/n).stat().st_size!=v['bytes'] or sha(dest/n)!=v['sha256']]
 if bad:raise ValueError('Closure checksum mismatch '+str(bad))
 rev=dest/'voxel_character/lily_city/revisions/original_lily_r01';files=list((rev/'data/modules').glob('*.json'))+list((rev/'data/presets').glob('*.json'))+list((rev/'clothing_library/modules').glob('*.json'))+[rev/'data/reference.json',rev/'data/combination_rules.json']
 before={str(p.relative_to(rev)):sha(p) for p in files};index=(rev/'data/resident_review_index.json').read_bytes();runs=[]
 for script in ['tools/author.py','tools/refine_r02.py','clothing_library/generate_clothing.py','tools/residents.py']:
  result=subprocess.run([sys.executable,str(rev/script)],capture_output=True,text=True,check=True);runs.append({'script':script,'exit_code':result.returncode,'stdout':result.stdout[-1500:]})
 after={str(p.relative_to(rev)):sha(p) for p in files};assert before==after,'Regenerated source bytes differ'
 (rev/'data/resident_review_index.json').write_bytes(index)
 # Rebuild all bound source objects, without voxel compilation, and compare every cache digest.
 sys.path.insert(0,str(rev/'tools'));from assemble import assemble
 from core import digest
 index_data=json.loads(index);checks=[]
 for row in [{'path':'data/presets/lily_original.json','cache':'generated/lily_r03'}]+index_data['presets']:
  recipe=json.loads((rev/row['path']).read_text());expected=json.loads((rev/row['cache']/'manifest.json').read_text())['source_master_hash'];actual=digest(assemble(recipe)['master.json']);assert actual==expected,(row,actual,expected);checks.append({'preset':recipe['id'],'master_hash':actual})
 rebuilt=[]
 from build import build
 for recipe,cache,label in [('lily_original','generated/lily_r03','lily'),(index_data['presets'][1]['preset'],index_data['presets'][1]['cache'],'skirt')]:
  output=rev/'generated'/('extraction_rebuild_'+label);build(rev/'data/presets'/(recipe+'.json'),output)
  source=rev/cache;expected=json.loads((source/'manifest.json').read_text())['files']
  assert all(sha(output/n)==h for n,h in expected.items()),'Common-mesher rebuild differs'
  rebuilt.append({'preset':recipe,'files_identical':len(expected)})
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(rev/'tests'),'-p','test_modules.py','-v'],capture_output=True,text=True,check=True);runs.append({'script':'test_modules.py','exit_code':0,'stdout':result.stderr[-1800:]})
 report={'schema':'riverstone.character.extraction_check.v1','archive':a.zip.name,'archive_sha256':sha(a.zip),'file_hashes_pass':len(manifest['files']),'regenerated_source_files_identical':len(before),'bound_master_checks':checks,'sampled_voxel_rebuilds':rebuilt,'runs':runs,'all_passed':True,'extraction':str(dest),'runtime_check':'Run CheckOriginal/CheckResidents separately in extracted project; see companion reports.'}
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['runs','bound_master_checks']}))
if __name__=='__main__':main()
