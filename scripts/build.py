#!/usr/bin/env python3
"""Build TOS Docker packages using only the Python standard library."""
import argparse
import configparser
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ('config.ini', 'wud.lang', 'wud.svg', 'docker-compose.yml')


def build(platform, publisher, docker_gid, image):
    metadata = json.loads((ROOT / 'packaging/config.ini').read_text())
    metadata.update(platform=platform, publisher=publisher)
    template = (ROOT / 'packaging/docker-compose.yml.in').read_text()
    startup = '/*\n' + (ROOT / 'LICENSE').read_text() + '\n*/\n' + (ROOT / 'runtime/start.cjs').read_text()
    # node -e has no main module, so invoke the exported initializer explicitly.
    startup += "\ninitialize({ store: '/store', socket: '/var/run/docker.sock', Database: require('better-sqlite3') });\nrequire(process.cwd() + '/dist/index.js');\n"
    startup = '\n'.join('        ' + line.replace('$', '$$') for line in startup.splitlines())
    compose = template.replace('@@BOOTSTRAP@@', startup).replace('@@DOCKER_GID@@', docker_gid).replace('@@IMAGE@@', image)
    assert '@@' not in compose
    languages = configparser.ConfigParser(interpolation=None)
    languages.read(ROOT / 'packaging/wud.lang')
    assert len(languages.sections()) == 26
    for section in languages.values():
        if section.name == 'DEFAULT':
            continue
        assert all(section.get(key, '').strip('" ') for key in ('name', 'auth', 'descript'))
    contents = {
        'config.ini': (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode(),
        'docker-compose.yml': compose.encode(),
        'wud.lang': (ROOT / 'packaging/wud.lang').read_bytes(),
        'wud.svg': (ROOT / 'packaging/wud.svg').read_bytes(),
    }
    stage = ROOT / 'build' / platform
    stage.mkdir(parents=True, exist_ok=True)
    output = ROOT / 'dist' / platform / 'wud.tar.gz'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name in FILES:
                    data = contents[name]
                    assert b'\r' not in data
                    (stage / name).write_bytes(data)
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(data))
    with tarfile.open(output) as archive:
        assert archive.getnames() == list(FILES)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    (output.parent / 'SHA256SUMS').write_text(checksum + '  wud.tar.gz\n')
    release = ROOT / 'dist/release'
    release.mkdir(exist_ok=True)
    (release / ('wud_' + platform + '.tar.gz')).write_bytes(output.read_bytes())
    (release / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
        for p in sorted(release.glob('wud_*.tar.gz'))
    ))
    print(str(output.relative_to(ROOT)) + '  sha256:' + checksum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('all', 'x86_64', 'aarch64'), default='all')
    parser.add_argument('--publisher', default=json.loads((ROOT / 'packaging/config.ini').read_text())['publisher'])
    parser.add_argument('--docker-gid', default='0', help='Numeric Docker socket group ID on the target NAS (default: 0).')
    parser.add_argument('--image-ref', default=json.loads((ROOT / 'packaging/image.lock.json').read_text())['reference'], help='Docker Hub image pinned by digest.')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9]+', args.docker_gid):
        parser.error('--docker-gid must be a non-negative integer')
    if not args.publisher.strip():
        parser.error('--publisher cannot be empty')
    if not re.fullmatch(r'(?:docker\.io/)?[a-z0-9_-]+/[a-z0-9._-]+:[a-zA-Z0-9._-]+@sha256:[a-f0-9]{64}', args.image_ref):
        parser.error('--image-ref must be a Docker Hub image with a tag and SHA256 digest')
    for platform in ('x86_64', 'aarch64') if args.platform == 'all' else (args.platform,):
        build(platform, args.publisher, args.docker_gid, args.image_ref)


if __name__ == '__main__':
    main()
