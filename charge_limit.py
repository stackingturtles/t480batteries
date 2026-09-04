#!/usr/bin/python3 -I
"""Root-owned fixed-purpose charge control; CLI accepts presets only."""
import fcntl
import json
import os
import sys
from pathlib import Path

ROOT = Path('/sys/class/power_supply')
STATE = Path('/var/lib/t480batteries/mode.json')
PRESETS = {'enable': (75, 80), 'disable': (0, 100)}


def thresholds(pack):
    values = tuple(int((pack / ('charge_control_' + kind + '_threshold')).read_text())
                   for kind in ('start', 'end'))
    if not 0 <= values[0] < values[1] <= 100:
        raise ValueError('Invalid thresholds for ' + pack.name)
    return values


def write_thresholds(pack, values):
    if thresholds(pack) == values:
        return
    # Lower start first so intermediate combinations are valid on the driver.
    for kind, value in [('start', 0), ('end', values[1]), ('start', values[0])]:
        (pack / ('charge_control_' + kind + '_threshold')).write_text(str(value) + '\n')
    if thresholds(pack) != values:
        raise OSError('Threshold readback failed for ' + pack.name)


def apply(mode, root=ROOT, state=STATE, persist=True):
    target = PRESETS[mode]
    packs = [root / name for name in ('BAT0', 'BAT1')
             if (root / name / 'present').exists()
             and (root / name / 'present').read_text().strip() == '1']
    # Validate every present pack before touching any of them.
    previous = [(pack, thresholds(pack)) for pack in packs]
    changed = []
    try:
        for pack, values in previous:
            changed.append((pack, values))
            write_thresholds(pack, target)
        if persist:
            temporary = state.with_suffix('.tmp')
            with temporary.open('w') as handle:
                json.dump({'mode': mode}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o644)
            temporary.replace(state)
    except (OSError, ValueError) as error:
        failed = []
        for pack, values in reversed(changed):
            try:
                write_thresholds(pack, values)
            except (OSError, ValueError):
                failed.append(pack.name)
        if failed:
            raise OSError('Could not restore ' + ', '.join(failed) + '; inspect hardware thresholds') from error
        raise
    return {pack.name: list(thresholds(pack)) for pack in packs}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in (*PRESETS, 'restore'):
        raise ValueError('Usage: charge_limit.py enable|disable|restore')
    if os.geteuid() != 0:
        raise PermissionError('Administrator authentication required')
    STATE.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    with (STATE.parent / 'control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mode = sys.argv[1]
        if mode == 'restore':
            if not STATE.exists():
                return
            mode = json.loads(STATE.read_text())['mode']
            if mode not in PRESETS:
                raise ValueError('Invalid saved charge mode')
        result = apply(mode, persist=sys.argv[1] != 'restore')
        if sys.argv[1] != 'restore':
            print(json.dumps({'mode': mode, 'thresholds': result}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
