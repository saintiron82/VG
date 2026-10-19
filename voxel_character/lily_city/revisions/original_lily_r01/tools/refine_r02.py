"""Targeted actual-view correction. Writes new module source, retains old caches/evidence."""
from author import HERE,dump,box,poly,ribbon
import json,math

def main():
 path=HERE/'data/modules/lily_long.json';m=json.loads(path.read_text());ops=m['operations']
 ops[:]=[o for o in ops if o['id']!='curved_cowlick' and not o['id'].startswith(('rear_lock_','rear_ridge_'))]
 # Connected arch made of perpendicular-width segment polygons, not horizontal-offset ribbon.
 pts=[[-.115,1.746],[-.072,1.789],[-.018,1.808],[.028,1.798],[.049,1.768]]
 for i,(a,b) in enumerate(zip(pts,pts[1:])):
  dx=b[0]-a[0];dy=b[1]-a[1];d=math.hypot(dx,dy);nx=-dy/d*.010;ny=dx/d*.010
  poly(ops,'hair','cowlick_connected_'+str(i),'silver_light',[[a[0]+nx,a[1]+ny],[b[0]+nx,b[1]+ny],[b[0]-nx,b[1]-ny],[a[0]-nx,a[1]-ny]],-.011,.018)
 # Nape transition connects crown to flowing rear lock segments; no detached rear sheet.
 for i,(yl,yh,zl,zh,w) in enumerate([(1.60,1.72,-.157,-.083,.155),(1.49,1.63,-.201,-.129,.173),(1.41,1.52,-.229,-.170,.191)]):
  poly(ops,'hair_tail_back','nape_transition_'+str(i),'silver', [[-w,yl],[w,yl],[w*.82,yh],[-w*.82,yh]],zl,zh)
 for i in range(7):
  x=(i-3)*.055;bot=.57+abs(i-3)*.025
  pts=[[x,1.66,-.134],[x*1.16,1.47,-.185],[x*1.33,1.23,-.229],[x*1.72,1.02,-.260],[x*1.64,.80,-.248],[x*1.36,bot,-.205]]
  for j,(a,b) in enumerate(zip(pts,pts[1:])):
   wa=.034*(1-j*.06);wb=.034*(1-(j+1)*.06)
   # Two vertical sections split at the middle create an explicit depth wave.
   mid=[(a[k]+b[k])/2 for k in range(3)]
   for k,(p,q,w1,w2) in enumerate([(a,mid,wa,(wa+wb)/2),(mid,b,(wa+wb)/2,wb)]):
    poly(ops,'hair_tail_back',f'flowing_rear_{i}_{j}_{k}','silver' if i%2 else 'silver_light',[[p[0]-w1,p[1]],[p[0]+w1,p[1]],[q[0]+w2,q[1]],[q[0]-w2,q[1]]],min(p[2],q[2])-.024,max(p[2],q[2])+.018)
    poly(ops,'hair_tail_back',f'flowing_ridge_{i}_{j}_{k}','silver_shadow' if i%2 else 'silver',[[p[0]-.020,p[1]],[p[0]-.007,p[1]],[q[0]-.007,q[1]],[q[0]-.020,q[1]]],min(p[2],q[2])-.034,min(p[2],q[2])-.022)
 # Viewer image-right is +X in this camera convention. Move braid there.
 for o in ops:
  if o['part']=='braid':
   s=o['shape'];s['polygon']=[[-x,y] for x,y in reversed(s['polygon'])]
 m['metadata']['revision_note']='r02: connected cowlick, depth-varying nape/rear locks, image-right (+X) braid'
 dump(path,m)
 p=HERE/'data/modules/lily_teal_gold.json';m=json.loads(p.read_text())
 for o in m['operations']:
  s=o['shape']
  if s['kind']=='box':s['min'][0],s['max'][0]=-s['max'][0],-s['min'][0]
  else:s['polygon']=[[-x,y] for x,y in reversed(s['polygon'])]
 m['metadata']['image_right']='character positive X, verified actual front render'
 dump(p,m)
 # Open eyes have a larger vertical iris range and less sleepy almond silhouette.
 for kind in ['soft_taper','oval','square']:
  p=HERE/'data/modules'/(kind+'.json');m=json.loads(p.read_text())
  for o in m['operations']:
   if o['id'].startswith(('eye_white_','iris_','pupil_','glint_')):
    s=o['shape']
    if s['kind']=='box':
     for key in ['min','max']:s[key][1]=1.64+(s[key][1]-1.64)*1.28
    else:s['polygon']=[[x,1.64+(y-1.64)*1.28] for x,y in s['polygon']]
  for op in m['operations']:
   if op['id'].startswith('lid_'):op['material']='skin_light'
  for lab in ['left','right']:
   x=(-1 if lab=='left' else 1)*.074
   poly(m['operations'],'eyelid_'+lab,'closed_lid_line_'+lab,'lash',[[x-.036,1.680],[x+.036,1.680],[x+.033,1.690],[x-.033,1.690]],.166,.179)
  dump(p,m)
 print('Refined source modules; previous cached renders retained')
if __name__=='__main__':main()
