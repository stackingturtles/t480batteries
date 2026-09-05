# Migrate the original plugin namespace

The original ID was `io.github.ijonas.t480batteries`. The public ID is
`io.github.stackingturtles.t480batteries`. Legacy references here identify only
what must be migrated; new installs use the public ID.

1. Back up `~/.config/omarchy/shell.json` and any configuration-manager copy.
2. Disable the old plugin. For a development symlink, remove only the symlink;
   retain the source checkout. For a Git installation, use Omarchy plugin removal.
3. Install the new plugin as described in the README (or run `python3 install.py`
   for a development checkout). Replace the old widget ID in any configuration
   manager, so a later apply cannot restore it.
4. Re-run `install-saver.sh` to migrate the Polkit policy. It backs up the old
   policy and replaces it only when its contents match the original project
   policy. Custom policies require manual review. The helper/service paths and
   saved mode stay the same; this is not a charge-limit reset.

If administrator authentication is cancelled, the existing charge-control helper
and old policy continue to work with the new panel because the executable path
has not changed. Complete policy migration before removing legacy policy files.

For recovery, disable the new panel, restore the previous checkout and plugin
link, and restore the saved shell/configuration-manager files. Restore a whole
shell backup only if no subsequent desktop changes need preserving. Privileged
installer backups are under `/var/backups/t480batteries/`.
