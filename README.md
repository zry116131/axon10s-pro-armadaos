# ZTE Axon 10s Pro · ArmadaOS 适配进度

中兴天机 Axon 10s Pro（ZTE A2020 SP / P865A02，骁龙 865 / SM8250，Adreno 650）的原生 ARM64 Linux / ArmadaOS 实验性适配记录。

**状态日期：2026-10-16。已在一台实机上运行中文 Plasma 桌面、Steam 游戏模式及部分游戏。项目仍处于设备适配阶段，尚无面向其他用户的安装发行版。**

本仓库首批公开内容是进度、方法、验证边界和问题清单。完整适配源码、固件、系统镜像和刷写工具不在本批次中；源码来源与下一批整理范围见 [来源与代码说明](docs/SOURCES.md)。本项目为非官方设备移植记录，与 ArmadaOS、ZTE 或 Valve 无隶属关系。

## 当前结果

- 中文 Plasma 桌面、触摸、亮度和音量键已获得实机反馈。
- 八核上线，Adreno 650 原生渲染已验证；Steam 游戏模式、触摸和部分游戏已运行。
- Wi-Fi 配置保存、SSH、代理联网、蓝牙手柄和扬声器基础功能已验证。
- 原 Android super 空间已在 GPT 层面合并进约 **116.28 GiB 连续根分区**，运行单套 ArmadaOS。ext4 可用容量与分区容量不同。
- 专用 Recovery 支持音量键选择、电源键确认、USB root 调试，以及返回系统。
- 原生休眠、USB HUB、开机白条、部分游戏兼容及性能问题仍待解决。

## 版本边界

| 层级 | 状态 |
| --- | --- |
| 正常启动分区 boot_a | #38；已安装并有正常启动记录，使用分离 GPU/KMS 配置 |
| 本轮运行环境 | #43 临时启动；合并 GPU/KMS、内置 uinput、启用 CPU idle，尚未写入 boot_a |
| 桌面修复 | KWin 6.7.5 已安装，受控唤醒回归通过；长期与正常重启验收待完成 |
| 休眠策略 | 使用模拟休眠；原生 s2idle 的电源键唤醒未通过 |

**当前实机运行结果不能等同于重启后所有功能均可用。** 每项功能的证据层级见 [支持矩阵](docs/STATUS.md)，镜像身份见 [验证记录](docs/VALIDATION.md)。

## 文档

- [硬件与功能支持矩阵](docs/STATUS.md)
- [剩余问题与复现现象](docs/KNOWN-ISSUES.md)
- [移植方法与关键发现](docs/ARCHITECTURE.md)
- [版本和验证边界](docs/VALIDATION.md)
- [恢复路径与维护约束](docs/RECOVERY.md)
- [后续计划](docs/ROADMAP.md)
- [来源、致谢与源码整理范围](docs/SOURCES.md)
- [公开范围与隐私处理](docs/PUBLICATION.md)

电话、移动数据、相机和指纹不在本阶段范围内。同为 SM8250 的其他手机也需要独立的板级适配，不能沿用本机分区布局或其他机型的 ABL、设备树与固件。
