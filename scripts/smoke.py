#!/usr/bin/env python3
"""Run an isolated Docker lifecycle test; requires a running local Docker daemon."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, capture=False):
    return subprocess.check_output(args, text=True) if capture else subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('aarch64', 'x86_64'), default='aarch64')
    parser.add_argument('--image', help='Override for local image remediation tests.')
    parser.add_argument('--ui', action='store_true', help='Run Playwright login checks and save screenshots.')
    args = parser.parse_args()
    source = ROOT / 'build' / args.platform / 'docker-compose.yml'
    config = json.loads(run('docker', 'compose', '-f', str(source), 'config', '--format', 'json', capture=True))
    work = Path(tempfile.mkdtemp(prefix='smoke-', dir=ROOT / 'build'))
    project = 'wud-test-' + work.name
    container = project
    compose = work / 'compose.json'
    service = config['services']['wud']
    if args.image:
        service['image'] = args.image
    service['container_name'] = container
    service['platform'] = 'linux/arm64' if args.platform == 'aarch64' else 'linux/amd64'
    service.pop('ports', None)
    if args.ui:
        service['ports'] = [{'target': 3000, 'published': '0', 'host_ip': '127.0.0.1', 'protocol': 'tcp'}]
    if os.uname().sysname == 'Linux':
        service['group_add'] = [str(os.stat('/var/run/docker.sock').st_gid)]
    service['volumes'][0]['source'] = str(work / 'store')
    (work / 'store').mkdir()
    config['name'] = project
    config['networks'] = {'default': {'name': project + '-default'}}
    config.pop('x-app-meta', None)
    compose.write_text(json.dumps(config))
    command = ('docker', 'compose', '-p', project, '-f', str(compose))

    def ownership(uid, gid):
        # Match the ownership setup performed by the TOS installer on Linux.
        if os.uname().sysname == 'Linux':
            run('docker', 'run', '--rm', '--platform', service['platform'], '--user', '0:0', '--entrypoint', 'chown', '-v', str(work / 'store') + ':/data', service['image'], '-R', str(uid) + ':' + str(gid), '/data')

    def wait_ready():
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            status = run('docker', 'inspect', container, '--format', '{{.State.Health.Status}}', capture=True).strip()
            if status == 'healthy':
                return
            time.sleep(1)
        raise RuntimeError('WUD did not become healthy')

    probe = r'''
const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const base = 'http://127.0.0.1:3000';
const auth = password => ({Authorization: 'Basic ' + Buffer.from('admin:' + password).toString('base64')});
(async () => {
  assert.equal(process.getuid(), 1000);
  const mode = process.argv[1];
  const original = fs.readFileSync('/store/.tos/initial-admin-password', 'utf8').trim();
  assert.equal((await fetch(base + '/api/containers')).status, 401);
  if (mode === 'before') {
    const headers = auth(original);
    assert.equal((await fetch(base + '/auth/login', {method:'POST', headers})).status, 200);
    const users = await (await fetch(base + '/api/users', {headers})).json();
    const admin = users.find(user => user.username === 'admin');
    assert.ok(admin);
    const password = crypto.randomBytes(32).toString('hex');
    const response = await fetch(base + '/api/users/' + admin.id, {method:'PUT', headers:{...headers, 'Content-Type':'application/json'}, body:JSON.stringify({password})});
    assert.equal(response.status, 200);
    fs.writeFileSync('/store/.smoke-password', password, {mode:0o600});
    fs.writeFileSync('/store/.smoke-session', fs.readFileSync('/store/.tos/session-secret'), {mode:0o600});
  } else {
    const headers = auth(fs.readFileSync('/store/.smoke-password', 'utf8'));
    assert.equal((await fetch(base + '/auth/login', {method:'POST', headers})).status, 200);
    assert.equal((await fetch(base + '/auth/login', {method:'POST', headers:auth(original)})).status, 401);
    assert.equal((await fetch(base + '/api/containers', {headers})).status, 200);
    assert.equal(fs.readFileSync('/store/.tos/session-secret', 'utf8'), fs.readFileSync('/store/.smoke-session', 'utf8'));
  }
  console.log('PASS ' + mode + ': non-root, authentication, credentials and persistence');
})().catch(error => { console.error(error.message); process.exit(1); });
'''
    try:
        ownership(1000, 1000)
        run(*command, 'up', '-d')
        wait_ready()
        run('docker', 'exec', container, 'node', '-e', probe, 'before')
        if args.ui:
            port = run(*command, 'port', 'wud', '3000', capture=True).strip().rsplit(':', 1)[1]
            password = run('docker', 'exec', container, 'cat', '/store/.smoke-password', capture=True)
            subprocess.run(['node', str(ROOT / 'tests/browser.cjs'), 'http://127.0.0.1:' + port, args.platform], input=password, text=True, check=True)
        run(*command, 'up', '-d', '--force-recreate')
        wait_ready()
        run('docker', 'exec', container, 'node', '-e', probe, 'after')
        print('PASS: ' + args.platform + ' container lifecycle')
    except Exception:
        run('docker', 'logs', '--tail', '25', container)
        raise
    finally:
        run(*command, 'down', '--remove-orphans')
        ownership(os.getuid(), os.getgid())
        shutil.rmtree(work)


if __name__ == '__main__':
    main()
