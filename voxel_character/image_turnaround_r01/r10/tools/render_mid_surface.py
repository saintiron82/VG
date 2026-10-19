"""Render the actual fitted mid-surface, separate from overlapping prism caps."""
from regularized_surface import *
def run():
 master=gzread(SURFACE/'generated/master.json.gz');groups={}
 for op in master['components'][0]['operations']:
  q=[apply(transform(op['transform']),[*p,0]) for p in op['shape']['polygon']];groups.setdefault(op['material'],[]).extend([q,list(reversed(q))])
 r={'materials':master['materials'],'groups':[{'material':k,'quads':v} for k,v in sorted(groups.items())]};gzwrite(SURFACE/'generated/mid_surface.render.json.gz',r);pts=np.array([p for g in r['groups'] for q in g['quads'] for p in q]);center=(pts.min(0)+pts.max(0))/2;span=float(max(pts.max(0)-pts.min(0))*1.4);sheet=Image.new('RGB',(1536,445),'white');d=ImageDraw.Draw(sheet);d.text((12,12),'Actual inferred mid-surface before normal thickness and voxels. Same measured mask; no silhouette repair.',fill='black');files=[]
 for i,(name,yaw,pitch) in enumerate([('front',0,0),('three_quarter',45,15),('side',90,0),('back',180,0)]):
  im=raster(r,math.radians(yaw),math.radians(pitch),center,span,size=384);dr=ImageDraw.Draw(im);dr.rectangle((0,0,384,25),fill='white');dr.text((8,8),name+' / actual continuous mid-surface',fill='black');p=SURFACE/'generated'/f'mid_surface_{name}.png';im.save(p);sheet.paste(im,(i*384,45));files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
 p=SURFACE/'generated/mid_surface_four_views.jpg';sheet.save(p,quality=89);write(SURFACE/'evidence/mid_surface_provenance.json',{'master_sha256':sha(SURFACE/'generated/master.json.gz'),'render_input_sha256':sha(SURFACE/'generated/mid_surface.render.json.gz'),'renderer_sha256':sha(CPU_SOURCE),'exporter_sha256':sha(__file__),'double_sided':True,'normal_thickness_in_this_preview':False,'notes':'Earlier continuous_*.png previews show all individual extrusion caps, including internal overlapping faces; those are preserved but are not composited exterior renders. This preview renders the actual fitted shared mid-surface only, prior to adding the explicit normal thickness. Common voxel exterior remains authoritative after compile.','images':files,'comparison_sha256':sha(p)})
 print(json.dumps({'path':str(p),'sha256':sha(p),'disk_bytes':budget()}))
if __name__=='__main__':run()
