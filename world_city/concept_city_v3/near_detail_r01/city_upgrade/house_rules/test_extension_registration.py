import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import register_extension_outputs as registration


class ExtensionRegistrationContracts(unittest.TestCase):
    def test_requires_both_qa_and_replay_and_preserves_existing_mapping(self):
        with tempfile.TemporaryDirectory(dir=registration.b.HERE) as d:
            root=Path(d);home=root/'rules';home.mkdir();(home/'compiled').mkdir()
            catalog=root/'house_extensions/generated/active_catalog.json';catalog.parent.mkdir(parents=True)
            entry={'asset_key':'row','source_master_path':'source','source_sha256':'s','emitted_master_path':'master','emitted_master_sha256':'m'}
            catalog.write_text(json.dumps({'assets':[entry]}));overrides=home/'compiled/selection_overrides.json'
            overrides.write_text(json.dumps({'assets':{'old':{'stats_path':'preserved'}}}))
            record={'status':'PASS_STRUCTURAL_PENDING_VISUAL','stats_path':'stats','stats_sha256':'hash',
                'independent_qa':{'path':'qa','sha256':'q','pass':True}}
            with patch.object(registration.b,'HERE',home),patch.object(registration.b,'inspect_output',return_value=record):
                self.assertEqual(registration.publish()['added'],[])
                record['independent_replay']={'path':'replay','sha256':'r','pass':True}
                self.assertEqual(registration.publish()['added'],['row'])
                previous=overrides.read_bytes();self.assertEqual(registration.publish()['added'],[])
                self.assertEqual(overrides.read_bytes(),previous)
                record['stats_sha256']='different'
                with self.assertRaisesRegex(ValueError,'selection differs'):registration.publish()
                self.assertEqual(overrides.read_bytes(),previous)
            self.assertEqual(json.loads(overrides.read_text())['assets']['old'],{'stats_path':'preserved'})

if __name__=='__main__':unittest.main()
