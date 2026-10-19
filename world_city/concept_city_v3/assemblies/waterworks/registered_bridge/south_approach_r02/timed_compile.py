import runpy,resource,time,json
start=time.monotonic()
try:runpy.run_path(__file__.replace('timed_compile.py','resume_compile.py'),run_name='__main__')
finally:print('PROCESS_RESOURCE',json.dumps({'wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
