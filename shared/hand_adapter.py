"""Explicit hardware channels <-> canonical independent joint radians.

No default hardware mapping is assumed. Configure state and command separately.
"""
import json
import math
import os
from pathlib import Path

JOINTS = ('thumb_cmc_roll', 'thumb_cmc_yaw', 'thumb_cmc_pitch',
          'index_mcp_roll', 'index_mcp_pitch', 'middle_mcp_pitch',
          'ring_mcp_roll', 'ring_mcp_pitch', 'pinky_mcp_roll', 'pinky_mcp_pitch')


def limits(model, side):
    if model == 'L20lite':
        ranges = [(0, 1.03), (0, 1.4), (0, .52), (0, .19),
                  (0, min(1.36, .62 / .46)), (0, min(1.36, .62 / .46)),
                  (0, .2), (0, min(1.36, .62 / .46, 1.78 / (1.34 if side == 'right' else 1.3))),
                  (0, .3), (0, min(1.36, .62 / .46, 1.78 / (1.34 if side == 'right' else 1.3)))]
    elif model == 'l10v6':
        ranges = [(-.785, .785), (0, 1.57),
                  (0, .5285 if side == 'left' else min(.5286, 1.0467 / 2.24, 1.256 / 2.38)),
                  (0, .2268) if side == 'left' else (-.2268, 0), (0, 1.325),
                  (0, 1.325), (-.2093, 0) if side == 'left' else (0, .2093),
                  (0, 1.325), (-.3663, 0) if side == 'left' else (0, .3663), (0, 1.325)]
    else:
        raise ValueError('Unsupported hand model: ' + str(model))
    return ranges


class HandAdapter:
    def __init__(self, config, side):
        self.side = side
        self.config = config
        self.model = config['model']
        self.bounds = limits(self.model, side)
        self.channels = config['hands'][side]
        for kind in ('state', 'command'):
            entries = self.channels[kind]
            if set(entries) != set(JOINTS):
                raise ValueError('Configure all ten joints for ' + side + '/' + kind)
            selectors = []
            for joint in JOINTS:
                entry = entries[joint]
                if not isinstance(entry, dict) or ('name' in entry) == ('index' in entry):
                    raise ValueError('Each channel needs exactly one name or index: ' + joint)
                selector = ('name', entry['name']) if 'name' in entry else ('index', entry['index'])
                if selector[0] == 'index' and (type(selector[1]) is not int or selector[1] < 0):
                    raise ValueError('Invalid channel index')
                selectors.append(selector)
                if not math.isfinite(entry['scale']) or entry['scale'] == 0 or not math.isfinite(entry['offset']):
                    raise ValueError('Invalid affine calibration')
            if len(set(selectors)) != 10:
                raise ValueError('Duplicate channels')

    @classmethod
    def load(cls, side):
        path = os.environ.get('HUMAN_DEX_HAND_CONFIG')
        if not path:
            raise ValueError('Set HUMAN_DEX_HAND_CONFIG to a calibrated mapping JSON; see shared/hand_mapping.example.json')
        with open(path) as stream:
            return cls(json.load(stream), side)

    def decode(self, names, values, kind='state', optional=False, velocity=False):
        if optional and len(values) == 0:
            return []
        if names and len(set(names)) != len(names):
            raise ValueError('Duplicate message names')
        out = []
        for joint in JOINTS:
            entry = self.channels[kind][joint]
            index = names.index(entry['name']) if 'name' in entry else entry['index']
            value = float(values[index]) * entry['scale'] + (0 if velocity else entry['offset'])
            if not math.isfinite(value):
                raise ValueError('Non-finite hand value')
            out.append(value)
        return out

    def encode(self, values):
        if len(values) != 10 or not all(math.isfinite(float(v)) for v in values):
            raise ValueError('Expected ten finite canonical hand angles')
        entries = self.channels['command']
        named = all('name' in entries[j] for j in JOINTS)
        indexed = all('index' in entries[j] for j in JOINTS)
        if not (named or indexed):
            raise ValueError('Command selectors must all be names or all be indices')
        order = list(JOINTS) if named else sorted(JOINTS, key=lambda j: entries[j]['index'])
        if indexed and [entries[j]['index'] for j in order] != list(range(10)):
            raise ValueError('Command indices must cover 0..9')
        clamped = {j: max(lo, min(hi, float(v))) for j, v, (lo, hi) in zip(JOINTS, values, self.bounds)}
        return ([entries[j]['name'] for j in order] if named else [],
                [(clamped[j] - entries[j]['offset']) / entries[j]['scale'] for j in order])


def split_action(action, left_arm=6, right_arm=6, left_hand=10, right_hand=10):
    if len(action) != left_arm + right_arm + left_hand + right_hand:
        raise ValueError('Action dimension does not match configured robot')
    arm_end = left_arm + right_arm
    return list(action[:arm_end]), list(action[arm_end:arm_end + left_hand]), list(action[arm_end + left_hand:])
