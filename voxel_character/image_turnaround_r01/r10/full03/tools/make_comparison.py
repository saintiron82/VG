"""Arrange unretouched approved input and actual-source CPU render evidence."""
from field_source import *
ref=Image.open(REPO/'voxel_character/three_head_reference_r01/violet_costume_skin_candidate_r06.png').convert('RGB').crop((0,0,1536,624))
views=Image.open(BASE/'generated/coupled_source_four_views.jpg').convert('RGB')
out=Image.new('RGB',(1536,1144),'white');d=ImageDraw.Draw(out)
d.text((10,8),'Approved generated reference r06 (observed pixels of AI sheet; side/back are AI interpretation, not calibrated photographs)',fill='black');out.paste(ref,(0,30));out.paste(views,(0,664));d.text((10,1125),'FAILURE PRESERVED: truncated hidden hair / rough bouquet / layered costume. No full common compile, GPU or rig approval.',fill='black')
p=BASE/'generated/approved_full03_failure_comparison.jpg';out.save(p,quality=85);print(sha(p),p.stat().st_size)
