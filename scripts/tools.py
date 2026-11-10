#!/usr/bin/env python3
"""Fetch pinned vendor tools and verify their release digests before execution."""
import argparse
import hashlib
import io
import platform
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIVY = {
    ('Darwin', 'arm64'): ('macOS-ARM64', 'ae7ea358326960406b703c77b2ac490190797d80b306b5b50c2a27221da0a5b8'),
    ('Linux', 'arm64'): ('Linux-ARM64', 'ab9d51f86e6a5fb936f605faff6b593ac51bc378fff4d3e8b9d58358b9c367c3'),
    ('Linux', 'amd64'): ('Linux-64bit', 'bc0fc726e017b8927a62b2d3531d7a84ee01769daf5c99ed866dced54089fdbf'),
}
SELFTEST = {
    'arm64': 'da370ac825d04fa5bedc009065d94b077b35db9fa27dd42ae736a14686e2caa9',
    'amd64': '7d4fdc3ad5515322d1b947f344c293d66df6063a6047b1dbd57d5bdecad11234',
}


def fetch(name):
    machine = platform.machine().lower()
    arch = {'aarch64': 'arm64', 'arm64': 'arm64', 'x86_64': 'amd64', 'amd64': 'amd64'}.get(machine)
    if not arch:
        raise SystemExit('Unsupported tool architecture: ' + machine)
    if name == 'trivy':
        suffix, digest = TRIVY[(platform.system(), arch)]
        url = 'https://github.com/aquasecurity/trivy/releases/download/v0.76.2/trivy_0.76.2_' + suffix + '.tar.gz'
        filename = 'trivy-0.76.2-' + suffix
    else:
        if platform.system() != 'Linux':
            raise SystemExit('The official TOS self-test tool requires Linux; use an Ubuntu container.')
        digest = SELFTEST[arch]
        filename = 'TOSAppSelfTestingTool_' + arch
        url = 'https://github.com/terramaster-tos/tos-app-pkg-tools/releases/download/v1.0.3-beta/' + filename
    directory = ROOT / '.cache/tools'
    directory.mkdir(parents=True, exist_ok=True)
    downloaded = directory / (filename + '.download')
    if not downloaded.exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            downloaded.write_bytes(response.read())
    data = downloaded.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit('Release integrity mismatch: ' + str(downloaded))
    executable = directory / filename
    if name == 'trivy':
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            data = archive.extractfile('trivy').read()
    executable.write_bytes(data)
    executable.chmod(0o755)
    return executable


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool', choices=('trivy', 'selftest'))
    print(fetch(parser.parse_args().tool))
