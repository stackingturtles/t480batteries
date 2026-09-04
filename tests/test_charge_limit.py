import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import charge_limit as control


class ChargeControlTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = self.root / 'mode.json'
        for name in ('BAT0', 'BAT1'):
            pack = self.root / name
            pack.mkdir()
            (pack / 'present').write_text('1')
            for kind, value in [('start', 0), ('end', 100)]:
                (pack / f'charge_control_{kind}_threshold').write_text(str(value))

    def apply(self, mode, **kwargs):
        return control.apply(mode, self.root, self.state, **kwargs)

    def test_both_presets_and_persistence(self):
        self.assertEqual(self.apply('enable'), {'BAT0': [75, 80], 'BAT1': [75, 80]})
        self.assertEqual(json.loads(self.state.read_text()), {'mode': 'enable'})
        self.assertEqual(self.apply('disable'), {'BAT0': [0, 100], 'BAT1': [0, 100]})

    def test_partial_failure_rolls_back_and_preserves_saved_mode(self):
        self.apply('disable')
        original = control.write_thresholds
        def fail(pack, values):
            if pack.name == 'BAT1' and values == (75, 80):
                raise OSError('simulated write failure')
            original(pack, values)
        with patch.object(control, 'write_thresholds', side_effect=fail):
            with self.assertRaises(OSError):
                self.apply('enable')
        self.assertEqual(control.thresholds(self.root / 'BAT0'), (0, 100))
        self.assertEqual(json.loads(self.state.read_text())['mode'], 'disable')

    def test_unsupported_pack_validated_before_any_write(self):
        (self.root / 'BAT1/charge_control_end_threshold').unlink()
        with self.assertRaises(OSError):
            self.apply('enable')
        self.assertEqual(control.thresholds(self.root / 'BAT0'), (0, 100))

    def test_reinsertion_and_restore_without_rewriting_state(self):
        (self.root / 'BAT1/present').write_text('0')
        self.assertEqual(self.apply('enable'), {'BAT0': [75, 80]})
        modified = self.state.stat().st_mtime_ns
        (self.root / 'BAT1/present').write_text('1')
        self.assertEqual(self.apply('enable', persist=False)['BAT1'], [75, 80])
        self.assertEqual(self.state.stat().st_mtime_ns, modified)

    def test_idempotent_restore_does_not_write_sysfs(self):
        self.apply('enable')
        with patch.object(Path, 'write_text', side_effect=AssertionError('unexpected write')):
            self.apply('enable', persist=False)

    def test_state_failure_rolls_back_hardware(self):
        with self.assertRaises(OSError):
            control.apply('enable', self.root, self.root / 'missing/mode.json')
        self.assertEqual(control.thresholds(self.root / 'BAT0'), (0, 100))
        self.assertEqual(control.thresholds(self.root / 'BAT1'), (0, 100))
