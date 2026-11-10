# Changelog

## 9.8.0 (unreleased)

- Package WUD 9.8.0 for TOS 7 on x86_64 and aarch64.
- Persist the database and credentials, generate an initial administrator password, and preserve password changes across container recreation.
- Pin the official Docker Hub image by digest and validate metadata, SVG limits, language coverage and Compose configuration.
- Check package structure with the official TOS tool and verify container lifecycle behavior on both architectures.
- Gate release preparation on image vulnerability scans and recorded TNAS lifecycle evidence.
