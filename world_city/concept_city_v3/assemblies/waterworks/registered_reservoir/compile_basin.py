"""Bounded sequential native compilation of the finite basin, never the city."""
import json,resource,time,sys
from author_reservoir import HERE,ROOT,ORIGIN,PITCH,ref,write,estimate_candidates
from voxel_character.common import coordinate_planes,render_data,core

def main():
 start=time.monotonic();name=sys.argv[1] if len(sys.argv)>1 else 'preflight';pre=json.loads((HERE/(name+'.json')).read_text());rows=[]
 for item in pre['sources']:
  source=ROOT/item['source']['path'];s=json.loads(source.read_text());assert ref(source)==item['source'];estimate=estimate_candidates(s,PITCH)['candidate_cells_exact_aabb_visits'];assert estimate<600000;t=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':PITCH},max_candidate_cells=600000,max_output_cells=200000);assert c['valid'];assert c['candidate_cells']==estimate;r=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.2.render.json";write(cp,r)
  row={'id':s['id'],'source':ref(source),'cache':ref(cp),'master_hash':core.digest(s),'pitch_m':PITCH,'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':r['quad_count'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'bounds_local_m':r['bounds'],'grid_origin':c['grid_origin']};rows.append(row);print(json.dumps(row),flush=True)
 report={'schema':'riverstone.city.reservoir_native_compile.v1','preflight':ref(HERE/(name+'.json')),'requests':rows,'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'status':'pass','actual_scene_loaded':False,'actual_viewed':False};write(HERE/('interface_compile_report.json' if name=='interface_preflight' else 'compile_report.json'),report)
if __name__=='__main__':main()
