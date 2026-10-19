"""Dimension-authored recovery of the sealed range grammar; no engine changes."""
import sys,math,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parent))
from build_audit import ref,write,estimate_candidates,source_bounds
from world_city.runtime_city.parts.author import Source,extrusion,approved_palette
TEMPLATE=HERE.parent/'assembly_r01/masters/registered_monastery_north_convent_range.json'
SPECS=[('school',24,12,14,9,'slate_gray'),('guest',24,12,13,8,'clay_red'),('infirmary',24,8,13,8,'clay_red'),('canon_narrow',10,10,10.5,6.5,'clay_red'),('canon_wide',14,8,12,7.5,'clay_red')]
def make_range(name,w,d,h,eave,roof):
 a=Source('precinct_'+name,[-w/2,-.5,-d/2],[w/2,h,d/2]);t=.75
 for id,lo,hi in [('west',[-w/2,0,-d/2],[-w/2+t,eave,d/2]),('east',[w/2-t,0,-d/2],[w/2,eave,d/2]),('rear',[-w/2+t,0,-d/2],[w/2-t,eave,-d/2+t]),('front',[-w/2+t,0,d/2-t],[w/2-t,eave,d/2])]:a.box('range_'+id,lo,hi,'stone',component='masonry')
 rot={'basis':[[0,0,-1],[0,1,0],[1,0,0]]}
 for side in (-1,1):
  low,high=(-w/2,-w/2+.5)if side<0 else(w/2-.5,w/2)
  a.op('gable_'+str(side),extrusion([[-d/2,eave-.5],[d/2,eave-.5],[0,h-.5]],low,high),'stone_dark',component='masonry',transform=rot)
 for side in (-1,1):
  for i in range(4):
   z0=side*d/2*i/4;z1=side*d/2*(i+1)/4;y0=h-(h-eave)*i/4;y1=h-(h-eave)*(i+1)/4
   a.op('roof_'+str(side)+'_'+str(i),extrusion([[z0,y0],[z1,y1],[z1,y1-.6],[z0,y0-.6]],-w/2,w/2),'slate',component='roof',transform=rot)
 a.box('ridge',[-w/2,h-.6,-.25],[w/2,h,.25],'slate_dark',component='roof')
 a.box('bearing_floor',[-w/2,-.5,-d/2],[w/2,0,d/2],'stone_dark',component='masonry')
 a.box('actual_entry',[-1.25,0,d/2-1],[1.25,3.5,d/2+.1],component='masonry',action='cut')
 count=max(2,int(w/4.5))
 for side in(-1,1):
  z=side*(d/2-.25)
  for i in range(count):
   x=-w/2+(i+.5)*w/count
   for level in ([eave*.55]if eave<8.5 else[2.2,eave*.62]):
    if side>0 and abs(x)<2 and level<3.5:continue
    a.box(f'window_surround_{side}_{i}_{level}',[x-.8,level,z-.25],[x+.8,level+1.8,z+.25],'stone_light',component='windows')
    a.box(f'window_pane_{side}_{i}_{level}',[x-.5,level+.25,z-.25],[x+.5,level+1.5,z+.25],'glass',component='windows')
 s=a.finish();s['materials']=approved_palette(roof);s['materials']['glass']=json.loads(TEMPLATE.read_text())['materials']['glass'];s['id']='registered_precinct_recovered_'+name;s['provenance'].update(recovered_factory=ref(Path(__file__)),sealed_grammar_reference=ref(TEMPLATE),recovery_note='Original author_assemblies.py was absent from restored checkpoint. New dimension-authored thin-wall/ridge/window source follows the sealed range operation grammar; no old master scaled or changed.',revision02_prompt_status='Inherited Source provenance points to an explicitly labeled reconstruction notice; original prompt bytes were unavailable.');s['extensions'].update(local_bounds_m=source_bounds(s),dimensions_m={'width':w,'depth':d,'height':h,'eave':eave},native_width_variant=name,entrances=[{'id':'main_entry','threshold_local_m':[0,0,d/2],'clear_width_m':2.5,'clear_height_m':3.5,'outward_normal':[0,0,1]}],owned_floor_depth_m=.5,actual_placed=False,actual_viewed=False);return s
if __name__=='__main__':
 rows=[]
 for spec in SPECS:
  s=make_range(*spec);p=HERE/'masters'/f"{s['id']}.json";write(p,s);e=estimate_candidates(s,.5);assert e['candidate_cells_exact_aabb_visits']<600000;rows.append({'role':spec[0],'source':ref(p),'estimate':e})
 write(HERE/'source_preflight.json',{'schema':'riverstone.precinct.recovered_ranges_preflight.v1','sources':rows,'pitch_m':.5,'candidate_cap_each':600000,'output_cap_each':150000,'new_factory':ref(Path(__file__)),'old_masters_changed':False});print([(x['role'],x['estimate']['candidate_cells_exact_aabb_visits'])for x in rows])
