#!/usr/bin/env python3
"""Require scan evidence and recorded TNAS review before creating a release."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    metadata = json.loads((ROOT / 'packaging/config.ini').read_text())
    readiness = json.loads((ROOT / 'docs/release-readiness.json').read_text())
    failures = []
    if readiness['version'] != metadata['version']:
        failures.append('TNAS evidence version does not match the package')
    if len(sys.argv) > 1 and sys.argv[1] != 'v' + metadata['version']:
        failures.append('Release tag must equal v' + metadata['version'])
    image = json.loads((ROOT / 'packaging/image.lock.json').read_text())['reference']
    for arch in ('x86_64', 'aarch64'):
        evidence = readiness['tnas'].get(arch)
        package = ROOT / 'dist' / arch / 'wud.tar.gz'
        if not evidence:
            failures.append(arch + ': TNAS installation/lifecycle evidence missing')
        else:
            required = ('model', 'tos_version', 'tested_at', 'package_sha256', 'install', 'start_stop', 'socket_mount_preserved', 'socket_ownership_preserved', 'retained_data_reinstall', 'clean_uninstall', 'web_ui')
            if not all(evidence.get(key) for key in required):
                failures.append(arch + ': incomplete TNAS evidence')
            if not package.exists() or evidence.get('package_sha256') != hashlib.sha256(package.read_bytes()).hexdigest():
                failures.append(arch + ': TNAS evidence does not cover this exact artifact')
        assessment_path = ROOT / 'reports' / ('scan-' + arch + '.json')
        report_path = ROOT / 'reports' / ('trivy-' + arch + '.json')
        if not assessment_path.exists() or not report_path.exists():
            failures.append(arch + ': vulnerability report missing')
        else:
            assessment = json.loads(assessment_path.read_text())
            report = json.loads(report_path.read_text())
            vulnerabilities = [v for result in report.get('Results', []) for v in result.get('Vulnerabilities', [])]
            if assessment.get('image') != image or assessment.get('platform') != arch or assessment.get('report_sha256') != hashlib.sha256(report_path.read_bytes()).hexdigest():
                failures.append(arch + ': image/report identity mismatch')
            if not assessment.get('passed') or any(v['Severity'] in {'HIGH', 'CRITICAL'} for v in vulnerabilities):
                failures.append(arch + ': HIGH/CRITICAL image vulnerabilities')
    for key in ('docker_hub_source_reviewed', 'app_id_availability_confirmed', 'publisher_account_2fa_confirmed'):
        if readiness.get(key) is not True:
            failures.append(key + ': not confirmed')
    if failures:
        raise SystemExit('Release blocked:\n' + '\n'.join('- ' + failure for failure in failures))
    print('PASS: release evidence covers both exact artifacts')


if __name__ == '__main__':
    main()
