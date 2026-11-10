'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { DatabaseSync } = require('node:sqlite');
const { initialize } = require('../runtime/start.cjs');

class Database extends DatabaseSync {
  constructor(filename) { super(filename, { readOnly: true }); }
}

async function fixture(t) {
  const store = fs.mkdtempSync(path.join(os.tmpdir(), 'wud-test-'));
  const socket = path.join(store, 'docker.sock');
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(socket, resolve); });
  const saved = { ...process.env };
  const oldMask = process.umask();
  t.after(async () => {
    await new Promise(resolve => server.close(resolve));
    fs.rmSync(store, { recursive: true, force: true });
    for (const key of Object.keys(process.env)) if (!(key in saved)) delete process.env[key];
    Object.assign(process.env, saved);
    process.umask(oldMask);
  });
  for (const key of ['WUD_AUTH_ADMIN_USER', 'WUD_AUTH_ADMIN_PASSWORD__FILE', 'WUD_AUTH_SESSION_SECRET__FILE']) delete process.env[key];
  return { store, socket, Database };
}

test('fresh install generates private credentials and a stable session secret', async t => {
  const options = await fixture(t);
  initialize(options);
  const password = process.env.WUD_AUTH_ADMIN_PASSWORD__FILE;
  const session = process.env.WUD_AUTH_SESSION_SECRET__FILE;
  assert.equal(process.env.WUD_AUTH_ADMIN_USER, 'admin');
  assert.match(fs.readFileSync(password, 'utf8').trim(), /^[a-f0-9]{64}$/);
  assert.equal(fs.statSync(password).mode & 0o777, 0o600);
  assert.equal(fs.statSync(path.dirname(password)).mode & 0o777, 0o700);
  const first = fs.readFileSync(session, 'utf8');
  initialize(options);
  assert.equal(fs.readFileSync(session, 'utf8'), first);
});

test('an existing admin is preserved without reseeding its password', async t => {
  const options = await fixture(t);
  const db = new DatabaseSync(path.join(options.store, 'wud.sqlite'));
  db.exec("CREATE TABLE users (role TEXT, password_hash TEXT); INSERT INTO users VALUES ('admin', 'changed-by-user');");
  db.close();
  initialize(options);
  assert.equal(process.env.WUD_AUTH_ADMIN_USER, undefined);
  assert.equal(process.env.WUD_AUTH_ADMIN_PASSWORD__FILE, undefined);
  assert.equal(fs.existsSync(path.join(options.store, '.tos/initial-admin-password')), false);
});

test('a database left before user migration still bootstraps', async t => {
  const options = await fixture(t);
  const db = new DatabaseSync(path.join(options.store, 'wud.sqlite'));
  db.exec('CREATE TABLE app_info (version TEXT)');
  db.close();
  initialize(options);
  assert.equal(process.env.WUD_AUTH_ADMIN_USER, 'admin');
});

test('a corrupt database fails without overwriting it', async t => {
  const options = await fixture(t);
  const file = path.join(options.store, 'wud.sqlite');
  fs.writeFileSync(file, 'corrupt database');
  assert.throws(() => initialize(options));
  assert.equal(fs.readFileSync(file, 'utf8'), 'corrupt database');
});

test('invalid existing secret fails instead of rotating silently', async t => {
  const options = await fixture(t);
  fs.mkdirSync(path.join(options.store, '.tos'));
  fs.writeFileSync(path.join(options.store, '.tos/session-secret'), '');
  assert.throws(() => initialize(options), /Invalid or empty secret/);
});

test('a directory substituted for the Docker socket fails with a useful error', async t => {
  const options = await fixture(t);
  assert.throws(() => initialize({ ...options, socket: options.store }), /not a socket/);
});
