"""Bounded reproducible appearance combinations, no simulation or NPC behavior."""
import copy,json,random
from author import HERE,dump
from assemble import assemble
RULES={'schema':'riverstone.character.combination_rules.v1','seed_contract':'Python random.Random(seed); ordered input lists; persist selected preset bytes. No runtime random appearance.','district_roles':{'market':['merchant','resident','child'],'craft':['artisan','resident','porter','child'],'residential':['resident','scholar','child'],'civic':['guard','scholar','resident','child'],'harbor':['porter','merchant','resident','child'],'garden':['resident','scholar','child']},'occupation_outfits':{'merchant':['female_long_dress','female_blouse_skirt','male_tunic','male_vest','male_coat'],'artisan':['female_blouse_skirt','female_workwear','male_workwear','male_vest'],'resident':['female_long_dress','female_blouse_skirt','female_workwear','male_tunic','male_vest','male_coat','male_workwear'],'guard':['male_coat','male_tunic'],'porter':['female_workwear','male_workwear','male_tunic'],'scholar':['female_long_dress','male_coat','male_vest'],'child':['child_tunic','child_dress','child_trousers']},'reserved_modules':{'lily_long':'Lily only','lily_teal_gold':'Lily only'},'excluded':['NPC actions','schedules','economy','dialogue','physical child controller integration without review']}
PALETTES=[{'teal_wool':'78618f','teal_light':'a18bb3','teal_shadow':'514363','linen':'dfd1b2','linen_shadow':'b2a181','brass':'b6975d','silver':'654535','silver_light':'986a48','silver_shadow':'392e2a'}, {'teal_wool':'416b69','teal_light':'67908a','teal_shadow':'2d494d','linen':'d8c9a7','linen_shadow':'a89a7a','brass':'b59862','silver':'b6a17e','silver_light':'d5bf97','silver_shadow':'837256'}, {'teal_wool':'975749','teal_light':'b77c67','teal_shadow':'6b3d37','linen':'dbccb0','linen_shadow':'ac9b7d','brass':'b69559','silver':'3c3535','silver_light':'64504b','silver_shadow':'24262a'}, {'teal_wool':'5b638d','teal_light':'818db0','teal_shadow':'3c425f','linen':'d2c5b5','linen_shadow':'a2927f','brass':'b89a68','silver':'a16d40','silver_light':'c3945d','silver_shadow':'72492f'}]
def generate(seed,role,district,index=0,outfit_id=None):
 rng=random.Random(seed)
 if district not in RULES['district_roles'] or role not in RULES['district_roles'][district]:raise ValueError('Occupation/district combination not allowed')
 allout={o['id']:o for o in json.loads((HERE/'clothing_library/outfit_examples.json').read_text())['outfits']}
 choices=[x for x in RULES['occupation_outfits'][role] if x in allout]
 outfit_id=outfit_id or rng.choice(choices)
 if outfit_id not in choices:raise ValueError('Occupation/outfit combination not allowed')
 outfit=allout[outfit_id];body=outfit['age_frame']
 p={'schema':'riverstone.character.assembly.v1','id':f'resident_{index:02d}_{outfit_id}','body':body,'face':rng.choice(['oval','square','soft_taper']),'hair':rng.choice(['swept_bob','short_crop']),'costume':outfit['modules'],'ornaments':[],'palette':copy.deepcopy(rng.choice(PALETTES)),'role':role,'district':district,'seed':seed,'outfit_id':outfit_id}
 if index%3==1:p['palette'].update({'skin':'bd8970','skin_shadow':'916553','skin_light':'d8a489'})
 if index%3==2:p['palette'].update({'skin':'e2b699','skin_shadow':'b78870','skin_light':'edc7ac'})
 assemble(p)
 return p

def main():
 dump(HERE/'data/combination_rules.json',RULES)
 outfits=json.loads((HERE/'clothing_library/outfit_examples.json').read_text())['outfits'];presets=[]
 for i,o in enumerate(outfits):
  child=o['age_frame']=='child';p=generate(61019+i,'child' if child else 'resident','residential',i,o['id']);dump(HERE/'data/presets'/(p['id']+'.json'),p);presets.append({'preset':p['id'],'path':'data/presets/'+p['id']+'.json','outfit':o['id'],'body':p['body']})
 dump(HERE/'data/resident_review_index.json',{'schema':'riverstone.character.review_index.v1','presets':presets,'art_acceptance':'pending actual images','scope':'appearance combinations only'})
 print('Authored',len(presets),'reproducible resident combinations')
if __name__=='__main__':main()
