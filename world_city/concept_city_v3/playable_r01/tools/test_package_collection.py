#!/usr/bin/env python3
"""Tiny temporary fixtures only: never build a ZIP or extract a real package."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import package_playable as p


class PackageCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='playable-package-unit-')
        self.root = Path(self.temp.name)
        self.city = self.root/'world_city/concept_city_v3'
        self.playable = self.city/'playable_r01'
        self.patch = patch.multiple(p, ROOT=self.root, C=self.city, P=self.playable,
                                    OUT=self.city/'checkpoints/playable_r01')
        self.patch.start()
        self.hidden = self.put('world_city/concept_city_v3/historical/hidden.json', '{"original":true}')
        self.put('world_city/concept_city_v3/historical/unrequested.json', '{"do_not_collect":true}')
        self.put('world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json',
                 json.dumps({'sources': {}, 'common_assets': {}}))
        self.put('world_city/concept_city_v3/playable_r01/validation/PORTABLE_VALIDATION_INPUTS.json', '{"files":[]}')
        self.put('world_city/concept_city_v3/playable_r01/character/source_binding.json', '{"files":[]}')
        self.dependencies = self.put('world_city/concept_city_v3/playable_r01/tools/packaging_dependencies.json',
                                    json.dumps({'schema':'riverstone.playable.packaging_dependencies.v1',
                                                'additional_files':[self.reference(self.hidden)]}))
        self.put('world_city/concept_city_v3/playable_r01/project.godot', '[application]')

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def put(self, relative, content):
        path = self.root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def reference(self, path):
        return {'path':str(path.relative_to(self.root)), 'bytes':path.stat().st_size, 'sha256':p.sha(path)}

    def test_exact_additional_file_and_no_blind_history(self):
        files = p.collect()
        self.assertIn(self.hidden, files)
        self.assertNotIn(self.hidden.with_name('unrequested.json'), files)
        self.assertEqual(len(files), len(set(files)))

    def test_reject_dependency_hash_and_size_drift(self):
        self.hidden.write_text('{"modified":true}')
        with self.assertRaisesRegex(ValueError, 'drift'):
            p.collect()

    def test_reject_duplicate_dependency(self):
        data=json.loads(self.dependencies.read_bytes())
        data['additional_files']*=2
        self.dependencies.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            p.collect()

    def test_prune_live_distribution_release_and_gui_staging(self):
        excluded = [
            'distribution/windows_r01/project/copied.py',
            'distribution/windows_r01/project/world_city/deep.py',
            'distribution/windows_r01/release/Lily.exe',
            'distribution/windows_r01/validation_pe/report.json',
            'release/Lily.pck', 'export_templates/windows.exe',
            'evidence/gui_r02/source/copied.py', 'evidence/gui_r02/frames/frame.png',
        ]
        for relative in excluded:
            self.put('world_city/concept_city_v3/playable_r01/'+relative, 'preserve separately')
        report=self.put('world_city/concept_city_v3/playable_r01/evidence/gui_r02/report.json', '{}')
        original={relative:(self.playable/relative).read_bytes() for relative in excluded}
        files=set(p.collect())
        self.assertIn(report,files)
        for relative in excluded:
            self.assertNotIn(self.playable/relative, files)
            self.assertEqual((self.playable/relative).read_bytes(),original[relative])
        policy=p.exclusion_manifest()
        self.assertTrue(policy['preserved_separately_in_repository'])
        self.assertIn('frames',policy['gui_staging']['child_directories'])

    def test_explicit_staging_reference_fails_closed(self):
        path=self.put('world_city/concept_city_v3/playable_r01/distribution/windows_r01/release/not_source.json','{}')
        data=json.loads(self.dependencies.read_bytes());data['additional_files']=[self.reference(path)]
        self.dependencies.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'excluded staging'):
            p.collect()

    def test_r02_output_and_filename_without_creating_them(self):
        output,archive=p.output_paths('r02')
        self.assertEqual(output,self.city/'checkpoints/playable_r02')
        self.assertEqual(archive.name,'city_playable_r02_source_runtime.zip')
        self.assertFalse(output.exists())
        output,archive=p.output_paths('r02','world_city/concept_city_v3/checkpoints/custom_r02','source_r02.zip')
        self.assertEqual(archive,output/'source_r02.zip')
        self.assertFalse(output.exists())

    def test_existing_r01_output_is_never_reused(self):
        sealed=self.city/'checkpoints/playable_r01';sealed.mkdir(parents=True)
        sentinel=sealed/'manifest.json';sentinel.write_text('sealed')
        with self.assertRaisesRegex(ValueError,'Refusing to replace'):
            p.output_paths('r01')
        self.assertEqual(sentinel.read_text(),'sealed')

    def test_reject_escaping_output_bad_revision_and_filename(self):
        for kwargs in [{'revision':'../r02'}, {'output':'../outside'}, {'filename':'../escape.zip'}, {'filename':'bad\\escape.zip'}, {'filename':'not_zip.exe'}]:
            with self.assertRaises(ValueError):
                p.output_paths(**kwargs)


if __name__=='__main__':
    unittest.main(verbosity=2)
