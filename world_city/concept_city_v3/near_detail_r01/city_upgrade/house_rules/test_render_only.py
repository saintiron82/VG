"""Retained-cell versus transient-cell rendering and tamper rejection."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import adapter as a
import layered_compile as layer
import render_only_qa as qa
import test_connected_constraints as connected_fixtures


class RenderOnlyContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=layer.HERE);cls.d=Path(cls.temp.name)
        master=connected_fixtures.ConnectedConstraintContracts().master([([-.3,-.1,-.1],[.35,.2,.2])])
        master['constraints']=[{'id':'joined','kind':'connected','selector':{}}]
        master['provenance']={'city_near_material_extension':{'seed':41873}}
        cls.source=cls.d/'source.json';cls.source.write_text(json.dumps(master))
        authored=cls.d/'authored.master.json.gz'
        with gzip.open(authored,'wt') as f:json.dump(master,f)
        cls.catalog=cls.d/'catalog.json';cls.catalog.write_text(json.dumps({'assets':[{'asset_key':'render_toy','source_master_path':str(cls.source.relative_to(a.ROOT)),
            'source_sha256':a.sha(cls.source),'emitted_master_path':str(authored.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(authored)}]}))
        rules=a.load(layer.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
        cls.rule_path=cls.d/'rules.json';cls.rule_path.write_text(json.dumps(rules))
        cls.retained=layer.run('render_toy',cls.d/'retained',cls.rule_path,cls.catalog)
        cls.transient=layer.run('render_toy',cls.d/'transient',cls.rule_path,cls.catalog,render_only=True)
        cls.repeat=layer.run('render_toy',cls.d/'repeat',cls.rule_path,cls.catalog,render_only=True)
        cls.rs=cls.d/'retained/render_toy.layered.stats.json';cls.ts=cls.d/'transient/render_toy.layered.stats.json'

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def altered(self,fn):
        value=copy.deepcopy(self.transient);fn(value)
        p=self.d/'altered.stats.json';p.write_text(json.dumps(value));return p

    def test_retained_cells_and_transient_render_exact_parity(self):
        result=qa.verify(self.ts,self.catalog,self.rs)
        self.assertTrue(result['pass'],result['checks'])
        self.assertEqual(result['status'],'PASS_RETAINED_CELL_PARITY')
        self.assertFalse(list((self.d/'transient').glob('*cells*')))
        self.assertEqual(self.transient['authoring_seed'],41873)
        for key in ('groups','bounds','cell_count','materials','master_hash'):
            r=json.load(gzip.open(a.ROOT/self.retained['files']['.render.json']['path'],'rt'))
            t=json.load(gzip.open(a.ROOT/self.transient['files']['.render.json']['path'],'rt'))
            self.assertEqual(r[key],t[key])

    def test_repeated_sampling_reproduces_render_bytes_and_fingerprints(self):
        self.assertEqual(self.transient['files']['.render.json']['sha256'],self.repeat['files']['.render.json']['sha256'])
        for key in ('full_fine_fingerprint','fine_face_fingerprint','occupancy_certificate_sha256'):
            self.assertEqual(self.transient[key],self.repeat[key])
        self.assertTrue(qa.verify(self.ts,self.catalog)['pass'])

    def test_fingerprint_tamper_fails(self):
        p=self.altered(lambda s:s['full_fine_fingerprint'].update(count=999))
        self.assertFalse(qa.verify(p,self.catalog)['pass'])

    def test_chunk_overlap_fails(self):
        def change(s):s['chunks'][1]['chunk']=s['chunks'][0]['chunk']
        self.assertFalse(qa.verify(self.altered(change),self.catalog)['checks']['chunk_ownership_nonoverlapping'])

    def test_snapshot_hash_tamper_fails(self):
        def change(s):s['replay_contract']['code_snapshots']['core']['sha256']='0'*64
        self.assertFalse(qa.verify(self.altered(change),self.catalog)['checks']['replay_snapshot_hashes'])

    def test_render_hash_tamper_fails(self):
        def change(s):s['files']['.render.json']['sha256']='0'*64
        self.assertFalse(qa.verify(self.altered(change),self.catalog)['checks']['render_size_hash'])

    def test_source_hash_mismatch_rejected_before_voxel_compile(self):
        old=self.source.read_bytes()
        try:
            self.source.write_bytes(old+b' ')
            with self.assertRaises(a.UnsupportedSurface):layer.run('render_toy',self.d/'bad_source',self.rule_path,self.catalog,render_only=True)
        finally:self.source.write_bytes(old)

    def test_global_constraint_failure_never_commits_render(self):
        # Failure checked by the same global aggregation as retained mode.
        catalog=json.loads(self.catalog.read_text());source=self.d/'failed_source.json'
        master=json.loads(self.source.read_text());master['constraints']=[{'id':'missing','kind':'nonempty','selector':{'part':'absent'}}]
        source.write_text(json.dumps(master));entry=catalog['assets'][0]
        for pathkey in ('source_master_path','emitted_master_path'):entry[pathkey]=str(source.relative_to(a.ROOT))
        for shakey in ('source_sha256','emitted_master_sha256'):entry[shakey]=a.sha(source)
        cp=self.d/'failed_catalog.json';cp.write_text(json.dumps(catalog))
        with self.assertRaises(a.UnsupportedSurface):layer.run('render_toy',self.d/'failed',self.rule_path,cp,render_only=True)
        self.assertFalse((self.d/'failed/render_toy.layered.render.json.gz').exists())

if __name__=='__main__':unittest.main()
