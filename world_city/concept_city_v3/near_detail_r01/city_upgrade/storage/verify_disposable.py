from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
pairs=[('world_city/concept_city_v3/checkpoints/playable_r01/city_playable_r01_source_runtime.zip','world_city/concept_city_v3/checkpoints/playable_r01/clean_extract'),('world_city/concept_city_v3/checkpoints/playable_r02/city_playable_r02_source_runtime.zip','world_city/concept_city_v3/checkpoints/playable_r02/clean_extract'),('world_city/concept_city_v3/near_detail_r01/distribution/near_detail_source_r01.zip','world_city/concept_city_v3/near_detail_r01/distribution/clean_source_extract')]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
reports=[]
for archive,folder in pairs:
 z=ROOT/archive;d=ROOT/folder;entries=[];issues=[]
 with zipfile.ZipFile(z) as f:
  names={i.filename for i in f.infolist() if not i.is_dir()};actual={str(x.relative_to(d)) for x in d.rglob('*') if x.is_file()}
  if actual!=names:issues.append({'unexpected':sorted(actual-names),'missing':sorted(names-actual)})
  for n in sorted(actual&names):
   p=d/n;fs=sha(p);zs=hashlib.sha256(f.read(n)).hexdigest()
   if fs!=zs:issues.append({'mismatch':n})
   entries.append({'path':n,'bytes':p.stat().st_size,'sha256':fs,'archive_same':fs==zs,'links':p.stat().st_nlink})
 r={'archive':archive,'archive_sha256':sha(z),'directory':folder,'status':'PASS' if not issues else 'BLOCK','issues':issues,'files':entries,'bytes':sum(e['bytes'] for e in entries)};reports.append(r);print(folder,r['status'],len(entries),r['bytes'],flush=True)
(OUT/'disposable_verification.json').write_text(json.dumps({'scope':'Exact archive-member equality check only. No deletion performed. Original archives, source and evidence outside these extraction copies remain.','directories':reports},indent=2))
