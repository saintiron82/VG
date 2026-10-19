from pathlib import Path
import json,os,resource,subprocess,sys,time
H=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
start=time.monotonic();rows=[]
while True:
 previous=sorted((H/'batches').glob('batch_*.json'));last=json.loads(previous[-1].read_bytes())if previous else None
 if last and last['whole_candidate_complete']:break
 spent=sum(json.loads(p.read_bytes())['elapsed_seconds']for p in previous)
 assert spent<240 and time.monotonic()-start<240
 number=len(previous)+1;log=H/'validation'/('batch_%03d.log'%number)
 with log.open('x')as output:
  result=subprocess.run([sys.executable,str(H/'author_r02.py'),'--count','16'],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONWARNINGS':'ignore::SyntaxWarning'},stdout=output,stderr=subprocess.STDOUT,timeout=min(30,240-spent))
 assert result.returncode==0,'Bounded batch failed; preserve log and stop'
 report=json.loads((H/'batches'/('batch_%03d.json'%number)).read_bytes());assert report['new_modules_this_batch']>0
 row={k:report[k]for k in ['new_modules_done','new_modules_required','elapsed_seconds','cumulative_batch_seconds','geometry_bytes']};rows.append(row);print(json.dumps(row),flush=True)
report={'all_pass':last['whole_candidate_complete'],'new_modules':last['new_modules_done'],'new_geometry_bytes':last['geometry_bytes'],'total_measured_batch_seconds':last['cumulative_batch_seconds'],'driver_wall_seconds':time.monotonic()-start,'one_sampler_at_a_time':True,'address_space_limit_bytes':256*1024*1024,'per_process_wall_limit_seconds':30,'cumulative_author_limit_seconds':240,'batch_results':rows}
(H/'validation/batch_driver.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report),flush=True)
