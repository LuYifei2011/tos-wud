# Contributing

Maintainer commits use the configured 1Password SSH signing key (`git commit -S`). Confirm GitHub marks each maintainer commit as **Verified** before releasing.

Build tooling requires Python 3.12+, Node.js 24 and Docker Compose. Packaging uses the Python standard library. Run:

```sh
python3 scripts/build.py
python3 scripts/check.py
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/start.test.cjs
python3 scripts/smoke.py --platform aarch64
python3 scripts/smoke.py --platform x86_64
python3 scripts/scan.py --platform aarch64
python3 scripts/scan.py --platform x86_64
```

Use the platform that matches your Docker host; emulation is useful locally, and CI tests both architectures on native runners. The scanner and official TOS checker are downloaded from pinned official releases with verified digests by `scripts/tools.py`.

Update `packaging/image.lock.json` when changing the runtime image. Record the upstream version, digest and vulnerability scan together. Keep container runtime users non-root, business data under `/store`, every language field non-empty and the SVG under 50,000 bytes with a valid viewBox. Preserve copyright and license notices.

Never commit `.cache`, generated packages, local reports, passwords, tokens, SSH configuration or NAS connection details. Distribute packages through GitHub Release assets. See [release preparation](docs/releasing.md) for the human review requirements.
