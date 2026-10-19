import hashlib,json,zipfile,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'world_city/concept_city_v3/checkpoints'
source=BASE/'concept_city_v3_full_migration_20261018T140107Z.zip'
out=BASE/'migration_volumes_1401';out.mkdir(exist_ok=False)
limit=450*1024*1024;parts=[];overall=hashlib.sha256()
with source.open('rb')as f:
 i=0
 while True:
  first=f.read(1024*1024)
  if not first:break
  i+=1;p=out/f'VG_full_20261018T140107Z.zip.part{i:03d}';h=hashlib.sha256();count=0
  with p.open('xb')as w:
   b=first
   while b:
    w.write(b);h.update(b);overall.update(b);count+=len(b)
    if count==limit:break
    b=f.read(min(1024*1024,limit-count))
  check=hashlib.sha256()
  with p.open('rb')as r:
   for b in iter(lambda:r.read(1024*1024),b''):check.update(b)
  assert check.hexdigest()==h.hexdigest()
  parts.append(dict(order=i,name=p.name,bytes=count,sha256=h.hexdigest()));print('sealed',p.name,count,flush=True)
assert overall.hexdigest()=='a9d31adabfe1a95c20f6e7b18721945a66acf22279d98382526bbec8496ff8ea'
spec=importlib.util.spec_from_file_location('win',ROOT/'Extract-VG-Windows.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with zipfile.ZipFile(source)as z:
 mapping=mod.mapping(z.namelist());renamed={k:v for k,v in mapping.items()if k!=v};manifest=json.loads(z.read('INTEGRATED_R8_MANIFEST.json'))
report=dict(schema='riverstone.migration.ordered_volumes.v1',archive=dict(name=source.name,sha256=overall.hexdigest(),bytes=source.stat().st_size,entries=len(mapping),project_files=len(manifest['files'])),volumes=parts,join_method='Binary concatenation in order, then verify the complete SHA-256 before extraction.',windows=dict(reversible_filename_escapes=len(renamed),casefold_collisions=0,extractor='Extract-VG-Windows.py',original_archive_must_be_retained=True),scope='Entire recovered RPG/voxel project as captured at 2026-10-18T14:01:07Z, except reproducible caches, engine, credentials and nested backup archives; original backup archives indexed in the internal manifest. Subsequent source/validation changes require final overlay.',animation_limitation='Only recovered older animation source is present. The latest pre-loss B7 animation source is unavailable; retained video evidence is not a substitute for that source.',validation='Full archive bytes and canonical build closure verified. Final traversal and clean-extract smoke are recorded separately; this snapshot is not a completion claim.')
(out/'VG_VOLUME_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n')
(ROOT/'world_city/concept_city_v3/registered_integration/r8/migration_windows_names_1413.json').write_text(json.dumps({'archive_sha256':overall.hexdigest(),'casefold_collisions':0,'renamed_count':len(renamed),'renames':renamed},indent=2)+'\n')
print(json.dumps(report,indent=2))
