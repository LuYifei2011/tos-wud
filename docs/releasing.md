# 发布流程

本项目为 WUD 的第三方 TOS 封装。商店安装包使用 `packaging/image.lock.json` 中固定摘要的 Docker Hub 镜像。

## 构建和检查

```sh
python3 scripts/build.py
python3 scripts/check.py
node --test tests/start.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/smoke.py --platform x86_64
python3 scripts/smoke.py --platform aarch64
python3 scripts/scan.py --platform x86_64
python3 scripts/scan.py --platform aarch64
```

CI 在两个架构的原生 GitHub runner 上执行测试。第三方 Actions 固定到完整 commit SHA，工具从官方固定 release 下载并校验摘要；PR 检查仅有 `contents: read` 权限。扫描发现 HIGH/CRITICAL 会导致任务失败，报告保存在 workflow artifacts，发布任务不会绕过该结果。

包位于 `dist/x86_64/wud.tar.gz`、`dist/aarch64/wud.tar.gz`。GitHub Release 使用 `dist/release/wud_x86_64.tar.gz`、`wud_aarch64.tar.gz` 和合并的 `SHA256SUMS`，避免两个架构的附件同名。架构仍以内含 `config.ini` 为准。

## TNAS 验证

确认应用 ID `wud` 在商店可用，开发者名称与 `publisher` 一致，并为 GitHub 账号启用 2FA。Docker Hub 镜像来源需符合商店第 9.4 节要求。

在对应架构的 TNAS 上，对准备发布的实际包运行官方工具的 `-c` 和 `-i`，确认以下行为：安装、应用中心打开、启停、Docker 事件接收、登录改密、保留数据卸载再装、删除数据卸载。检查平台未改写 socket 绑定路径、未更改宿主 socket 所有者，并确认实际 socket GID 与包的 `group_add` 一致。GID 不一致时用 `--docker-gid` 重建后重新验证该包。

记录安装后容器 `/store` 的实际宿主挂载路径，核对平台是否将包内的 `/Volume1/DockerAppData/wud/store` 改写到所选卷。使用独立测试数据，记录卸载选项、配置与凭据文件的摘要：保留数据后重装应恢复配置和修改后的密码；删除数据后检查已记录的宿主路径，重装应重新初始化凭据。普通 Deb 测试夹具的清理结果不代替此 Docker 包的验收。

把证据记录到 `docs/release-readiness.json` 的对应架构对象。每项须填入实际验证值；`package_sha256` 必须是该次实机测试的包摘要。例如对象需要这些字段：

```json
{
  "model": "实际设备型号",
  "tos_version": "实际系统版本",
  "tested_at": "实际测试日期",
  "package_sha256": "实际测试包的 SHA256",
  "install": true,
  "start_stop": true,
  "socket_mount_preserved": true,
  "socket_ownership_preserved": true,
  "retained_data_reinstall": true,
  "clean_uninstall": true,
  "web_ui": true
}
```

需要修改 `beta` 时，应在构建和实机测试前设置；随后对相同字节的最终包记录摘要。修改源码、镜像、发布者或 GID 都需要重新构建，并重新验证受影响的结果。

## 创建 GitHub Release

所有检查通过且证据完整后，执行 `python3 scripts/release_gate.py v9.8.0`。然后创建对应标签并推送。

```sh
git tag v9.8.0
git push origin v9.8.0
```

Release workflow 会重新验证并创建 **draft release**。检查架构附件、SHA256 和扫描报告，再手动发布该 Release。无需把 `.tar.gz` 文件提交到源码仓库。

商店从公开 GitHub Releases 拉取包。在 TNAS 开发者平台为 x86_64、aarch64 分别创建/提交应用，选择对应附件；应用 ID、类型和架构要与附件内元数据完全一致。商店的人工审核结论由平台作出。

## 镜像安全更新

优先采用上游已修复的 Docker Hub 版本/摘要，更新 `packaging/image.lock.json` 并重新扫描。不要只因为标签名称相同就认为镜像内容相同。

`image/` 提供一个针对当前扫描结果的可复现修复上下文：固定上游摘要，用经 SHA512 校验的 undici 8.12.2 替换对应模块，并移除运行时不需要的 npm。它用于本地诊断/验证；当前包仍引用上游官方镜像。

```sh
python3 scripts/prepare_image.py
docker build --platform linux/arm64 -t wud-tos-candidate:9.8.0 build/image
python3 scripts/smoke.py --platform aarch64 --image wud-tos-candidate:9.8.0
python3 scripts/scan.py --platform aarch64 --image wud-tos-candidate:9.8.0
```

维护自有公开镜像需要单独确定 Docker Hub 来源和商店认可条件，不能用仅存在于本机的镜像摘要作为商店依赖。
