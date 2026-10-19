"""Wait for the next committed batch result; no compiling or mutation."""
import argparse,json,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--after',type=int,required=True);x=p.parse_args()
path=Path(__file__).with_name('compiled')/'manifest.json'
while True:
    m=json.loads(path.read_text());n=m['summary']['compiled'];state=m.get('progress',{}).get('state')
    if n>x.after or state not in ('RUNNING','ASSET_COMPLETE'):
        print(json.dumps({'summary':m['summary'],'progress':m.get('progress'),
            'completed':[a for a in m['assets'] if a['status'].startswith('PASS')]},ensure_ascii=False),flush=True);break
    time.sleep(3)
