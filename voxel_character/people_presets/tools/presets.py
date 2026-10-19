#!/usr/bin/env python3
"""Small appearance DATA generator. Geometry is exclusively lily_city.tools.appearance.
Never imports or enables the paused resident scheduler; no simulation/role assignment.
"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, itertools, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
LILY=HERE.parent/'lily_city'
RULES_PATH=HERE/'data/rules.json'
CONTRACT_PATH=LILY/'data/appearance_contract.json'

def read(path): return json.loads(Path(path).read_text())
def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()
def file_sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def appearance_module():
    spec=importlib.util.spec_from_file_location('riverstone_shared_appearance',LILY/'tools/appearance.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def choose(seed, person_id, field, options, version=1):
    if not options: raise ValueError('empty choice set: '+field)
    token=canonical([version,str(seed),person_id,field]).encode()
    return options[int.from_bytes(hashlib.sha256(token).digest()[:8],'big')%len(options)]

def validate_rules(rules, contract):
    if rules['family']!=contract['family']: raise ValueError('appearance family mismatch')
    for key,target in [('body_frames','body_frames'),('faces','faces'),('hair_styles','hair_styles'),('outfits','outfits')]:
        if not set(rules[key])<=set(contract[target]): raise ValueError('unsupported choices: '+key)
    for row in rules['accessories']:
        if set(row)!=set(contract['accessory_keys']) or any(type(v) is not bool for v in row.values()): raise ValueError('accessory contract drift')
    if not set(rules['fixed_palette'])<=set(contract['palette_slots']): raise ValueError('palette contract drift')
    return True

def make_preset(seed, person_id, rules=None):
    if not isinstance(person_id,str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',person_id): raise ValueError('stable safe lower-case person ID required')
    rules=rules or read(RULES_PATH)
    contract=read(CONTRACT_PATH);validate_rules(rules,contract)
    pick=lambda tag,options: choose(seed,person_id,tag,options,rules['generator_version'])
    selections={k:pick(k,sorted(rules[k])) for k in ['skin_palettes','hair_palettes','cloth_palettes','linen_palettes','leather_palettes','iris_palettes']}
    palette=copy.deepcopy(rules['fixed_palette'])
    palette.update(rules['skin_palettes'][selections['skin_palettes']])
    for group,slots in [('hair_palettes',['silver','silver_light','silver_shadow']),('cloth_palettes',['teal_wool','teal_light','teal_shadow']),
                        ('linen_palettes',['linen','linen_shadow']),('leather_palettes',['leather','leather_light','leather_dark']),('iris_palettes',['iris','iris_light'])]:
        palette.update(zip(slots,rules[group][selections[group]]))
    return {'schema':contract['preset_schema'],'id':person_id,'display_name':person_id.replace('_',' ').title(),'family':contract['family'],
      'body_frame':pick('body_frame',rules['body_frames']),'face':pick('face',rules['faces']),
      'hair_style':pick('hair_style',rules['hair_styles']),'outfit':pick('outfit',rules['outfits']),
      'palette':palette,'accessories':copy.deepcopy(pick('accessories',rules['accessories'])),
      'provenance':{'generator':'people_presets.v1','seed':str(seed),'stable_person_id':person_id,'palette_choices':selections,
                    'rules_sha256':file_sha(RULES_PATH),'appearance_contract_sha256':file_sha(CONTRACT_PATH)},
      'qualification':'Adult appearance data only. No gender, occupation, class, behavior or population count is inferred.'}

def cohort(seed, ids):
    if len(ids)!=len(set(ids)): raise ValueError('duplicate person IDs')
    return [make_preset(seed,id) for id in ids]

def geometry_combinations(seed=41029):
    rules=read(RULES_PATH)
    for index,(body,face,hair,outfit,accessories) in enumerate(itertools.product(rules['body_frames'],rules['faces'],rules['hair_styles'],rules['outfits'],rules['accessories'])):
        p=make_preset(seed,f'combination_{index:03}')
        p.update(body_frame=body,face=face,hair_style=hair,outfit=outfit,accessories=copy.deepcopy(accessories))
        yield p

def geometry_signature(preset):
    return digest({k:preset[k] for k in ['body_frame','face','hair_style','outfit','accessories']})

def report(presets):
    return {'count':len(presets),'unique_ids':len({p['id'] for p in presets}),
      'unique_geometry_combinations':len({geometry_signature(p) for p in presets}),
      'unique_full_appearances':len({digest({k:p[k] for k in ['body_frame','face','hair_style','outfit','accessories','palette']}) for p in presets}),
      'coverage':{key:sorted({p[key] for p in presets}) for key in ['body_frame','face','hair_style','outfit']},
      'palette_coverage':{key:sorted({p['provenance']['palette_choices'][key] for p in presets}) for key in presets[0]['provenance']['palette_choices']} if presets else {},
      'no_meshes_instantiated':True,'visual_acceptance':'pending'}

def generate(output,seed,count):
    if output.exists(): raise FileExistsError('Use a NEW output directory; previous artifacts are immutable')
    if not 1<=count<=10000: raise ValueError('count must be 1..10000, data records only')
    presets=cohort(seed,[f'person_{i:04}' for i in range(count)])
    shared=appearance_module()
    for preset in presets: shared.validate_preset(preset)
    output.mkdir(parents=True)
    artifact={'schema':'riverstone.people.preset_collection.v1','seed':str(seed),'presets':presets,'summary':report(presets)}
    (output/'people.json').write_text(json.dumps(artifact,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    # Six review samples cover each body frame and each outfit/hair style.
    showcase=[]
    for i,(body,hair,outfit) in enumerate([('slender','braided','traveller_tunic'),('standard','cropped','work_tunic'),('broad','loose','guard_tabard'),
                                        ('slender','loose','work_tunic'),('standard','braided','guard_tabard'),('broad','cropped','traveller_tunic')]):
        p=make_preset(seed,f'review_{i:02}');p.update(body_frame=body,hair_style=hair,outfit=outfit,face='soft' if i%2==0 else 'angular',accessories={'cape':i%3==0,'satchel':i%2==0})
        (output/(p['id']+'.json')).write_text(json.dumps(p,ensure_ascii=False,sort_keys=True,indent=2)+'\n');showcase.append(p['id'])
    manifest={'schema':'riverstone.people.preset_manifest.v1','seed':str(seed),'summary':artifact['summary'],'review_presets':showcase,
      'sources':{str(p.relative_to(HERE.parent)):file_sha(p) for p in [RULES_PATH,Path(__file__),LILY/'tools/appearance.py',*sorted((LILY/'data').glob('*.json')),HERE.parent/'common/core.py',HERE.parent/'common/animation/build_render.py']},
      'files':{p.name:file_sha(p) for p in sorted(output.iterdir()) if p.is_file()},'geometry_builder':'lily_city/tools/appearance.py',
      'not_population_or_runtime_agents':True,'visual_acceptance':'pending'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',default='41029');p.add_argument('--count',type=int,default=100);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(a.output,a.seed,a.count),ensure_ascii=False,indent=2))
