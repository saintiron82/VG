"""One explicit B15 private approach regrade to the retained public lane edge."""
import json,math
from . import author as a,public_tails,regeneration,preflight_layout
from .audit_retired_boundaries import interval

def run():
 folder=a.HERE/'root06_regrade_r02'
 if folder.exists():raise SystemExit('Preserve prior finite profile')
 folder.mkdir();scene=a.load_scene();layout=json.loads((a.HERE/'layout_draft_r02/selected_layout.json').read_bytes());plan=json.loads(a.PLAN_PATH.read_bytes());road=next(r for r in plan['roads']if r['id']=='LOWER_CONTOUR');u,v=road['polyline_xz_m'][68:70];L=math.dist(u,v);tangent=[(v[k]-u[k])/L for k in(0,1)];inward=[-tangent[1],tangent[0]];center=public_tails.closest([155.75,115.25],u,v);end=[[center[k]+inward[k]*road['width_m']/2+sign*tangent[k]*1.75 for k in(0,1)]for sign in(-1,1)];start=[[154.,126.25],[157.5,126.25]];poly=[start[0],start[1],end[1],end[0]]
 index=a.TriangleIndex(scene,[poly]);preflight_layout.virtual_restorations(index,layout)
 # Probe the actual public side; evaluate its plane at the exact lane edge.
 ep=[[p[k]-inward[k]*1e-5 for k in(0,1)]for p in end];spans=[]
 for row in index.rows:
  if row['material']not in ('road','alley'):continue
  span=interval(*end,row['polygon_xz_m'])
  if span:spans.append((span,row))
 knots=sorted({0.,1.}|{t for span,_ in spans for t in span});knots=[t for i,t in enumerate(knots)if i==0 or t-knots[i-1]>1e-7];heights=[];seam=[]
 for t in knots:
  p=[end[0][k]+t*(end[1][k]-end[0][k])for k in(0,1)];votes=[a.common.height(row['plane_y_xz_m'],p)for span,row in spans if span[0]-1e-7<=t<=span[1]+1e-7]
  if not votes or max(votes)-min(votes)>1e-7:raise ValueError('Incompatible public seam '+str((t,votes)))
  heights.append(votes[0]);seam.append([p[0],heights[-1],p[1]])
 levels=[i/10 for i in range(11)];points=[];target=[];fixed={}
 for j,t in enumerate(levels):
  for k,s in enumerate(knots):
   p=[(1-t)*(start[0][c]+s*(start[1][c]-start[0][c]))+t*(end[0][c]+s*(end[1][c]-end[0][c]))for c in(0,1)];points.append(p);target.append(2.5+t*(heights[k]-2.5))
   if j==0:fixed[len(points)-1]=2.5
   if j==len(levels)-1:fixed[len(points)-1]=heights[k]
 n=len(knots);tris=[]
 for j in range(len(levels)-1):
  for k in range(n-1):
   i=j*n+k;tris.extend([[i,i+1,i+n+1],[i,i+n+1,i+n]])
 result=regeneration.solve_field(points,tris,fixed,target);result.update(schema='riverstone.r17.private_public_interface_regrade.v1',base_scene_sha256=a.SCENE_SHA256,id='B15:R8:LANE:2_5:06:REGRADE',polygon_xz_m=poly,start_edge_xz_m=start,public_edge_xz_m=end,public_seam_knots_xyz_m=seam,road_id='LOWER_CONTOUR',road_segment_index=68,public_traffic_top_changed=False,source_obligation='Remove obsolete private top and finite bank pieces only inside this owner. Keep exact public lane edge and add finite nonwalking side closure. New source triangles require footprint, support, edge and clear-volume audits before activation.')
 out=folder/'profile.json';out.write_text(json.dumps(result,separators=(',',':'))+'\n');print({k:result[k]for k in ('status','maximum_gradient','maximum_fixed_error_m')if k in result});print('knots',n,'triangles',len(tris),'bounds',a.bounds(poly));print(a.sha(out))
if __name__=='__main__':run()
