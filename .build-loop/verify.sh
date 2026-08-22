#!/usr/bin/env bash
set -u
echo "=== Final verification ==="
echo "1. Symlink + branch + version:"
echo "   readlink: $(readlink plugins/build-loop)"
echo "   branch:   $(git -C plugins/build-loop branch --show-current)"
echo "   version:  $(python3 -c 'import json,pathlib; print(json.loads(pathlib.Path("plugins/build-loop/.claude-plugin/plugin.json").read_text())["version"])')"
echo
echo "2. Three surfaces:"
python3 - <<'PY'
import json, pathlib, re
print("   .claude-plugin/marketplace.json:", [p for p in json.loads(pathlib.Path('.claude-plugin/marketplace.json').read_text())['plugins'] if p['name']=='build-loop'][0].get('version'))
print("   .agents/plugins/marketplace.json:", [p for p in json.loads(pathlib.Path('.agents/plugins/marketplace.json').read_text())['plugins'] if p['name']=='build-loop'][0].get('version'))
m=re.search(r'\[build-loop\]\([^)]+\)\s*\|\s*`([^`]+)`', pathlib.Path('README.md').read_text())
print("   README.md row:", m.group(1) if m else 'NOT FOUND')
PY
echo
echo "3. launchd plist:"
ls ~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist
launchctl list | grep ai.rosslabs.marketplace-sync
echo
echo "4. Tests:"
python3 tests/test_marketplace_sync.py 2>&1 | tail -2
echo
echo "5. Mirror hygiene:"
python3 - <<'PY'
import importlib.util, pathlib
sp = importlib.util.spec_from_file_location('ms', 'scripts/marketplace-sync.py')
ms = importlib.util.module_from_spec(sp); sp.loader.exec_module(ms)
recs = ms.scan_mirror_branches(pathlib.Path('plugins'))
off = ms.find_off_main_mirrors(recs)
print(f'   {len(recs)} mirrors scanned, {len(off)} off-main')
PY
