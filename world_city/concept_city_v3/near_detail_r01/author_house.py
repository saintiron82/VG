"""Add reusable near-view material geometry to a frozen ordinary house master.

The original envelope, wall transforms and apertures remain authoritative. This
is an explicit new candidate, not a changed coarse cache or generic subdivision.
All geometry is ordinary common-master paint/cut/extrusion data.
"""
from pathlib import Path
import copy, hashlib, json, math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'world_city/runtime_city/generated/r2/masters/ordinary_r2_5ab0065a8cd6bf.json'
DETAILED=ROOT/'voxel_character/common/assets/house/master.json'
RULES={
 'schema':'riverstone.surface_detail.rules.v1','seed':41873,
 'roof':{'tile_run_m':.25,'tile_width_m':.38,'lateral_joint_m':.05,
         'course_overlap_m':.055,'lip_height_m':.075,'underlay_recess_m':.10},
 'masonry':{'course_height_m':.20,'nominal_width_m':.40,'joint_m':.075,'recess_m':.05},
 'window':{'glass_recess_m':.15,'mullion_width_m':.075,'sill_projection_m':.26,
           'shutter_width_m':.30,'shutter_plank_m':.10},
 'door':{'plank_width_m':.18,'joint_m':.075,'face_depth_m':.075},
 'lod':{'near_pitch_m':.05,'near_enter_m':20.0,'far_exit_m':24.0,
        'whole_city_application':False,'collision':'independent unchanged reference envelope'},
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def stable(*parts):return int(hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()[:12],16)
def box(id,lo,hi,mat,part='solid',action='paint'):
 d={'id':id,'part':part,'action':action,'shape':{'kind':'box','min':lo,'max':hi}}
 if action=='paint':d['material']=mat
 return d
def prism(id,poly,z0,z1,mat,part='solid'):
 return {'id':id,'part':part,'action':'paint','shape':{'kind':'extrusion','polygon':poly,'z_min':z0,'z_max':z1},'material':mat}

def masonry_strip(prefix,x0,x1,y0,y1,z0,z1,rules=RULES['masonry']):
 """Running bond on +Z-facing planar span. Same inputs produce same stone IDs."""
 ops=[box(prefix+'_mortar',[x0,y0,z0],[x1,y1,z1-rules['recess_m']],'mortar')]
 row=0;y=y0;course_height=(y1-y0)/math.ceil((y1-y0)/rules['course_height_m'])
 while y<y1-1e-8:
  top=min(y1,y+course_height);w=rules['nominal_width_m'];x=x0-(w*.5 if row%2 else 0);col=0
  while x<x1-1e-8:
   a=max(x0,x+rules['joint_m']/2);b=min(x1,x+w-rules['joint_m']/2)
   if b>a:
    mat=['stone','stone_light','stone_dark'][stable(prefix,row,col,RULES['seed'])%3]
    ops.append(box(f'{prefix}_r{row}_c{col}',[a,y+rules['joint_m']/2,z0],[b,top-rules['joint_m']/2,z1],mat))
   x+=w;col+=1
  y=top;row+=1
 return ops

def tiled_roof(component,meta):
 ops=copy.deepcopy(component['operations']);out=[];r=RULES['roof'];tile_count=0
 for old in ops:
  if not old['id'].startswith('roof_plane_'):
   out.append(old);continue
  shape=old['shape'];p=shape['polygon'];z0,z1=shape['z_min'],shape['z_max']
  # The top edge is the highest Y endpoint at each X, independent of side.
  xs=sorted(set(v[0] for v in p));a,b=xs[0],xs[-1]
  ya=max(v[1] for v in p if v[0]==a);yb=max(v[1] for v in p if v[0]==b)
  under=copy.deepcopy(old);under['material']='slate_dark'
  under['shape']['polygon']=[[x,y-r['underlay_recess_m'] if abs(y-(ya+(yb-ya)*(x-a)/(b-a)))<1e-7 else y] for x,y in p]
  out.append(under)
  slope=(yb-ya)/(b-a);height=lambda x:ya+slope*(x-a)
  n=math.ceil((b-a)/r['tile_run_m']);step=(b-a)/n
  for course in range(n):
   # Grow a tile slightly uphill, never beyond the original roof boundary.
   x0=a+course*step;x1=a+(course+1)*step
   if slope>0:x1=min(b,x1+r['course_overlap_m'])
   else:x0=max(a,x0-r['course_overlap_m'])
   z=z0-(r['tile_width_m']*.5 if course%2 else 0);col=0
   while z<z1-1e-8:
    za=max(z0,z+r['lateral_joint_m']/2);zb=min(z1,z+r['tile_width_m']-r['lateral_joint_m']/2)
    if zb>za:
     # Downhill lip is raised; upper end beds into the next course.
     ha=height(x0)+(r['lip_height_m'] if slope>0 else .025)
     hb=height(x1)+(.025 if slope>0 else r['lip_height_m'])
     mat=['slate','slate','slate_light','slate_dark','slate_worn'][stable(old['id'],course,col,RULES['seed'])%5]
     out.append(prism(f"{old['id']}_tile_{course}_{col}",[[x0,height(x0)-.125],[x1,height(x1)-.125],[x1,hb],[x0,ha]],za,zb,mat))
     tile_count+=1
    z+=r['tile_width_m'];col+=1
 component['operations']=out
 return tile_count

def improve_wall(c):
 old=c['operations'];ops=[];count=0
 for op in old:
  op=copy.deepcopy(op)
  if op['id']=='era_stone_dado':
   lo,hi=op['shape']['min'],op['shape']['max']
   ops.extend(masonry_strip('dado',lo[0],hi[0],lo[1],hi[1],-.08,.06));continue
  if op['id'].endswith('_glass'):
   # Existing aperture remains; move the window pane physically behind frame.
   op['shape']['min'][2]=-.22;op['shape']['max'][2]=-.15
  if op['id']=='closed_door_leaf':
   lo,hi=op['shape']['min'],op['shape']['max'];op['material']='door_dark';hi[2]=0
   ops.append(op);n=math.ceil((hi[0]-lo[0])/RULES['door']['plank_width_m']);w=(hi[0]-lo[0])/n
   gap=RULES['door']['joint_m']/2
   for j in range(n):ops.append(box(f'door_plank_{j}',[lo[0]+j*w+gap,.04,0],[lo[0]+(j+1)*w-gap,hi[1]-.04,.075],'door' if j%3 else 'door_dark','door'))
   continue
  ops.append(op)
 # Existing cuts must precede added window detail; every new item is inside
 # or outside the opening frame, never refills the wall aperture.
 for op in old:
  if not (op['action']=='cut' and op['id'].startswith('window_')):continue
  name=op['id'].replace('_aperture','');lo,hi=op['shape']['min'],op['shape']['max'];x0,y0=lo[:2];x1,y1=hi[:2];xm=(x0+x1)/2;ym=(y0+y1)/2
  ops += [box(name+'_mullion',[xm-.04,y0,-.14],[xm+.04,y1,.055],'timber','windows'),
          box(name+'_transom',[x0,ym-.04,-.14],[x1,ym+.04,.055],'timber','windows'),
          box(name+'_sill_bottom',[x0-.23,y0-.18,-.20],[x1+.23,y0-.09,.19],'timber_dark','windows'),
          box(name+'_sill_top',[x0-.27,y0-.09,-.20],[x1+.27,y0-.015,.26],'timber_light','windows')]
  # Shutters folded back against facade: inset planks and two cross-bars.
  for side in [-1,1]:
   a=x0-.56 if side<0 else x1+.23;b=a+.30
   ops.append(box(name+f'_shutter_{side}',[a,y0,-.025],[b,y1,.075],'timber_dark','windows'))
   for j in range(3):ops.append(box(name+f'_shutter_{side}_plank{j}',[a+j*.10+.015,y0+.03,.075],[a+(j+1)*.10-.015,y1-.03,.125],'door','windows'))
   for j,y in enumerate([y0+.20,y1-.25]):ops.append(box(name+f'_shutter_{side}_strap{j}',[a,y,.125],[b,y+.05,.175],'iron','windows'))
  count+=1
 if any(o['id']=='closed_door_leaf' for o in old):
  ops.append(box('door_latch_plate',[.42,.95,.06],[.55,1.20,.13],'iron','door'))
  ops.append(box('door_handle',[.44,1.0,.13],[.51,1.14,.22],'iron_light','door'))
 c['operations']=ops
 return count

def build():
 master=json.loads(SOURCE.read_text());original=copy.deepcopy(master)
 master['id']='near_detail_B_REG_0120_r04';master['revision']=4
 tiles=windows=0
 for c in master['components']:
  if c['id'].startswith('wall_'):windows+=improve_wall(c)
  if c['id']=='roof':tiles=tiled_roof(c,master['metadata'])
  if c['id']=='foundation':
   # Retain the structural volume. Cut shallow running joints into its four
   # faces, so existing plinth extent and threshold do not move.
   plinth=c['operations'][0];lo,hi=plinth['shape']['min'],plinth['shape']['max'];plinth['material']='mortar'
   for side in ['front','back','left','right']:
    x0,x1=(lo[0],hi[0]) if side in ['front','back'] else (lo[2],hi[2])
    strip=[box('plinth_'+side+'_remove_skin',[x0,0,-.075],[x1,.5,0],None,action='cut')]+masonry_strip('plinth_'+side,x0,x1,0,.5,-.075,0)
    for op in strip:
     q=op['shape'];a,b=q['min'],q['max']
     if side=='front':q['min']=[a[0],a[1],hi[2]+a[2]];q['max']=[b[0],b[1],hi[2]+b[2]]
     if side=='back':q['min']=[-b[0],a[1],lo[2]-b[2]];q['max']=[-a[0],b[1],lo[2]-a[2]]
     if side=='right':q['min']=[hi[0]+a[2],a[1],a[0]];q['max']=[hi[0]+b[2],b[1],b[0]]
     if side=='left':q['min']=[lo[0]-b[2],a[1],a[0]];q['max']=[lo[0]-a[2],b[1],b[0]]
    c['operations'].extend(strip)
   # The threshold is an independent public-entry shape, not cladding skin.
   # Reapply its exact original operation last, so facade recess cannot notch it.
   threshold=copy.deepcopy(next(o for o in original['components'][0]['operations'] if o['id']=='threshold'))
   c['operations']=[o for o in c['operations'] if o['id']!='threshold']+[threshold]
 # The retained original eave rail was a detached small island. Two explicit
 # timber corbels join it to the existing front wall; no doorway is narrowed.
 master['components'].append({'id':'entry_corbels','parts':[{'id':'solid','pivot':[0,0,0]}], 'operations':[box('entry_corbel_'+str(s),[s*.58-.075,2.90,5.60],[s*.58+.075,3.15,6.20],'timber_dark') for s in [-1,1]]})
 master['instances'].append({'id':'entry_corbels','component':'entry_corbels','transform':{'translation':[0,0,0]}})
 master['provenance']['near_detail']={'source_master':str(SOURCE.relative_to(ROOT)),'source_sha256':sha(SOURCE),'detailed_rule_reference':str(DETAILED.relative_to(ROOT)),'detailed_sha256':sha(DETAILED),'reference_rules':['running-bond foundation boxes over recessed mortar','70 tile patches per canonical roof section; here parametrized to actual roof planes','frame/glass depth and shutter planks'],'reused_exact_components':['eave_rail'],'fixed_component_reuse_claim':False,'no_whole_house_scale':True,'new_tile_count':tiles,'window_count':windows}
 master['metadata']['near_detail_rules']=copy.deepcopy(RULES)
 master['metadata']['candidate_envelope_delta']='Roof lips up to +0.075m, window furniture remains within outer roof footprint. No wall transforms or aperture dimensions changed.'
 return original,master

if __name__=='__main__':
 out=HERE/'source';out.mkdir(parents=True,exist_ok=True)
 original,candidate=build()
 for name,value in [('house.r04.master.json',candidate),('detail_rules.r04.json',RULES)]:
  p=out/name
  if p.exists():raise SystemExit('Preserve existing output: '+str(p))
  p.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
 print(json.dumps({'candidate':str(out/'house.r04.master.json'),'ops':sum(len(c['operations']) for c in candidate['components']),'tiles':candidate['provenance']['near_detail']['new_tile_count'],'windows':candidate['provenance']['near_detail']['window_count']}))
