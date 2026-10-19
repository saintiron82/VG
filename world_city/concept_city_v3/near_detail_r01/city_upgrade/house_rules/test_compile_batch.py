"""Tiny transaction tests; do not compile or rewrite real output artifacts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import compile_batch as batch


class AtomicBatchContracts(unittest.TestCase):
    def test_atomic_replace_commits_complete_json(self):
        with tempfile.TemporaryDirectory(dir=batch.HERE) as directory:
            p=Path(directory)/'manifest.json'
            batch.atomic_json(p,{'status':'old'})
            batch.atomic_json(p,{'status':'new','items':[1,2,3]})
            self.assertEqual(json.loads(p.read_text()),{'status':'new','items':[1,2,3]})
            self.assertFalse(p.with_name(p.name+'.tmp').exists())

    def test_serialization_failure_preserves_committed_manifest(self):
        with tempfile.TemporaryDirectory(dir=batch.HERE) as directory:
            p=Path(directory)/'manifest.json'
            batch.atomic_json(p,{'status':'verified'})
            with self.assertRaises(TypeError):batch.atomic_json(p,{'bad':object()})
            self.assertEqual(json.loads(p.read_text()),{'status':'verified'})

    def test_manifest_keeps_unsupported_pending_and_records_verified_only(self):
        with tempfile.TemporaryDirectory(dir=batch.HERE) as directory:
            d=Path(directory);catalog=d/'input.json';output=d/'output';output.mkdir()
            catalog.write_text(json.dumps({'assets':[{'asset_key':'ok','source_sha256':'s','emitted_master_path':'master.json','emitted_master_sha256':'m'},
                                                   {'asset_key':'hip','source_sha256':'h','reason':'unsupported roof'}]}))
            record={'status':'PASS_STRUCTURAL_PENDING_VISUAL','max_rss_kib':123,'independent_qa':{'pass':True}}
            with patch.object(batch,'inspect_output',return_value=record):result=batch.refresh_manifest(catalog,output)
            self.assertEqual(result['summary']['compiled'],1)
            self.assertEqual(result['summary']['coverage_pending'],1)
            self.assertEqual(result['assets'][1]['status'],'AUTHORING_COVERAGE_PENDING')
            self.assertEqual(result['summary']['independently_checked'],1)
            self.assertEqual(result['summary']['max_rss_kib'],123)
            self.assertTrue((output/'manifest.json').is_file())

    def test_hold_and_verified_replacement_selection(self):
        with tempfile.TemporaryDirectory(dir=batch.HERE) as directory:
            root=Path(directory);out=root/'output';out.mkdir();replacement=out/'native';replacement.mkdir()
            key='toy';artifact=root/'render.json';artifact.write_text('{}')
            stats={'status':'PASS_STRUCTURAL_PENDING_VISUAL','source_master_sha256':'s','authored_master_sha256':'a',
                'files':{'.render.json':{'path':str(artifact.relative_to(batch.a.ROOT)),'sha256':batch.a.sha(artifact),'bytes':2}},
                'reference_full_fine_cells':1,'stored_fine_cells':1,'stored_core_cells':0,'quads':6,'visible_unit_faces':6,
                'max_rss_kib':1,'elapsed_seconds':1,'core_visible_faces':0,'chunks':[{}],'source_unchanged':True}
            old=out/(key+'.layered.stats.json');old.write_text(json.dumps(stats))
            batch.atomic_json(out/'provenance_holds.json',{'assets':{key:{'status':'PENDING_NATIVE_REISSUE'}}})
            self.assertEqual(batch.inspect_output(key,out)['status'],'PENDING_NATIVE_REISSUE')
            new=replacement/old.name;new.write_text(json.dumps(stats));qa=replacement/(key+'.layered.qa.json');qa.write_text('{"pass":true}')
            override={'stats_path':str(new.relative_to(batch.a.ROOT)),'stats_sha256':batch.a.sha(new),
                      'qa_path':str(qa.relative_to(batch.a.ROOT)),'qa_sha256':batch.a.sha(qa)}
            batch.atomic_json(out/'selection_overrides.json',{'assets':{key:override}})
            result=batch.inspect_output(key,out)
            self.assertTrue(result['status'].startswith('PASS'));self.assertEqual(result['stats_path'],override['stats_path'])
            new.write_text(new.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'override stats hash mismatch'):batch.inspect_output(key,out)


if __name__=='__main__':unittest.main()
