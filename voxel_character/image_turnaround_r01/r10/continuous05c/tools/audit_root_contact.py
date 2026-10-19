"""Exact convex-prism overlap audit before voxel sampling; no geometry mutation."""
from measured_surface import *

def convex_data(op):
 p=op['shape']['polygon'];lo=op['shape']['z_min'];hi=op['shape']['z_max'];tr=transform(op.get('transform'));v=np.array([apply(tr,[*xy,z]) for z in [lo,hi] for xy in p]);n=len(p);edges=np.array([v[j]-v[i] for i,j in [(i,(i+1)%n) for i in range(n)]+[(i+n,(i+1)%n+n) for i in range(n)]+[(i,i+n) for i in range(n)]]);norm=[np.cross(v[1]-v[0],v[2]-v[0])]+[np.cross(v[(i+1)%n]-v[i],v[i+n]-v[i]) for i in range(n)];return v,edges,np.array(norm),v.min(0),v.max(0)

def sat(a,b):
 av,ae,an,_,_=a;bv,be,bn,_,_=b;cross=np.cross(ae[:,None,:],be[None,:,:]).reshape(-1,3);axes=np.r_[an,bn,cross];norms=np.linalg.norm(axes,axis=1);axes=axes[norms>1e-12]/norms[norms>1e-12,None];aa=axes@av.T;bb=axes@bv.T;overlap=np.minimum(aa.max(1),bb.max(1))-np.maximum(aa.min(1),bb.min(1));return float(overlap.min())

def run():
 t=time.monotonic();ma=gzread(BASE/'generated/panel_master.json.gz');pv=gzread(ROOT/'full01/generated/volume_master_v03.json.gz');parent=[(o['id'],convex_data(o)) for o in pv['components'][0]['operations'] if o['part']=='torso_closed'];rootbox=A['views']['front']['root_search_box'];selected=[]
 for o in ma['components'][0]['operations']:
  d=convex_data(o);p=np.array(o['transform']['translation']);u=p[0]/SCALE+F['axis_u'];y=F['sole_y']-p[1]/SCALE
  if rootbox[0]<=u<=rootbox[2] and rootbox[1]<=y<=rootbox[3]:selected.append((o['id'],d))
 candidates=0;overlaps=[];contacts=[]
 for ident,a in selected:
  for pid,b in parent:
   if np.any(a[4]<b[3]) or np.any(b[4]<a[3]):continue
   candidates+=1;margin=sat(a,b)
   if margin>1e-9:overlaps.append({'cloth_op':ident,'parent_op':pid,'minimum_SAT_projection_overlap_m':margin})
   elif margin>=-1e-9:contacts.append([ident,pid])
 report={'master_sha256':sha(BASE/'generated/panel_master.json.gz'),'parent_sha256':sha(ROOT/'full01/generated/volume_master_v03.json.gz'),'root_operations_tested':len(selected),'aabb_pair_candidates':candidates,'strict_positive_volume_intersection_pairs':len(overlaps),'zero_margin_contact_pairs':len(contacts),'witnesses':overlaps[:12],'method':'Separating-axis theorem for actual convex triangular normal-thickness prism and convex measured torso extrusion; all face normals and edge cross-product axes. Same fixed25mm representation thickness.','numerical_margin_m':1e-9,'strict_source_overlap_exists':bool(overlaps),'anatomical_or_sewing_attachment_verified':False,'root_identity_remains_unknown':True,'no_new_connector':True,'runtime_seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'script_sha256':sha(__file__)}
 write(BASE/'evidence/exact_root_solid_contact.json',report);print(json.dumps(report))
if __name__=='__main__':run()
