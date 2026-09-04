#!/bin/bash
# Run via pkexec from the project; runtime uses only root-owned installed files.
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")"
[[ $EUID == 0 ]] || { echo 'Run: pkexec ./install-saver.sh'; exit 1; }
backup=/var/backups/t480batteries/$(date -u +%Y%m%dT%H%M%S)
mkdir -p "$backup"
for target in /usr/local/libexec/t480batteries/charge_limit.py /etc/systemd/system/t480batteries-charge-limit.{service,timer} /usr/share/polkit-1/actions/io.github.ijonas.t480batteries.policy; do
  if [[ -e $target ]]; then cp --parents -a "$target" "$backup"; fi
done
install -d -m 755 -o root -g root /usr/local/libexec/t480batteries /var/lib/t480batteries
install -m 755 -o root -g root charge_limit.py /usr/local/libexec/t480batteries/charge_limit.py
install -m 644 -o root -g root system/t480batteries-charge-limit.{service,timer} /etc/systemd/system/
install -m 644 -o root -g root system/io.github.ijonas.t480batteries.policy /usr/share/polkit-1/actions/
systemctl daemon-reload
systemctl enable --now t480batteries-charge-limit.timer
echo "Charge control installed. Backup: $backup. No preset was changed by installation."
