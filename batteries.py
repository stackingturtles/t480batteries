#!/usr/bin/env python3
"""Read-only T480 power-supply snapshot. No subprocesses, serials or privileges."""

import argparse
import json
import math
from pathlib import Path


def read(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return None


def number(path):
    try:
        value = float(read(path))
        return value if math.isfinite(value) and value >= 0 else None
    except (TypeError, ValueError):
        return None


def energy(path, suffix):
    value = number(path / f"energy_{suffix}")
    if value is not None:
        return value / 1_000_000
    charge = number(path / f"charge_{suffix}")
    voltage = number(path / "voltage_min_design") or number(path / "voltage_now")
    return charge * voltage / 1_000_000_000_000 if charge is not None and voltage else None


def power(path):
    value = number(path / "power_now")
    if value is not None:
        return value / 1_000_000
    # Some drivers use a signed current; direction comes from status, not sign.
    try:
        current = abs(float(read(path / "current_now")))
        voltage = number(path / "voltage_now")
        if math.isfinite(current) and voltage:
            return current * voltage / 1_000_000_000_000
    except (ValueError, TypeError):
        pass
    return None


def battery(root, name, label, ac_online):
    path = root / name
    result = {"id": name, "label": label, "present": False, "state": "absent"}
    if read(path / "type") != "Battery" or number(path / "present") == 0:
        return result
    full = energy(path, "full")
    now = energy(path, "now")
    percentage = number(path / "capacity")
    if percentage is None and full and now is not None:
        percentage = now / full * 100
    if percentage is not None:
        percentage = max(0, min(100, percentage))
    if now is None and full and percentage is not None:
        now = full * percentage / 100
    rate = power(path)
    start = number(path / "charge_control_start_threshold")
    end = number(path / "charge_control_end_threshold")
    start = start if start is not None and 0 <= start <= 100 else None
    end = end if end is not None and 0 < end <= 100 else None
    state = {
        "Charging": "charging", "Discharging": "discharging", "Full": "full",
        "Not charging": "standby", "Unknown": "unknown",
    }.get(read(path / "status"), "unknown")
    # Do not mistake the waiting battery in a two-pack system for charging.
    # A limit is known only when a configured threshold explains idle charging.
    if (ac_online is True and end is not None and end < 100
            and percentage is not None and percentage >= (start if start is not None else end)
            and state in ("standby", "full", "charging") and rate is not None and rate <= 0.2):
        state = "holding"
    seconds = None
    estimated = False
    if state in ("charging", "discharging"):
        suffix = "full" if state == "charging" else "empty"
        seconds = number(path / f"time_to_{suffix}_now")
        if state == "charging" and end is not None and end < 100:
            seconds = None  # Native full-time may ignore a configured charge cap.
        if not seconds:
            seconds = None
            if rate is not None and rate > 0.2 and now is not None:
                remaining = now if state == "discharging" else (max(0, full * (end if end is not None else 100) / 100 - now) if full else None)
                if remaining is not None:
                    seconds = remaining / rate * 3600
                    estimated = True
    result.update(present=True, percentage=percentage, energyWh=now, fullWh=full,
                  designWh=energy(path, "full_design"), rateW=rate,
                  cycles=number(path / "cycle_count"), state=state,
                  thresholdStart=start, thresholdEnd=end, seconds=seconds,
                  estimated=estimated)
    # An external pack can disappear while its individual attributes are read.
    if not path.exists() or number(path / "present") == 0:
        return {"id": name, "label": label, "present": False, "state": "absent"}
    return result


def snapshot(root):
    if not root.is_dir():
        raise OSError("Power-supply directory is unavailable")
    online = [number(path / "online") for path in root.iterdir()
              if read(path / "type") in ("Mains", "USB", "USB_C", "USB_PD")]
    known = [value for value in online if value is not None]
    ac_online = any(known) if known else None
    batteries = [battery(root, "BAT0", "Internal", ac_online),
                 battery(root, "BAT1", "External", ac_online)]
    present = [item for item in batteries if item["present"]]
    # Weight by actual full energy: a 24 Wh pack and a 72 Wh pack are not peers.
    percentage = None
    if present and all(item["fullWh"] and item["energyWh"] is not None for item in present):
        percentage = min(100, max(0, sum(item["energyWh"] for item in present)
                                 / sum(item["fullWh"] for item in present) * 100))
    elif len(present) == 1:
        percentage = present[0]["percentage"]
    if any(item["state"] == "discharging" for item in present):
        state = "discharging"
    elif any(item["state"] == "charging" for item in present):
        state = "charging"
    elif present and all(item["state"] == "full" for item in present):
        state = "full"
    else:
        state = "standby" if present else "absent"
    return {"schemaVersion": 1, "acOnline": ac_online, "batteries": batteries,
            "percentage": percentage, "state": state}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/sys/class/power_supply"),
                        help="Alternative sysfs fixture directory for tests")
    args = parser.parse_args()
    try:
        data = snapshot(args.root)
        data["chargeControlInstalled"] = Path("/usr/local/libexec/t480batteries/charge_limit.py").is_file()
        print(json.dumps(data, allow_nan=False))
    except OSError:
        print(json.dumps({"error": "Battery telemetry unavailable"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
