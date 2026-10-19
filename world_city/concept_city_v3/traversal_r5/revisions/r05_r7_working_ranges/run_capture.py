"""Execute the unchanged Bash/Godot harness after the lead releases the slot."""
import pathlib,subprocess,time,resource,json,argparse
H=pathlib.Path(__file__).resolve().parent

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--report-stem',required=True);args=parser.parse_args();stem=args.report_stem;assert stem.replace('_','').isalnum();report=H/'evidence'/(stem+'.json');log=H/'evidence'/(stem+'.log');metrics=H/'evidence'/(stem+'_metrics.json');assert (H/'prepared.json').exists();assert not any(p.exists()for p in [report,log,metrics]);start=time.monotonic()
 with log.open('x')as output:
  run=subprocess.run(['bash',str(H/'run.sh'),'--prepared='+str(H/'prepared.json'),'--report='+str(report)],stdout=output,stderr=subprocess.STDOUT)
 data={'wall_seconds':time.monotonic()-start,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'exit_code':run.returncode}
 with metrics.open('x')as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(data));raise SystemExit(run.returncode)
if __name__=='__main__':main()
