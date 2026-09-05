#!/bin/bash
# Run via pkexec from the project; runtime uses only root-owned installed files.
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")"
[[ $EUID == 0 ]] || { echo 'Run: pkexec ./install-saver.sh'; exit 1; }
# Refuse to remove an administrator-customized legacy policy.
legacy_policy=/usr/share/polkit-1/actions/io.github.ijonas.t480batteries.policy
if [[ -e $legacy_policy || -L $legacy_policy ]]; then
  [[ ! -L $legacy_policy ]] || { echo 'Legacy policy is a symlink; review manually.' >&2; exit 1; }
  cmp -s "$legacy_policy" <(sed 's/io.github.stackingturtles.t480batteries/io.github.ijonas.t480batteries/g' system/io.github.stackingturtles.t480batteries.policy) || {
    echo 'Legacy policy has custom contents; review manually.' >&2; exit 1;
  }
fi
backup=/var/backups/t480batteries/$(date -u +%Y%m%dT%H%M%S)
mkdir -p "$backup"
for target in "$legacy_policy" /usr/local/libexec/t480batteries/charge_limit.py /etc/systemd/system/t480batteries-charge-limit.{service,timer} /usr/share/polkit-1/actions/io.github.stackingturtles.t480batteries.policy; do
  if [[ -e $target ]]; then cp --parents -a "$target" "$backup"; fi
done
install -d -m 755 -o root -g root /usr/local/libexec/t480batteries /var/lib/t480batteries
install -m 755 -o root -g root charge_limit.py /usr/local/libexec/t480batteries/charge_limit.py
install -m 644 -o root -g root system/t480batteries-charge-limit.{service,timer} /etc/systemd/system/
install -m 644 -o root -g root system/io.github.stackingturtles.t480batteries.policy /usr/share/polkit-1/actions/
rm -f -- "$legacy_policy"
systemctl daemon-reload
systemctl enable --now t480batteries-charge-limit.timer
echo "Charge control installed. Backup: $backup. No preset was changed by installation."
