#!/usr/bin/env python3
"""Link this development checkout into Omarchy, or restore the stock panel."""

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ID = "io.github.ijonas.t480batteries"


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent
    target = Path.home() / ".config/omarchy/plugins" / PLUGIN_ID
    if target.is_symlink():
        if target.resolve() != repo:
            parser.error(f"Refusing to change another checkout: {target}")
    elif target.exists():
        parser.error(f"Refusing to overwrite an existing installation: {target}")
    elif args.uninstall:
        parser.error("This checkout is not installed")

    # Confirm shell availability before changing any configuration.
    subprocess.run(["omarchy", "plugin", "list", "--json"], check=True, stdout=subprocess.DEVNULL)
    run("omarchy", "plugin", "validate", str(repo))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = Path.home() / ".local/state/t480batteries/backups" / stamp
    backup.mkdir(parents=True)
    config = Path.home() / ".config/omarchy/shell.json"
    if config.exists() or config.is_symlink():
        shutil.copy2(config, backup / "shell.json", follow_symlinks=False)
        if config.is_symlink() and config.is_file():
            shutil.copy2(config, backup / "shell.contents.json")
    print(f"Shell backup: {backup}", flush=True)

    if args.uninstall:
        run("omarchy", "plugin", "disable", PLUGIN_ID)
        run("omarchy", "plugin", "enable", "omarchy.power")
        target.unlink()
        run("omarchy-shell", "shell", "rescanPlugins")
        print("Restored Omarchy Power. Keep or remove this project separately.")
        print("If Fleet has a tank override, restore its power widget id too.")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_symlink():
        target.symlink_to(repo, target_is_directory=True)
    run("omarchy-shell", "shell", "rescanPlugins")
    # Discovery is asynchronous; enabling in the same instant can report unknown.
    for _ in range(40):
        result = subprocess.run(["omarchy", "plugin", "list", "--json"],
                                check=True, capture_output=True, text=True)
        if any(plugin["id"] == PLUGIN_ID for plugin in json.loads(result.stdout)):
            break
        time.sleep(0.1)
    else:
        raise SystemExit("Plugin not discovered; shell config was not changed. Check shell logs.")
    run("omarchy", "plugin", "enable", PLUGIN_ID)
    print("Installed T480 Batteries. Click the power icon to open the panel.")


if __name__ == "__main__":
    main()
