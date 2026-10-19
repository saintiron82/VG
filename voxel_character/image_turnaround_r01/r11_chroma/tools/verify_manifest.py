from pathlib import Path
import json,hashlib,sys
B=Path(__file__).resolve().parents[1];R=B.parents[2]
p=B/(sys.argv[1]if len(sys.argv)>1 else'evidence/closure_first_three_failures.json');j=json.loads(p.read_text());bad=[]
for row in j['files']:
 f=R/row['path']
 if not f.is_file()or hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']or f.stat().st_size!=row['bytes']:bad.append(row['path'])
print(json.dumps({'manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checked':len(j['files']),'mismatch':bad,'integrity_pass':not bad,'art_or_sixview_pass':False},indent=2));sys.exit(bool(bad))
