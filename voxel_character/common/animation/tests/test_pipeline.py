import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from build_render import make_animated_render,bindings_from,isolate
sys.path.insert(0,str(HERE.parent))
from core import compile_master,digest,InvalidMaster


def fixture():
    master={'schema':'riverstone.voxel.master.v1','id':'unrelated_box_fixture','revision':1,
       'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],
       'materials':{'clay':'997755'},'components':[{'id':'module','parts':[{'id':'piece','pivot':[0,0,0]}],
       'operations':[{'id':'volume','action':'paint','part':'piece','material':'clay','shape':{'kind':'box','min':[0,0,0],'max':[1,2,.5]}}]}],
       'instances':[{'id':'mobile','component':'module','transform':{'translation':[2,1,3]}},
                    {'id':'cover','component':'module','transform':{'translation':[2,1,3]}}], 'constraints':[]}
    clip=json.loads((HERE/'data/house_door.json').read_text())
    clip.update(source_id=master['id'],master_hash=digest(master))
    clip['tracks'][0]['selector']={'instance':'mobile','part':'piece'}
    return master,clip


class PipelineTests(unittest.TestCase):
    def setUp(self):self.master,self.clip=fixture()
    def test_independent_layers_preserve_hidden_part(self):
        composite=compile_master(self.master,{'pitch':.25})
        self.assertFalse(any(c[3]=='mobile' for c in composite['cells']))
        result=make_animated_render(self.master,self.clip,.25)
        self.assertEqual(result['rigid_parts'][0]['cell_count'],64)
        self.assertEqual(result['cell_count'],128)
        self.assertEqual(result['quad_count'],12)
    def test_animation_key_changes_do_not_change_geometry(self):
        a=make_animated_render(self.master,self.clip,.25)
        changed=copy.deepcopy(self.clip);changed['tracks'][0]['keys'][2]['rotation_degrees']=70
        b=make_animated_render(self.master,changed,.25)
        self.assertEqual(a,b)
    def test_pivot_same_at_two_pitches(self):
        a=make_animated_render(self.master,self.clip,.25)
        b=make_animated_render(self.master,self.clip,.125)
        self.assertEqual(a['rigid_parts'][0]['pivot_world'],[2,1,3])
        self.assertEqual(a['rigid_parts'][0]['pivot_world'],b['rigid_parts'][0]['pivot_world'])
    def test_exact_repeat(self):
        self.assertEqual(make_animated_render(self.master,self.clip,.25),make_animated_render(self.master,self.clip,.25))
    def test_no_mutation(self):
        before=copy.deepcopy((self.master,self.clip));make_animated_render(self.master,self.clip,.25)
        self.assertEqual((self.master,self.clip),before)
    def test_shared_component_instance_isolation(self):
        result=make_animated_render(self.master,self.clip,.25)
        self.assertEqual(result['provenance']['layers'][0]['cell_count'],64)
        self.assertEqual(result['provenance']['layers'][1]['cell_count'],64)
    def test_component_selector_assembly_cut_scalar_and_list(self):
        for value in ('module',['module'],['unknown','module']):
            self.master['assembly_cuts']=[{'id':'slice','shape':{'kind':'box','min':[2,1,3],'max':[2.5,3,3.5]},'selector':{'component':value}}]
            self.clip['master_hash']=digest(self.master)
            result=make_animated_render(self.master,self.clip,.25)
            self.assertEqual([l['cell_count'] for l in result['provenance']['layers']],[32,32])
    def test_component_selector_local_cut(self):
        self.master['components'][0]['operations'].append({'id':'slice','action':'cut','part':'piece','shape':{'kind':'box','min':[0,0,0],'max':[.5,2,.5]},'selector':{'component':'module'}})
        self.clip['master_hash']=digest(self.master)
        result=make_animated_render(self.master,self.clip,.25)
        self.assertEqual([l['cell_count'] for l in result['provenance']['layers']],[32,32])
    def test_component_selector_keeps_instance_intersection(self):
        self.master['assembly_cuts']=[{'id':'slice','shape':{'kind':'box','min':[2,1,3],'max':[2.5,3,3.5]},'selector':{'component':'module','instance':'mobile'}}]
        self.clip['master_hash']=digest(self.master)
        result=make_animated_render(self.master,self.clip,.25)
        self.assertEqual([l['cell_count'] for l in result['provenance']['layers']],[64,32])
    def test_unknown_component_cannot_accidentally_match_clone(self):
        self.master['assembly_cuts']=[{'id':'slice','shape':{'kind':'box','min':[2,1,3],'max':[2.5,3,3.5]},'selector':{'component':'isolated_component_0'}}]
        self.clip['master_hash']=digest(self.master)
        result=make_animated_render(self.master,self.clip,.25)
        self.assertEqual([l['cell_count'] for l in result['provenance']['layers']],[64,64])
    def test_part_pivot_uses_source_basis(self):
        self.master['components'][0]['parts'][0]['pivot']=[.5,1,0]
        self.master['instances'][0]['transform']['basis']=[[0,-1,0],[1,0,0],[0,0,1]]
        self.clip['master_hash']=digest(self.master)
        self.assertEqual(bindings_from(self.master,self.clip)[0]['pivot_world'],[1,1.5,3])
    def test_reject_unknown_part(self):
        self.clip['tracks'][0]['selector']['part']='missing'
        with self.assertRaises(InvalidMaster):make_animated_render(self.master,self.clip,.25)
    def test_reject_wrong_source(self):
        self.clip['master_hash']='old_revision'
        with self.assertRaises(InvalidMaster):make_animated_render(self.master,self.clip,.25)
    def test_reject_duplicate_selector(self):
        self.clip['tracks'].append(copy.deepcopy(self.clip['tracks'][0]))
        with self.assertRaises(InvalidMaster):make_animated_render(self.master,self.clip,.25)
    def test_canonical_runtime_byte_identical(self):
        self.assertEqual((HERE/'TransformTracks.gd').read_bytes(),(HERE.parent/'preview/AnimationTracks.gd').read_bytes())
    def test_original_house_pivot_contract(self):
        master=json.loads((HERE.parent/'assets/house/master.json').read_text());clip=json.loads((HERE/'data/house_door.json').read_text())
        binding=bindings_from(master,clip)[0]
        self.assertEqual(binding['pivot_world'],[.65,.6,2.72])
        self.assertEqual(binding['pivot_world'],master['extensions']['rigid_joint_contracts'][0]['pivot_world'])
    @unittest.skipUnless(shutil.which('godot'),'Godot required')
    def test_generic_runtime_and_preview_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder);env=dict(os.environ,HOME=folder,XDG_CONFIG_HOME=folder,XDG_DATA_HOME=folder,XDG_CACHE_HOME=folder)
            clip=temp/'clip.json';clip.write_text(json.dumps(self.clip))
            a=temp/'a.json';a.write_text(json.dumps(make_animated_render(self.master,self.clip,.25)))
            b=temp/'b.json';b.write_text(json.dumps(make_animated_render(self.master,self.clip,.125)))
            report=temp/'runtime.json'
            command=['godot','--headless','--path',str(HERE.parent/'preview'),'--script',str(HERE/'tests/CheckAnimation.gd'),'--',str(a),str(b),str(clip),str(report)]
            process=subprocess.run(command,env=env,text=True,capture_output=True,timeout=20)
            self.assertEqual(process.returncode,0,process.stdout+process.stderr)
            self.assertNotIn('SCRIPT ERROR',process.stdout+process.stderr)
            self.assertTrue(json.loads(report.read_text())['passed'])
            command=['godot','--headless','--path',str(HERE.parent/'preview'),'--','--left',str(a),'--right',str(b),'--animation',str(clip),'--animation-time=2.4','--paused','--validate-only','--report',str(temp/'viewer.json')]
            process=subprocess.run(command,env=env,text=True,capture_output=True,timeout=20)
            self.assertEqual(process.returncode,0,process.stdout+process.stderr)
            self.assertNotIn('SCRIPT ERROR',process.stdout+process.stderr)
            r=json.loads((temp/'viewer.json').read_text())
            self.assertTrue(r['animation']['same_phase'])
            self.assertTrue(r['animation']['mesh_resources_and_asset_roots_unchanged'])
            self.assertFalse(r['animation']['states'][0]['playing'])
            self.assertEqual(r['animation']['states'][0]['tracks'][0]['rotation_degrees'],105)

if __name__=='__main__':unittest.main()
