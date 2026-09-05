import json
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_public_identity_and_license(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["id"], "io.github.stackingturtles.t480batteries")
        self.assertEqual(manifest["author"], "Stacking Turtles Ltd.")
        self.assertEqual(manifest.get("license"), "MIT")
        policy = ROOT / "system" / (manifest["id"] + ".policy")
        action = ET.parse(policy).getroot().find("action")
        self.assertEqual(action.attrib["id"], manifest["id"] + ".charge-limit")

    def test_legacy_policy_guard_preserves_custom_files(self):
        script = (ROOT / "install-saver.sh").read_text()
        guard = script.split("# Refuse to remove")[1].split("backup=/var/backups/")[0]
        guard = "# Refuse to remove" + guard
        policy = ROOT / "system/io.github.stackingturtles.t480batteries.policy"
        original = policy.read_text().replace(
            "io.github.stackingturtles", "io.github.ijonas"
        )
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "legacy.policy"
            guard = guard.replace(
                "/usr/share/polkit-1/actions/io.github.ijonas.t480batteries.policy",
                str(legacy),
            )
            for contents, success in [(original, True), ("custom policy", False)]:
                legacy.write_text(contents)
                result = subprocess.run(
                    ["bash", "-c", guard], cwd=ROOT, capture_output=True, check=False
                )
                self.assertEqual(result.returncode == 0, success)
                self.assertEqual(legacy.read_text(), contents)
            legacy.unlink()
            legacy.symlink_to(Path(directory) / "missing")
            result = subprocess.run(
                ["bash", "-c", guard], cwd=ROOT, capture_output=True, check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(legacy.is_symlink())
