# WUD 9.8.0 for TOS 7

第三方 TOS 封装，提供 x86_64、aarch64 两个独立安装包。依赖应用中心的 DockerEngine，Web 端口为 13000。

首次启动生成 `admin` 的随机密码，位于容器内 `/store/.tos/initial-admin-password`。用户改密后，同一数据挂载下重启和容器重建保留新密码。包内默认宿主路径为 `/Volume1/DockerAppData/wud/store`；实际安装挂载和应用中心卸载的数据处理仍待 TNAS 验证，操作前按实际路径备份。

下载与你的架构匹配的附件并核验 `SHA256SUMS`。安装方式、socket GID 检查、备份和卸载行为见仓库 README。此应用需要访问宿主 Docker API。

WUD 项目与图标采用 MIT 许可。此仓库负责 TOS 打包与集成支持，WUD 本身的问题请联系上游项目。
