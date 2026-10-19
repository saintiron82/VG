from render_field import *

def run():
 m,a,src,q,b=inputs();sheet=Image.new('RGB',(1024,620),'white');d=ImageDraw.Draw(sheet);d.text((8,8),'Actual source diagnosis: flat material vs projected RGB | geometry unchanged | not beauty correction',fill='black');reports=[]
 for row,p in enumerate([b['parts'][0],b['parts'][6]]):
  i=p['index'];v=q[f'v{i}'];f=q[f'f{i}'];center=(v.min(0)+v.max(0))/2;span=float(max(v.max(0)-v.min(0))*1.2);tr=v[f];norm=np.cross(tr[:,1]-tr[:,0],tr[:,2]-tr[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12);c=tr.mean(1);names=list(C['views']);cameras=np.array([[math.sin(math.radians(C['views'][n]['yaw_degrees'])),0,math.cos(math.radians(C['views'][n]['yaw_degrees']))]for n in names]);ids=(norm@cameras.T).argmax(1);front=norm[:,2]>0
  reports.append({'part':p['id'],'front_facing_triangles':int(front.sum()),'front_facing_appearance_view_counts':{n:int((front&(ids==j)).sum())for j,n in enumerate(names)},'flat_geometry_winding_correct':True})
  r=prior_review.render_input(q,[p]);im,_=mesh_raster(r,0,0,center,span,size=280);sheet.paste(im,(10,row*300+40));d.text((10,row*300+25),p['id']+' source RGB',fill='black')
  flat={'materials':{'flat':{'color':'#bc958f' if i==0 else '#d4d2df'}},'groups':[{'material':'flat','quads':[[t[0].tolist(),t[1].tolist(),t[2].tolist(),t[2].tolist()]for t in tr]}]};im,_=mesh_raster(flat,0,0,center,span,size=280);sheet.paste(im,(310,row*300+40));d.text((310,row*300+25),'same source, flat material diagnostic',fill='black')
  # Controlled appearance test: actual front source RGB on front-facing surface;
  # no vertex move and no image repaint. Visibility/side albedo still unresolved.
  color=q[f'c{i}'].copy();fv=C['views']['front'];x=np.clip(np.floor(fv['axis_u']+c[:,0]/SCALE).astype(int),0,src.shape[1]-1);y=np.clip(np.floor(fv['sole_y']-c[:,1]/SCALE).astype(int),0,src.shape[0]-1);color[front]=src[y[front],x[front]];qq={f'v{i}':v,f'f{i}':f,f'c{i}':color};im,_=mesh_raster(prior_review.render_input(qq,[p]),0,0,center,span,size=280);sheet.paste(im,(610,row*300+40));d.text((610,row*300+25),'front RGB priority, diagnostic only',fill='black')
 sheet.save(BASE/'generated/appearance_geometry_diagnostic.jpg',quality=90);write(BASE/'evidence/appearance_geometry_audit.json',{'source_geometry_sha256':A['fixed_source_sha256'],'script_sha256':sha(__file__),'reports':reports,'applied_to_full_candidate':False});print(json.dumps(reports))
if __name__=='__main__':run()
