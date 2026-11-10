#!/usr/bin/env python3
"""Validate TOS package rules, including requirements the official checker omits."""
import argparse
import configparser
import hashlib
import json
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = 'zh-cn zh-hk en-us ko-kr ja-jp de-de fr-fr it-it es-es hu-hu pl-pl tr-tr ru-ru pt-pt cs-cz da-dk nl-nl nb-no sv-se el-gr ro-ro th-th vi-vn id-id ar-sa he-il'.split()
RESERVED_PORTS = {22, 80, 443, 445, 3306, 5050, 5432, 6379, 8181, 8443}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_icon(data):
    require(len(data) <= 50_000, 'SVG exceeds the platform 50 KB limit')
    require(b'<!DOCTYPE' not in data.upper(), 'SVG must not contain a DTD')
    svg = ET.fromstring(data)
    require(svg.tag == '{http://www.w3.org/2000/svg}svg', 'Invalid SVG root')
    values = [float(v) for v in svg.attrib.get('viewBox', '').replace(',', ' ').split()]
    require(len(values) == 4 and values[2] > 0 and values[3] > 0, 'SVG needs a valid viewBox')
    for element in svg.iter():
        require(element.tag.rsplit('}', 1)[-1] not in {'script', 'foreignObject'}, 'Active SVG content prohibited')
        for name, value in element.attrib.items():
            require(not name.startswith('on'), 'SVG event handlers prohibited')
            if name.rsplit('}', 1)[-1] == 'href':
                require(value.startswith('#'), 'SVG must be self-contained')


def validate_languages(data):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(data.decode('utf-8'))
    require(set(LANGUAGES) <= set(parser.sections()), 'Missing TOS language sections')
    for language in parser.sections():
        for key in ('name', 'auth', 'descript'):
            require(bool(parser[language].get(key, '').strip('" ')), language + ': missing ' + key)


def validate_package(platform):
    package = ROOT / 'dist' / platform / 'wud.tar.gz'
    expected = {'config.ini', 'wud.lang', 'wud.svg', 'docker-compose.yml'}
    with tarfile.open(package) as archive:
        require(len(archive.getmembers()) == 4 and set(archive.getnames()) == expected, 'Package must contain exactly four files')
        require(all(m.isfile() and m.mode == 0o644 for m in archive.getmembers()), 'Archive entry type or permissions invalid')
        files = {name: archive.extractfile(name).read() for name in expected}
    for name, data in files.items():
        require(b'\r' not in data and not data.startswith(b'\xef\xbb\xbf'), name + ': require LF/UTF-8 without BOM')
        require(data == (ROOT / 'build' / platform / name).read_bytes(), 'Staging/archive mismatch: ' + name)
    metadata = json.loads(files['config.ini'])
    for key in ('id', 'icon', 'publisher', 'version', 'help', 'category', 'platform', 'application_type', 'user', 'compose_project'):
        require(bool(metadata.get(key)), 'Missing metadata: ' + key)
    require(metadata['id'] == 'wud' and not metadata['id'].startswith('tos'), 'Invalid App ID')
    require(metadata['platform'] == platform and metadata['application_type'] == 'docker', 'Package identity mismatch')
    require(metadata['open_path'] is True and metadata['exec'] is True, 'Docker UI must open externally')
    require(metadata['recommend'] is False and type(metadata['beta']) is bool, 'Invalid publication flags')
    require(metadata['user'] != 'root' and metadata['user'] != '0', 'Root platform user prohibited')
    require('DockerEngine' in metadata.get('depend', []), 'DockerEngine dependency missing')
    require(re.fullmatch(r'\d+(?:\.\d+){0,2}', metadata['version']), 'Invalid numeric package version')
    require(metadata['icon'] == '/images/icons/wud.svg', 'Icon metadata path mismatch')
    validate_icon(files['wud.svg'])
    validate_languages(files['wud.lang'])
    stage_compose = ROOT / 'build' / platform / 'docker-compose.yml'
    config = json.loads(subprocess.check_output(['docker', 'compose', '-f', str(stage_compose), 'config', '--format', 'json'], text=True))
    require(set(config['services']) == {'wud'}, 'Unexpected service')
    service = config['services']['wud']
    require(re.fullmatch(r'(?:docker\.io/)?[a-z0-9_-]+/[a-z0-9._-]+:[\w.-]+@sha256:[a-f0-9]{64}', service['image']), 'Image must be pinned to a Docker Hub digest')
    require(service['user'] == '1000:1000', 'Container must run as UID/GID 1000')
    require(not service.get('privileged') and service.get('network_mode') != 'host', 'Unsafe container isolation')
    require('ALL' in service.get('cap_drop', []) and service.get('healthcheck', {}).get('test'), 'Missing hardening/healthcheck')
    require(service['restart'] == 'unless-stopped', 'Restart policy mismatch')
    ports = service['ports']
    require(len(ports) == 1 and int(ports[0]['published']) == 13000 and ports[0]['target'] == 3000, 'Port mapping mismatch')
    require(int(ports[0]['published']) not in RESERVED_PORTS, 'Reserved host port')
    require(config['x-app-meta']['web'] == {'port': 13000, 'protocol': 'http'}, 'App Center web metadata mismatch')
    require(metadata['path'] == 'http://${ip}:13000', 'Web entry mismatch')
    mounts = {v['target']: v for v in service['volumes']}
    require(mounts['/store']['source'] == '/Volume1/DockerAppData/wud/store', 'Storage persistence mismatch')
    require(mounts['/var/run/docker.sock']['source'] == '/var/run/docker.sock' and mounts['/var/run/docker.sock']['read_only'], 'Socket mount mismatch')
    require(not any(k.startswith('WUD_AUTH_ADMIN') for k in service['environment']), 'Bootstrap credentials must be generated at runtime')
    require('Copyright (c) 2026 Lu Yifei' in service['command'][2], 'Bundled code license missing')
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    require((package.parent / 'SHA256SUMS').read_text() == digest + '  wud.tar.gz\n', 'Checksum mismatch')
    release = ROOT / 'dist/release' / ('wud_' + platform + '.tar.gz')
    require(release.read_bytes() == package.read_bytes(), 'Release asset mismatch')
    print('PASS: ' + platform + ' metadata, languages, icon, Compose, archive and checksums')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('all', 'x86_64', 'aarch64'), default='all')
    args = parser.parse_args()
    for platform in ('x86_64', 'aarch64') if args.platform == 'all' else (args.platform,):
        validate_package(platform)


if __name__ == '__main__':
    main()
