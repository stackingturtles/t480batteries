# T480 Batteries

This is an Omarchy user plugin, not a Codex plugin. Read the Omarchy skill for
desktop work. Never edit `/usr/share/omarchy/`.

- Plugin id: `io.github.ijonas.t480batteries`; `clonedFrom: omarchy.power`
  preserves the stock panel IPC. Keep `omarchy.battery` enabled for warnings.
- BAT0 is internal and BAT1 external on this T480. Do not mix their cycles,
  thresholds, current or time estimates. Combined charge must be energy weighted.
- `batteries.py` is a read-only standard-library sysfs collector. No root,
  subprocesses, network, serial numbers, battery writes or persisted telemetry.
- `BatteryCard.qml` is shared by both packs. `Panel.qml` owns refresh, bar,
  popup and profile selection; `Model.js` contains pure display/profile helpers.
- Missing/unknown values must remain distinct from valid zero readings. A
  standby pack is not discharging merely because the laptop is on battery.
- Run the Python and Node tests in README after logic changes, validate the
  manifest, and inspect the running popup and shell logs after QML changes.
- Installer backs up shell config and symlinks the project for development.
  Do not publish, push, or alter charge settings without user authorization.

- User authorized lifespan saver implementation and live threshold verification.
  Only `charge_limit.py` writes charge thresholds, via an installed root-owned
  isolated copy and Polkit. Never run user-editable collector/QML code as root.
- Saver presets: enable 75/80, disable 0/100, both present packs; preserve rollback,
  readback, locking and atomic state persistence. Timer restores every 30 seconds
  for boot/resume/insertion. No TPM, firmware or forced-discharge changes.
- Reinstall helper/system files with `pkexec ./install-saver.sh` after edits;
  document existing state and restore it after live tests unless user requests otherwise.
