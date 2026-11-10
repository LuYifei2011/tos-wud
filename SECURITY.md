# Security

Security fixes target the version in `packaging/config.ini`. Each release pins a Docker Hub image digest. HIGH and CRITICAL findings block the release workflow; the project does not suppress those findings.

Report sensitive packaging vulnerabilities through the repository's private vulnerability reporting feature if enabled. If unavailable, contact the maintainer through their [GitHub profile](https://github.com/LuYifei2011) to arrange a private channel. Do not put credentials, logs containing tokens or exploit details in a public issue.

Report vulnerabilities in WUD itself to the [upstream project](https://github.com/getwud/wud/security). A Docker socket grants Docker API access even with a read-only filesystem mount. Run this application only on a trusted host and restrict its HTTP entry to a trusted network or an authenticated HTTPS reverse proxy.

The first administrator password and session secret are generated at runtime. Passwords changed through WUD are preserved across container recreation. Backups of the application store include authentication data and must receive the same protection as the live store.
