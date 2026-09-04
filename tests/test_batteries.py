import tempfile
import unittest
from pathlib import Path

from batteries import snapshot


class BatteriesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.supply("AC", type="Mains", online=0)

    def supply(self, name, **values):
        path = self.root / name
        path.mkdir(exist_ok=True)
        for key, value in values.items():
            (path / key).write_text(str(value))

    def pack(self, name="BAT0", **overrides):
        data = dict(type="Battery", present=1, status="Discharging", capacity=50,
                    energy_now=12_000_000, energy_full=24_000_000,
                    energy_full_design=24_000_000, power_now=6_000_000, cycle_count=0)
        data.update(overrides)
        self.supply(name, **data)

    def test_weighted_total_and_independent_cycles(self):
        self.pack(cycle_count=0)
        self.pack("BAT1", capacity=100, energy_now=72_000_000, energy_full=72_000_000,
                  cycle_count=2, status="Not charging", power_now=0)
        data = snapshot(self.root)
        self.assertEqual(data["percentage"], 87.5)
        self.assertEqual([b["cycles"] for b in data["batteries"]], [0, 2])
        self.assertEqual(data["batteries"][0]["seconds"], 7200)
        self.assertIsNone(data["batteries"][1]["seconds"])
        self.assertEqual(data["batteries"][1]["state"], "standby")

    def test_external_removal_and_reinsertion(self):
        self.pack()
        self.pack("BAT1", present=0)
        data = snapshot(self.root)
        self.assertFalse(data["batteries"][1]["present"])
        self.assertEqual(data["percentage"], 50)
        self.supply("BAT1", present=1)
        self.assertTrue(snapshot(self.root)["batteries"][1]["present"])

    def test_equal_percentages_can_diverge_independently(self):
        self.pack(capacity=91, status="Not charging", power_now=0)
        self.pack("BAT1", capacity=91)
        self.assertEqual([b["percentage"] for b in snapshot(self.root)["batteries"]], [91, 91])
        self.supply("BAT1", capacity=90)
        self.assertEqual([b["percentage"] for b in snapshot(self.root)["batteries"]], [91, 90])

    def test_no_batteries_is_not_zero_charge(self):
        data = snapshot(self.root)
        self.assertIsNone(data["percentage"])
        self.assertEqual(data["state"], "absent")

    def test_charging_time_uses_each_pack_not_whole_machine(self):
        self.supply("AC", online=1)
        self.pack(status="Charging", power_now=12_000_000)
        self.pack("BAT1", status="Not charging", power_now=0)
        data = snapshot(self.root)
        self.assertEqual(data["batteries"][0]["seconds"], 3600)
        self.assertTrue(data["batteries"][0]["estimated"])
        self.assertEqual(data["batteries"][1]["state"], "standby")
        self.assertEqual(data["state"], "charging")

    def test_charge_estimate_targets_limit_not_full(self):
        self.pack(status="Charging", charge_control_start_threshold=75,
                  charge_control_end_threshold=80, time_to_full_now=7200)
        b = snapshot(self.root)["batteries"][0]
        self.assertAlmostEqual(b["seconds"], 4320)
        self.assertTrue(b["estimated"])

    def test_thresholds_never_leak_between_batteries(self):
        self.supply("AC", online=1)
        self.pack(status="Not charging", capacity=80, power_now=0,
                  charge_control_start_threshold=75, charge_control_end_threshold=80)
        self.pack("BAT1", status="Charging", power_now=12_000_000,
                  charge_control_start_threshold=90, charge_control_end_threshold=95)
        a, b = snapshot(self.root)["batteries"]
        self.assertEqual(a["state"], "holding")
        self.assertEqual(a["thresholdEnd"], 80)
        self.assertEqual(b["thresholdEnd"], 95)
        self.assertEqual(b["state"], "charging")

    def test_zero_or_missing_rate_does_not_invent_time(self):
        self.pack(power_now=0)
        self.assertIsNone(snapshot(self.root)["batteries"][0]["seconds"])
        (self.root / "BAT0/power_now").unlink()
        self.assertIsNone(snapshot(self.root)["batteries"][0]["rateW"])

    def test_charge_and_signed_current_fallback(self):
        self.supply("BAT0", type="Battery", present=1, status="Discharging",
                    charge_now=1_000_000, charge_full=2_000_000,
                    voltage_min_design=12_000_000, voltage_now=12_000_000,
                    current_now=-500_000)
        b = snapshot(self.root)["batteries"][0]
        self.assertEqual((b["percentage"], b["energyWh"], b["fullWh"], b["rateW"]),
                         (50, 12, 24, 6))

    def test_bad_attributes_are_unknown_not_nan_or_zero(self):
        self.pack(capacity="NaN", energy_now="bad", energy_full=0,
                  cycle_count=-1, power_now="Infinity", status="Unknown")
        data = snapshot(self.root)
        self.assertIsNone(data["percentage"])
        self.assertIsNone(data["batteries"][0]["cycles"])
        self.assertIsNone(data["batteries"][0]["rateW"])
        self.assertEqual(data["batteries"][0]["state"], "unknown")

    def test_full_battery_has_no_time_to_full(self):
        self.pack(status="Full", capacity=100, power_now=0)
        b = snapshot(self.root)["batteries"][0]
        self.assertEqual(b["state"], "full")
        self.assertIsNone(b["seconds"])

    def test_native_time_is_not_marked_estimated(self):
        self.pack(time_to_empty_now=4200)
        b = snapshot(self.root)["batteries"][0]
        self.assertEqual(b["seconds"], 4200)
        self.assertFalse(b["estimated"])

    def test_unreadable_pack_does_not_skew_total(self):
        self.pack()
        self.pack("BAT1", energy_full="bad", energy_now="bad")
        self.assertIsNone(snapshot(self.root)["percentage"])

    def test_ac_state_unknown_and_usb_power(self):
        (self.root / "AC/online").unlink()
        self.assertIsNone(snapshot(self.root)["acOnline"])
        self.supply("USB", type="USB_PD", online=1)
        self.assertTrue(snapshot(self.root)["acOnline"])


if __name__ == "__main__":
    unittest.main()
