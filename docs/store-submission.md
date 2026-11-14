# 商店提交信息

| 字段 | 当前值 |
| --- | --- |
| Application ID | `wud`，提交前确认唯一性 |
| Package type | Docker |
| Repository | `https://github.com/LuYifei2011/tos-wud` |
| Architectures | x86_64、aarch64，分别提交对应 Release 附件 |
| Publisher | Lu Yifei，需与开发者账号展示名称一致 |
| Version | 9.8.0 |
| Minimum TOS | 7.0 |
| Dependency | DockerEngine |
| Web entry | `http://${ip}:13000` |
| Permissions | README 权限表；需要宿主 Docker API；Shared Folder: None |
| Initial login | admin；密码在首次启动时随机生成，位置见 README |
| Data retention | 包内默认 `/Volume1/DockerAppData/wud/store:/store`；实际挂载、保留数据重装及删除数据卸载待 TNAS 实机确认 |
| License | 封装与上游 WUD 均为 MIT；许可已随相应代码和图标包含在包中 |

提交资料应同时包含完整公开源码、安装说明、Release 包附件和校验和、镜像扫描结果、TNAS 实机测试记录。开发者平台会自行计算包摘要；本项目的 SHA256 附件供用户校验。

网页截图可通过 `npm ci`、`npx playwright install chromium`、`python3 scripts/smoke.py --platform aarch64 --ui` 生成到 `reports/screenshots/`，截图来自隔离测试实例。提交前使用经过实机确认的画面，并确认不包含密码、令牌或个人数据。

当前准备情况和发布阻塞见 [VALIDATION.md](../VALIDATION.md)。包格式检查通过不代表已通过商店安全与实机审核。
