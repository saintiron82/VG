"""Two finite native field-edge rails; common compiler, no scaling."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from author_native import Source,estimate_candidates,coordinate_planes,render_data,core,ref,load,sha,ROOT

def main():
 (OUT/'masters').mkdir(exist_ok=True);(OUT/'cache').mkdir(exist_ok=True);sources=[]
 for w in(2,4):
  a=Source(f'precinct_field_edge_{w}',[-w/2,-.5,-.25],[w/2,1.25,.25])
  for x in(-w/2+.125,w/2-.125):a.box('post'+str(x),[x-.125,-.5,-.25],[x+.125,1.25,.25],'timber_dark',component='posts')
  for y in(.25,.75):a.box('rail'+str(y),[-w/2,y,-.125],[w/2,y+.25,.125],'timber',component='rails')
  s=a.finish();s['id']=f'registered_precinct_r06_field_edge_{w}m';s['provenance'].update(author=ref(Path(__file__)),approved_reference=ref(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'),mesh_scaling=False);mp=OUT/'masters'/f'{s["id"]}.json';mp.write_text(json.dumps(s,indent=2)+'\n');e=estimate_candidates(s,.25);assert e['candidate_cells_exact_aabb_visits']<10000;sources.append({'role':f'field_edge_{w}m','id':s['id'],'source':ref(mp),'pitch_m':.25,'estimate':e})
 (OUT/'native_preflight.json').write_text(json.dumps({'sources':sources,'summary':{'new_sources':2,'candidate_cells':sum(s['estimate']['candidate_cells_exact_aabb_visits']for s in sources)},'common_dependencies':[ref(ROOT/'voxel_character/common/coordinate_planes.py'),ref(ROOT/'voxel_character/common/render_data.py'),ref(ROOT/'voxel_character/common/core.py')]},indent=2)+'\n');out=[]
 for row in sources:
  s=load(ROOT/row['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':.25},max_candidate_cells=10000,max_output_cells=10000);assert c['valid'];m=render_data.make_render_data(c);rp=OUT/'cache'/f'{s["id"]}.render.json';rp.write_text(json.dumps(m,separators=(',',':'))+'\n');out.append(dict(row,cache=ref(rp),bounds=m['bounds'],master_hash=core.digest(s),candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),constraints=c['constraints']))
 (OUT/'compiled_assets.json').write_text(json.dumps({'assets':out,'summary':{'candidate_cells':sum(r['candidate_cells']for r in out),'output_cells':sum(r['output_cells']for r in out)}},indent=2)+'\n');print('native_edges',len(out),sum(r['candidate_cells']for r in out),sum(r['output_cells']for r in out))
if __name__=='__main__':main()
