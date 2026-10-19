"""Losslessly compact master JSON while retaining original bytes and semantic digest."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'common'))
from core import digest

def compact(directory):
 p=directory/'master.json';raw=p.read_bytes();master=json.loads(raw);manifest_path=directory/'manifest.json';manifest=json.loads(manifest_path.read_text());before=digest(master)
 assert before==manifest['master_hash']
 archive=directory/'master.original_format.json.gz'
 if not archive.exists():
  with gzip.GzipFile(filename=str(archive),mode='wb',mtime=0) as f:f.write(raw)
 assert json.loads(gzip.decompress(archive.read_bytes()))==master
 p.write_text(json.dumps(master,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
 assert digest(json.loads(p.read_text()))==before
 for f in [p,archive]:manifest['files'][f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
 manifest['storage_note']='Lossless whitespace compaction; original bytes retained in master.original_format.json.gz. Semantic master_hash unchanged.'
 manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'master_hash':before,'values_unchanged':True,'before_bytes':len(raw),'compact_bytes':p.stat().st_size}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('directory',type=Path);compact(a.parse_args().directory.resolve())
