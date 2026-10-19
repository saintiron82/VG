from render_field import *

def run():
 m,a,src,q,b=inputs();n=np.load(BASE/'generated/head_interval_trial.npz');p=b['parts'][0];v=n['v0'];center=(v.min(0)+v.max(0))/2;span=float(max(v.max(0)-v.min(0))*1.2);sheet=Image.new('RGB',(1280,720),'white');d=ImageDraw.Draw(sheet);d.text((10,10),'Head interval trial | visible skin is lower support, hair envelope upper support; hidden closure prior explicit',fill='black');d.text((10,35),'Original approved image / front actual source / side actual source / flat geometry. No image or original skin recolor.',fill='black');original=Image.fromarray(src).crop((255,45,486,252));original.thumbnail((310,310));sheet.paste(original,(0,80))
 for j,(name,angle)in enumerate([('front',0),('side',75),('back',180)]):
  im,_=mesh_raster(prior_review.render_input(n,[p]),math.radians(angle),0,center,span,size=310);sheet.paste(im,((j+1)*320,80));d.text(((j+1)*320+10,60),name,fill='black')
 f=n['f0'];tr=v[f];flat={'materials':{'flat':{'color':'#bc958f'}},'groups':[{'material':'flat','quads':[[t[0].tolist(),t[1].tolist(),t[2].tolist(),t[2].tolist()]for t in tr]}]}
 for j,angle in enumerate([0,45,75,180]):
  im,_=mesh_raster(flat,math.radians(angle),0,center,span,size=310);sheet.paste(im,(j*320,400))
 sheet.save(BASE/'generated/head_interval_trial_comparison.jpg',quality=89);write(BASE/'evidence/head_trial_render.json',{'source_sha256':sha(BASE/'generated/head_interval_trial.npz'),'renderer_sha256':sha(CPU_SOURCE),'script_sha256':sha(__file__),'center_m':center.tolist(),'span_m':span,'shape_art_approved':False,'head_bare_skull_is_inferred':True})
if __name__=='__main__':run()
