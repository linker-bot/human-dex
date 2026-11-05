import unittest
from shared.hand_adapter import HandAdapter, JOINTS, split_action


def config(model='L20lite'):
    return {'model': model, 'hands': {s: {k: {j: {'name': j, 'scale': 0.01, 'offset': 0.1} for j in JOINTS} for k in ('state', 'command')} for s in ('left', 'right')}}


class AdapterTests(unittest.TestCase):
    def test_reorder_and_roundtrip(self):
        a = HandAdapter(config(), 'left')
        values = a.decode(list(reversed(JOINTS)), list(range(10)))
        self.assertAlmostEqual(values[0], .19)
        names, raw = a.encode(values)
        self.assertEqual(names, list(JOINTS))
        for expected, actual in zip(values, a.decode(names, raw, 'command')):
            self.assertAlmostEqual(expected, actual)

    def test_signed_and_mimic_limits(self):
        a = HandAdapter(config('l10v6'), 'left')
        _, raw = a.encode([0]*6 + [-.1, 0, -.2, 0])
        decoded = a.decode(list(JOINTS), raw, 'command')
        self.assertAlmostEqual(decoded[6], -.1)
        self.assertAlmostEqual(decoded[8], -.2)
        a = HandAdapter(config('l10v6'), 'right')
        self.assertLessEqual(a.bounds[2][1] * 2.24, 1.0467)

    def test_invalid(self):
        a = HandAdapter(config(), 'left')
        with self.assertRaises(ValueError):
            a.encode([float('nan')]*10)
        with self.assertRaises((ValueError, IndexError)):
            a.decode(list(JOINTS[:9]), [0]*9)
        self.assertEqual(a.decode([], [], optional=True), [])
        self.assertEqual(a.decode(list(JOINTS), [1]*10, velocity=True), [.01]*10)

    def test_unequal_split(self):
        arms, left, right = split_action(list(range(17)), 2, 3, 5, 7)
        self.assertEqual(left, list(range(5, 10)))
        self.assertEqual(right, list(range(10, 17)))
        with self.assertRaises(ValueError):
            split_action([0]*30)

    def test_configuration_rejected_at_startup(self):
        for change in (
            {'name': '' , 'scale': 1, 'offset': 0},
            {'index': 10, 'scale': 1, 'offset': 0},
            {'name': 'channel', 'scale': True, 'offset': 0},
            {'name': 'channel', 'scale': 1},
        ):
            c = config()
            c['hands']['left']['command'][JOINTS[0]] = change
            with self.assertRaises(ValueError):
                HandAdapter(c, 'left')
        with self.assertRaises(ValueError):
            HandAdapter(config(), 'invalid')

    def test_integer_task_dimensions(self):
        import runpy
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for path, task in (
            ('humanplus/scripts/utils/HIT/constants.py', 'data_cb_grasp'),
            ('recorddata/src/record_hdf5/scripts/utils/constants.py', 'data_columbus_test'),
        ):
            task_config = runpy.run_path(str(root / path))['TASK_CONFIGS'][task]
            for key in ('state_dim', 'action_dim', 'joint_total'):
                self.assertEqual(task_config[key], 32)
            self.assertEqual(len(task_config['state_mask']), 32)
            self.assertEqual(len(task_config['action_mask']), 32)

    def test_index_order(self):
        c = config()
        for k in ('state', 'command'):
            c['hands']['left'][k] = {j: {'index': 9-i, 'scale': 1, 'offset': 0} for i,j in enumerate(JOINTS)}
        a = HandAdapter(c, 'left')
        names, values = a.encode([.1]*10)
        self.assertEqual(names, [])
        self.assertEqual(a.decode([], values), [.1]*10)


if __name__ == '__main__':
    unittest.main()
