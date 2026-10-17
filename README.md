# ZTE Axon 10s Pro · ArmadaOS 适配进度

中兴天机 Axon 10s Pro（ZTE A2020 SP / P865A02，骁龙 865 / SM8250，Adreno 650）的原生 ARM64 Linux / ArmadaOS 实验性适配记录。

**状态日期：2026-10-17。已在一台实机上运行中文 Plasma 桌面、Steam 游戏模式及部分游戏。项目仍处于设备适配阶段，尚无面向其他用户的安装发行版。**

首批进度、方法和问题清单已公开；现提供 [boot #43 与专用 REC 开发预览下载](https://github.com/zry116131/axon10s-pro-armadaos/releases/tag/v0.1.0-dev.20261016)，附内核配置和源码参考包。**尚无完整 ArmadaOS rootfs 或一键安装器。** 使用前阅读 [镜像说明与前置条件](docs/IMAGES.md)，源码来源见 [来源与代码说明](docs/SOURCES.md)。本项目为非官方设备移植记录，与 ArmadaOS、ZTE 或 Valve 无隶属关系。

当前实机已安装 #93，保留 #44 USB 基础、ICC/显示修复与 2 GiB LZ4 ZRAM；当前仅 ZRAM swap 启用。音视频及安装证据见 [视频适配记录](docs/VIDEO-DECODE-TRIALS.md)，历史内存证据见 [ZRAM 验证记录](docs/ZRAM-VALIDATION.md)。#93 的物理交互与长期游戏回归仍待完成。

## 当前结果

- 中文 Plasma 桌面、触摸、亮度和音量键已获得实机反馈。
- 八核上线，Adreno 650 原生渲染已验证；Steam 游戏模式、触摸和部分游戏已运行。
- Wi-Fi 配置保存、SSH、代理联网、蓝牙手柄和扬声器基础功能已验证。
- 原 Android super 空间已在 GPT 层面合并进约 **116.28 GiB 连续根分区**，运行单套 ArmadaOS。ext4 可用容量与分区容量不同。
- 专用 Recovery 支持音量键选择、电源键确认、USB root 调试，以及返回系统。
- **USB2 HUB 已修复并固化至 #44**：无外部供电的 HUB、小米键鼠接收器通过正常重启和实机操作确认；有线 USB 手柄尚待实测。
- 原生 s2idle 及 RTC 唤醒已通过受控测试；深层驻留、实际待机耗电和长期可靠性仍待验收。开机白条、部分游戏兼容及性能问题仍未全部解决。

## 版本边界

| 层级 | 状态 |
| --- | --- |
| 正常启动分区 boot_a | #93 已安装，整分区回读、正常重启、REC/GPT 保持及只读恢复通过；完整 #87 回滚备份保存在手机与电脑 |
| 本轮运行环境 | #93 从内部存储正常启动；H.264 硬解与 VP8/VP9 软件回退通过，音频修复已集成；硬件视频开关已启用 |
| 桌面修复 | KWin 6.7.5 已安装，受控唤醒回归通过；后续正常重启基础交互已确认，长期稳定性待验证 |
| 休眠策略 | 原生 s2idle 已持久化；#93 临时运行的 RTC/恢复后音视频测试通过；电源键实机反馈来自此前 #82，不能替代 #93 物理验收 |

**#93 正常重启的软件检查已通过；画面和触摸的用户确认来自较早节点。长期稳定性、深层驻留和待机功耗仍未验收。** 每项功能的证据层级见 [支持矩阵](docs/STATUS.md)，镜像身份见 [验证记录](docs/VALIDATION.md)。

**当前维护记录已更新到 #93；本地提交尚未推送，GitHub 认证不可用。H.264 硬解、音频通路与休眠恢复已有受控证据；VPx 硬解、SoundWire 告警、实际游戏 OOM、待机耗电及长期 GPU 稳定性仍未全部解决。详见 [后续计划](docs/ROADMAP.md) 和 [运行时修复与检查](docs/RUNTIME-REPAIRS.md)。**

## 分批分享计划

第一批为进度、情况与移植经验。第二批现已提供两份已验收的 boot/REC 镜像、配置、源码参考和校验信息；完整干净 rootfs 与可复现安装流程仍待完成。镜像通过 Release 分发，不存入 Git。

## 文档

- [镜像下载、适用范围与校验](docs/IMAGES.md)

- [视频硬解试验与当前边界](docs/VIDEO-DECODE-TRIALS.md)
- [USB HUB 修复与验收](docs/USB-HOST.md)
- [实际移植经验与踩坑记录](docs/EXPERIENCE.md)
- [硬件与功能支持矩阵](docs/STATUS.md)
- [剩余问题与复现现象](docs/KNOWN-ISSUES.md)
- [移植方法与关键发现](docs/ARCHITECTURE.md)
- [版本和验证边界](docs/VALIDATION.md)
- [恢复路径与维护约束](docs/RECOVERY.md)
- [后续计划](docs/ROADMAP.md)
- [来源、致谢与源码整理范围](docs/SOURCES.md)
- [公开范围与隐私处理](docs/PUBLICATION.md)

电话、移动数据、相机和指纹不在本阶段范围内。同为 SM8250 的其他手机也需要独立的板级适配，不能沿用本机分区布局或其他机型的 ABL、设备树与固件。
