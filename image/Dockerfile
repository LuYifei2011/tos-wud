# The base is the upstream project image, pinned to its multi-architecture index.
FROM getwud/wud:9.8.0@sha256:5a45a94c2c3e9c26e052c62bbc5bef9f945e3f7826dc446b5c71586a1238ed40
USER 0:0
COPY undici-8.12.2.tgz /tmp/undici.tgz
RUN rm -rf /home/node/app/node_modules/undici \
    && mkdir /home/node/app/node_modules/undici \
    && tar -xzf /tmp/undici.tgz -C /home/node/app/node_modules/undici --strip-components=1 \
    && rm /tmp/undici.tgz \
    && rm -rf /usr/local/lib/node_modules/npm /root/.npm \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx
LABEL org.opencontainers.image.title="WUD for TOS" \
      org.opencontainers.image.source="https://github.com/LuYifei2011/tos-wud" \
      org.opencontainers.image.version="9.8.0" \
      org.opencontainers.image.licenses="MIT"
USER 1000:1000
