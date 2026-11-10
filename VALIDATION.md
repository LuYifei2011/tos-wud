# 验证记录

日期：2026-11-10（Asia/Shanghai）。目标：TOS 7.0+，应用 ID `wud`，WUD 9.8.0。主机为 macOS ARM64，Docker Engine 29.7.2、Compose 5.5.0。

## 已通过

| 检查 | 证据 |
| --- | --- |
| 官方包检查 | 两架构包均通过 TOSAppSelfTestingTool v1.0.3-beta，输出 `check passed`；工具在 Ubuntu 24.04 容器内执行 |
| 工具供应链 | 官方自检工具、Trivy 0.76.2 和 actionlint 1.7.12 的下载均核对官方 release asset 摘要 |
| 额外包规范 | `scripts/check.py` 验证元数据、四文件包结构、26 个语言区段、LF/UTF-8、图标大小及 viewBox、自包含 SVG、Compose、持久化、权限、端口、镜像摘要、内嵌许可和校验和 |
| SVG | 42,695 字节，小于平台 50,000 字节阈值；viewBox `0 0 1024 1024`；优化前后 512px 渲染已目视比较 |
| 单元测试 | Node 启动逻辑 6/6；Python 商店格式防回归 5/5 |
| 可复现构建 | 连续两次构建的两个应用包摘要各自相同 |
| 官方 ARM64 镜像生命周期 | UID 1000、健康检查、初始账号登录、修改密码、强制重建后新密码有效/旧密码失效、会话密钥保留、认证 API 访问通过 |
| 官方 x86_64 镜像生命周期 | 同上，由 Docker Desktop 在 ARM64 主机模拟运行；GitHub CI 配置使用两个架构的原生 runner |
| 网页 | Playwright Chromium：登录页、使用已修改凭据登录、仪表板、无页面 JS 错误和桌面横向溢出；截图在本地 `reports/screenshots/aarch64/` |
| 工作流静态检查 | actionlint 通过 `.github/workflows/ci.yml` 与 `release.yml` |
| 测试资源 | 所有生命周期测试均在 finally 阶段清理容器、对应网络和临时凭据目录 |

当前应用包 SHA256：

```text
x86_64  085f3d507ea6fa5ada4fbe05cbbf8d5cf73a32686e9025e089d87e16c6755c11
aarch64 7140109f74474727f82f05c2fd52b7247e78c78cfaffb8c151ac6a11e8af5b95
```

## 发布阻塞

### 官方镜像漏洞

包固定的 Docker Hub 官方多架构索引为：

```text
getwud/wud:9.8.0@sha256:5a45a94c2c3e9c26e052c62bbc5bef9f945e3f7826dc446b5c71586a1238ed40
```

Trivy 0.76.2 对两个架构均检出：**HIGH 10、MEDIUM 17、LOW 1、CRITICAL 0**。HIGH 按“依赖实例 × 漏洞”计数，并非 10 个独立 CVE。其中应用中的 undici 8.11.2 有 4 条 HIGH，镜像内 npm 的依赖有另外 6 条 HIGH。

扫描摘要与依赖路径见 [机器可读记录](docs/security-scan-2026-11-10.json)。本地完整报告位于 `reports/trivy-x86_64.json`、`reports/trivy-aarch64.json`，CI 会把完整报告上传到该次 run 的 artifacts。`scripts/scan.py` 已实际运行，并对两个架构返回非零退出码；这是预期的安全拦截结果。

本地诊断候选镜像用固定的 undici 8.12.2 替换对应依赖并移除 npm，复扫结果为 **0 HIGH/CRITICAL，1 MEDIUM**，ARM64 生命周期测试通过。它未推送到公开仓库，安装包仍引用上述官方镜像。上架前需采用已修复、可公开拉取且符合商店来源规则的 Docker Hub 镜像并重验。

### TNAS 实机与账号审核

尚未完成 TNAS 实机安装、应用中心入口、平台对 socket 挂载/所有者的处理、平台启停、保留数据重装和清理数据卸载验证。`docs/release-readiness.json` 两个架构均保留空记录，没有填入推测性通过结果。

还需在开发者平台确认 App ID 可用、发布者身份和 Docker Hub 来源审核条件，并确认发布账号 2FA。当前包保留 `beta: true`。正式 Release workflow 在安全扫描及实机证据均通过前不会创建发布草稿。

未验证所有 WUD 镜像仓库、通知渠道、自动更新触发器或公网反向代理；未提交到商店，也没有商店审核通过结论。
