# Axon 10s Pro ArmadaOS · 开发预览镜像

版本：v0.1.0-dev.20261016。仅针对 ZTE A2020 SP / P865A02（SM8250）。

**版本提示：设备现已升级并验收 #44 USB HUB 修复，但本 Release 下载内容仍为 #43 和原专用 REC。#44 镜像尚未公开，不能从本页的 #43 下载获得 USB HUB 修复。**

## 下载内容

| 文件 | 用途 | 验收范围 |
| --- | --- | --- |
| axon10s-pro-armada-boot43-c673d20f.img | Android boot v2 容器中的 #43 Linux 内核与 initramfs | 原开发设备 boot_a 安装、回读、普通重启、Steam 游戏模式及触摸已确认 |
| axon10s-pro-armada-recovery-10078aa9.img | 专用 RAM Recovery | 原开发设备安装、USB root、按键菜单、返回 Armada 已确认；关机及长时间运行未完整验收 |
| boot43.config / recovery.config | 两份构建的完整内核配置 | 用于研究、对照和重建 |
| axon10s-port-source-20261016.tar.gz | 板级适配、驱动、补丁、构建入口及相关脚本的开发快照 | 包含从两份镜像提取的精确启动脚本；不是已验收的全自动重建工程 |
| linux-7.2.6.tar.xz | Linux 基线源码 | 版本及哈希与原开发基线一致 |
| ubuntu-runtime-sources.tar.gz | BusyBox、glibc、e2fsprogs、util-linux 对应 Ubuntu 来源包和版权文件 | 包含发行版补丁与 .dsc 校验信息 |
| image-manifest.json / SHA256SUMS | 镜像身份和完整性清单 | 下载后核对；哈希相同不代表适合另一台设备 |

## 这些镜像不包含什么

**本次没有完整 ArmadaOS rootfs、Steam 客户端/游戏或一键安装器。** boot 镜像不能独立引导到桌面，需要已适配的 ArmadaOS 根文件系统和用户空间配置。KWin 6.7.5、SDDM/Decky 服务配置等修复位于开发设备的 rootfs，不会仅凭刷入 boot 镜像自动获得。

没有上传用户磁盘、账号、Wi-Fi 连接凭据、代理订阅、密钥、persist 校准分区、GPT 备份或原厂 boot_b/recovery_b。

镜像保留本机原厂引导容器需要的 ramdisk、硬件 DTB，以及 REC 的 recovery DTBO；initramfs 中含驱动所需的通用/原厂固件。这些是硬件与引导组件，版权和许可属于各自权利人，不因本项目发布而改用 Linux 许可证。

## 布局与运行条件

- 必须先自行确认机型、原厂版本、解锁和恢复路径。仅有 9008/QPST 接口，不代表具备完整可用的恢复输入。
- #43 只在 `/dev/sda15` 上寻找标签为 `AXON_ARMADA`、带本机板级标记的 ext4 根文件系统。
- initramfs 允许的两种历史几何为：起点 26464576 个 512 字节扇区 / 长度 111968858112 字节，或起点 1304576 个 512 字节扇区 / 长度 124850778112 字节。后者是当前开发设备的合并布局。
- **这些数字是运行前置检查的说明，不是给其他设备照抄的分区方案。** 本 Release 不提供 GPT 写入脚本。不要改别人的分区表来绕过检查。
- REC 默认将内部存储设为只读，不自动挂载根文件系统；其 `recctl status/check` 还要求当前合并布局及 slot-guard。原厂分区布局下检查可能拒绝执行，不能声称是通用 Recovery。
- 通过物理 USB 提供无登录验证的 root 调试入口，属于开发维护版本。尚未完成面向日常分发的访问控制加固。
- 源码快照保留历史脚本；其默认输入目录需要自行准备。修改任何镜像后必须重新校验和验证，不能继承本 Release 的验收结论。

## 本 Release（#43）的限制

保留模拟休眠。原生休眠电源键唤醒不可靠；USB HUB/OTG、外接显示器、开机白条、部分游戏兼容/性能、完整充电与音频通路仍未全部解决。#43 基础开机验收通过，长期稳定性尚未完成。

本次只重新校验和发布本地已验收文件，没有对手机执行新的刷写、重启或休眠测试。公开镜像与已验收镜像字节一致。

## 校验

Linux：`sha256sum -c SHA256SUMS`

macOS：`shasum -a 256 -c SHA256SUMS`

在放齐所有 Release 文件的目录中执行以上命令。完整支持矩阵、经验和更新记录见仓库文档。

[前往 GitHub Release 下载](https://github.com/zry116131/axon10s-pro-armadaos/releases/tag/v0.1.0-dev.20261016)
