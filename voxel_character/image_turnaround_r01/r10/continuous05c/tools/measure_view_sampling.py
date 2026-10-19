"""Sampling loss versus the same continuous surface, separate from reference fit."""
from review_surface import *

def run():
 ma=gzread(BASE/'generated/panel_master.json.gz');sf=np.load(BASE/'generated/continuous_surface.npz');src=source_render(sf['vertices'],sf['triangles'],ma['materials']);renders={name:gzread(BASE/'generated'/('common'+name+'.render.json.gz')) for name in ['25','125']};p=sf['vertices'];center=(p.min(0)+p.max(0))/2;span=float(max(p.max(0)-p.min(0))*1.5);out={}
 for angle in [0,45,90,180]:
  theta=math.radians(angle);s=span/400;view={'crop':[0,0,400,400],'axis_u':200-(math.cos(theta)*center[0]-math.sin(theta)*center[2])/s,'sole_y':200+center[1]/s,'scale_px_per_unit':HEIGHT/s,'yaw_degrees':angle};truth=project_exact(src,view);out[str(angle)]={}
  for name,r in renders.items():
   m=project_exact(r,view);out[str(angle)][name]={'continuous_mid_surface_pixels':int(truth.sum()),'common_projected_pixels':int(m.sum()),'missed_mid_surface_pixels':int((truth&~m).sum()),'mid_surface_coverage':int((truth&m).sum())/int(truth.sum()),'silhouette_IoU':int((truth&m).sum())/int((truth|m).sum())}
 write(BASE/'evidence/multiview_sampling_loss.json',{'same_master_sha256':sha(BASE/'generated/panel_master.json.gz'),'source_surface_sha256':sha(BASE/'generated/continuous_surface.npz'),'metrics':out,'frame_size':400,'span_m':span,'exact_pixel_center_projection':True,'interpretation':'Alias/coverage versus same continuous mid-surface only. Does not measure garment likeness, infer hidden geometry, or override reference/correspondence failures. The normal thickness can expand the voxel silhouette.'});print(json.dumps(out))
if __name__=='__main__':run()
