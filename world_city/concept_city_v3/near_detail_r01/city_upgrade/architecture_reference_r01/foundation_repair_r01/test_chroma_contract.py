"""Synthetic next-input contract, not a recoloring or recovery of the r03 raster."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent;ROOT=next(p for p in O.parents if (p/'voxel_character/common/core.py').exists());KEY=np.array([255,0,255.]);PAL=np.array([[164,156,153],[70,65,61],[185,121,66],[24,161,170],[62,112,35]],float)
def classify(rgb,marker=False):
 if marker:return 'annotation'
 p=np.asarray(rgb,float)
 if np.max(np.abs(p-KEY))<=1:return 'background'
 if np.min(np.max(np.abs(PAL-p),axis=1))<=1:return 'material'
 for color in PAL:
  delta=color-KEY;alpha=np.dot(p-KEY,delta)/np.dot(delta,delta);res=np.max(np.abs(p-(KEY+alpha*delta)))
  if .01<alpha<.99 and res<=1:return 'uncertain_edge_mix'
 return 'uncertain_unlisted_color'
def validate_background(image,known_background):return bool(np.all(np.max(np.abs(image[known_background].astype(float)-KEY),axis=1)<=1))
def palette_ok(pal):return bool(np.all(np.max(np.abs(pal-KEY),axis=1)>20))
tests={};swatches=[('key',KEY,False,'background'),('gray_stone',PAL[0],False,'material'),('cyan_glass',PAL[3],False,'material'),('dark_mortar',PAL[1],False,'material'),('wood',PAL[2],False,'material'),('plant',PAL[4],False,'material'),('grid_black_separate_mask',[0,0,0],True,'annotation'),('fiducial_white_separate_mask',[255,255,255],True,'annotation')]
for a in [.25,.5,.75]:swatches.append((f'mixed_stone_alpha{a}',np.rint(KEY*(1-a)+PAL[0]*a),False,'uncertain_edge_mix'))
for name,p,mark,want in swatches:tests[name]=classify(p,mark)==want
canvas=np.tile(KEY.astype(np.uint8),(8,8,1));domain=np.ones((8,8),bool);tests['solid_key_background_accepted']=validate_background(canvas,domain);changed=canvas.copy();changed[0,0]=[230,0,230];tests['background_shadow_rejected']=not validate_background(changed,domain);changed=canvas.copy();changed[:,:,1]=np.arange(8)[None,:]*3;tests['background_gradient_rejected']=not validate_background(changed,domain);tests['palette_key_collision_rejected']=not palette_ok(np.concatenate([PAL,KEY[None,:]]));tests['gray_cyan_palette_safe']=palette_ok(PAL);tests['unknown_color_uncertain']=classify([120,140,220])=='uncertain_unlisted_color';tests['source_unchanged']=hashlib.sha256((ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png').read_bytes()).hexdigest()=='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93';assert all(tests.values())
fixture=np.tile(KEY.astype(np.uint8),(16,16*len(swatches),1))
for i,(_,color,_,_) in enumerate(swatches):fixture[:,i*16:(i+1)*16]=color
Image.fromarray(fixture).save(O/'chroma_synthetic_fixture.png');r={'schema':'riverstone.image_input.chroma_fixture.v1','all_pass':True,'test_count':len(tests),'tests':tests,'key_rgb':KEY.astype(int).tolist(),'allowed_palette_rgb':PAL.astype(int).tolist(),'swatches':[{'id':n,'rgb':np.asarray(p).astype(int).tolist(),'separate_annotation_mask':m,'expected':w} for n,p,m,w in swatches],'requirements':['Future generated input has solid palette-external magenta background, no background gradient or cast shadow.','Grid and fiducials are separate annotation masks, never part of material foreground.','Known mixed key/material edge pixels remain uncertain; no forced hole or solid decision.','Cyan remains a valid material and is not used as the key.','This synthetic fixture does not restore lost r03 pixels. Foundation repair reads unchanged white-background source.'],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256((O/'chroma_synthetic_fixture.png').read_bytes()).hexdigest(),'sampling_calls':0};(O/'chroma_tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'all_pass':True,'tests':len(tests)}))
