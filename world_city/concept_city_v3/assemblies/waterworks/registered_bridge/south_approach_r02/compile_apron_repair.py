import author,resource,time,json
start=time.monotonic()
p=author.read(author.HERE/'profile.json')
old=author.read(author.HERE/'evidence/coplanar_apron_01/resolved_placements.json')
for r in old['assets']['recessed_fixed'].values():
 if isinstance(r,dict) and 'path' in r:assert author.sha(author.ROOT/r['path'])==r['sha256']
fine=author.compile_one(author.fine_master(p),author.PITCH,2000000,700000)
old['assets']['visible_cover']=fine
old['apron_revision']='Optional bridge-side and upstream apron clipped to avoid actual native coplanar faces; previous evidence preserved.'
author.write(author.HERE/'resolved_placements.json',old)
print('PROCESS_RESOURCE',json.dumps({'wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
