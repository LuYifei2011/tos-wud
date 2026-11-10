#!/usr/bin/env python3
"""Prepare a Docker build context with integrity-verified dependency archives."""
import base64
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / 'build/image'
    target.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / 'image/dependencies.lock.json').read_text())
    for name, dependency in lock.items():
        archive = target / (name + '-' + dependency['version'] + '.tgz')
        if not archive.exists():
            with urllib.request.urlopen(dependency['url'], timeout=120) as response:
                archive.write_bytes(response.read())
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
        if integrity != dependency['integrity']:
            raise SystemExit('Integrity mismatch: ' + str(archive))
    shutil.copyfile(ROOT / 'image/Dockerfile', target / 'Dockerfile')
    print('Verified build context: ' + str(target))


if __name__ == '__main__':
    main()
