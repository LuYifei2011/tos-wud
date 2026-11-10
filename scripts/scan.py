#!/usr/bin/env python3
"""Scan the exact packaged image and fail on every HIGH or CRITICAL finding."""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path
from tools import fetch

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('x86_64', 'aarch64'), required=True)
    parser.add_argument('--image', help='Override only for testing a local remediation image.')
    parser.add_argument('--trivy', type=Path)
    args = parser.parse_args()
    compose = ROOT / 'build' / args.platform / 'docker-compose.yml'
    config = json.loads(subprocess.check_output(['docker', 'compose', '-f', str(compose), 'config', '--format', 'json'], text=True))
    image = args.image or config['services']['wud']['image']
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    suffix = args.platform + ('-candidate' if args.image else '')
    output = reports / ('trivy-' + suffix + '.json')
    trivy = args.trivy or fetch('trivy')
    subprocess.run([str(trivy), 'image', '--platform', 'linux/amd64' if args.platform == 'x86_64' else 'linux/arm64', '--cache-dir', str(ROOT / '.cache/trivy/db'), '--scanners', 'vuln', '--format', 'json', '--output', str(output), '--timeout', '10m', image], check=True)
    data = json.loads(output.read_text())
    findings = [v for result in data.get('Results', []) for v in result.get('Vulnerabilities', [])]
    counts = dict(collections.Counter(v['Severity'] for v in findings))
    assessment = {'image': image, 'platform': args.platform, 'report_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'counts': counts, 'passed': not any(v['Severity'] in {'HIGH', 'CRITICAL'} for v in findings)}
    (reports / ('scan-' + suffix + '.json')).write_text(json.dumps(assessment, indent=2) + '\n')
    print(json.dumps(assessment, indent=2))
    if not assessment['passed']:
        raise SystemExit('Release blocked: HIGH/CRITICAL findings in the packaged image. See ' + str(output))


if __name__ == '__main__':
    main()
