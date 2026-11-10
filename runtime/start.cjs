'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function initialize({ store, socket, Database }) {
  process.umask(0o077);
  if (!fs.statSync(socket).isSocket()) {
    throw new Error('Docker socket mount is not a socket: ' + socket);
  }
  try {
    fs.accessSync(socket, fs.constants.R_OK | fs.constants.W_OK);
  } catch (error) {
    throw new Error('Cannot access Docker socket. Rebuild with --docker-gid matching stat -c %g /var/run/docker.sock on the NAS.', { cause: error });
  }

  const secrets = path.join(store, '.tos');
  fs.mkdirSync(secrets, { recursive: true, mode: 0o700 });
  fs.chmodSync(secrets, 0o700);
  function secretFile(name) {
    const filename = path.join(secrets, name);
    try {
      fs.writeFileSync(filename, crypto.randomBytes(32).toString('hex') + '\n', { flag: 'wx', mode: 0o600 });
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
    fs.chmodSync(filename, 0o600);
    const value = fs.readFileSync(filename, 'utf8').trim();
    if (value.length < 32) throw new Error('Invalid or empty secret file: ' + filename);
    return filename;
  }
  process.env.WUD_AUTH_SESSION_SECRET__FILE = secretFile('session-secret');

  let adminExists = false;
  const dbPath = path.join(store, 'wud.sqlite');
  if (fs.existsSync(dbPath)) {
    const db = new Database(dbPath, { readonly: true, fileMustExist: true });
    try {
      const table = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'").get();
      if (table) adminExists = Boolean(db.prepare("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").get());
    } finally {
      db.close();
    }
  }
  if (!adminExists) {
    process.env.WUD_AUTH_ADMIN_USER = 'admin';
    process.env.WUD_AUTH_ADMIN_PASSWORD__FILE = secretFile('initial-admin-password');
    console.info('Initial WUD login: admin. Read the password from ' + process.env.WUD_AUTH_ADMIN_PASSWORD__FILE + ' on the NAS.');
  }
}

module.exports = { initialize };
if (require.main === module) {
  initialize({ store: '/store', socket: '/var/run/docker.sock', Database: require('better-sqlite3') });
  require(process.cwd() + '/dist/index.js');
}
