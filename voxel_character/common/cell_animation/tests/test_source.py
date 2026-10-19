"""Read-only source contract comparison, separate from the generic runtime."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
COMMON = HERE.parent
ROOT = COMMON.parent
sys.path.insert(0, str(COMMON))
import coordinate_planes
spec=importlib.util.spec_from_file_location('cell_animation_builder_source_test',HERE/'build_render.py')
build=importlib.util.module_from_spec(spec); spec.loader.exec_module(build)


class PreservedSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master=json.loads((COMMON/'assets/fountain/master.json').read_text())
        cls.original=json.loads((ROOT/'master/fountain_master.json').read_text())
        cls.clip=json.loads((HERE/'data/flow_clip.json').read_text())
        cls.render=json.loads((HERE/'generated/flow_pitch_0.1_r4.json').read_text())
        cls.rules=cls.original['voxel_state_animation']

    def test_primary_authored_functions(self):
        rules=self.rules;clip=self.clip;flow,column,moving=clip['pools']
        for key,source in [('duration','duration_seconds'),('loop','loop'),('update_hz','update_hz')]:
            self.assertEqual(clip[key],rules[source])
        for key,source in [('speed','speed_world_per_second'),('band_size','band_height_world'),('cycle','cycle_bands'),('bright_bands','bright_bands')]:
            self.assertEqual(flow['banded_color'][key],rules['flow'][source])
        self.assertEqual(flow['palette'],[rules['flow']['base_color'],rules['flow']['highlight_color']])
        self.assertEqual(column['threshold_visibility']['keys'],rules['plume']['height_keys'])
        self.assertEqual(column['threshold_visibility']['interpolation'],rules['plume']['interpolation'])
        self.assertEqual(moving['ballistic']['period'],rules['splash']['period_seconds'])
        self.assertEqual(moving['ballistic']['acceleration'],[0,-rules['splash']['gravity_world_per_second_squared'],0])
        self.assertEqual(moving['palette'],[rules['splash']['color'],rules['splash']['secondary_color']])
        self.assertEqual(self.master['extensions']['voxel_state_animation'],rules)

    def test_48_original_trajectory_members_and_resolved_anchors(self):
        members=self.clip['pools'][2]['source']['members'];pool=self.render['cell_animation']['pools'][2]
        anchors=[a for a in self.master['extensions']['functional_anchors'] if a['connection'] in self.rules['splash']['impact_connections']]
        self.assertEqual(len(anchors),8);self.assertEqual(len(members),48)
        _, info=coordinate_planes.resolve_master(self.master, {'pitch':.1})
        planes={name:p['value'] for name,p in info.items()}
        for ai,anchor in enumerate(anchors):
            for ti,trajectory in enumerate(self.rules['splash']['trajectories']):
                i=ai*6+ti;member=members[i]
                radial=anchor['direction_world'];tangent=[-radial[2],0,radial[0]]
                expected=[radial[d]*trajectory['velocity_radial']+tangent[d]*trajectory['velocity_tangent']+(trajectory['velocity_up'] if d==1 else 0) for d in range(3)]
                self.assertEqual(member['velocity'],expected)
                self.assertEqual(member['phase'],trajectory['phase_seconds']+ai*self.rules['splash']['anchor_phase_seconds'])
                self.assertEqual(member['lifetime'],trajectory['lifetime_seconds'])
                self.assertEqual(member['color_index'],0 if i%3 else 1)
                origin=[anchor['impact_world'][0],planes[anchor['receiving_surface']+'_top']+pool['cell_size']*.5,anchor['impact_world'][2]]
                self.assertEqual(pool['positions'][i],origin)

    def test_analytic_states_against_original_scalar_rules(self):
        animation=self.render['cell_animation'];flow,column,moving=animation['pools']
        rule=self.rules
        # Float64 mathematical reference for the source rule, not bitwise legacy Vector3.
        for frame in range(24):
            t=frame/10;actual=build.evaluate(animation,t)['pools']
            expected=[1 if math.floor((p[1]+t*rule['flow']['speed_world_per_second'])/rule['flow']['band_height_world'])%rule['flow']['cycle_bands']<rule['flow']['bright_bands'] else 0 for p in flow['positions']]
            self.assertEqual(actual[0]['color_indices'],expected)
            keys=rule['plume']['height_keys']
            for start,end in zip(keys,keys[1:]):
                if t<=end[0]:height=start[1]+(end[1]-start[1])*(t-start[0])/(end[0]-start[0]);break
            visible=[i for i,p in enumerate(column['positions']) if p[1]<=height+1e-8]
            self.assertEqual(actual[1]['member_ids'],visible)
            self.assertEqual(actual[1]['color_indices'],[1 if (math.floor(column['positions'][i][1]/.1)+math.floor(t*8))%3==0 else 0 for i in visible])
            live=[];positions=[]
            for i,(origin,velocity,phase,life) in enumerate(zip(moving['positions'],moving['ballistic']['velocities'],moving['ballistic']['phases'],moving['ballistic']['lifetimes'])):
                age=(t-phase)%rule['splash']['period_seconds']
                if age>=life-min(1e-8,life*1e-6):continue
                offset=[v*age for v in velocity];offset[1]-=.5*rule['splash']['gravity_world_per_second_squared']*age*age
                if offset[1]<-1e-8:continue
                live.append(i);positions.append([(math.floor((origin[d]+offset[d])/.1)+.5)*.1 for d in range(3)])
            self.assertEqual(actual[2]['member_ids'],live)
            self.assertEqual(actual[2]['positions'],positions)
            self.assertEqual(actual[2]['color_indices'],[0 if i%3 else 1 for i in live])

    def test_no_required_frame_table(self):
        self.assertNotIn('states',self.clip);self.assertNotIn('states',self.render['cell_animation'])
        self.assertEqual([len(p['positions']) for p in self.render['cell_animation']['pools']],[256,36,48])
        self.assertEqual(self.clip['seed'],0)

if __name__=='__main__':unittest.main(verbosity=2)
