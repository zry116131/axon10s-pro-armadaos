# 来源与代码说明

下列版本来自本地已检出的参考仓库或构建记录，保留为复核入口。引用某项目不表示直接采用该设备的刷机二进制，也不代表上游认可本移植。

| 项目 | 固定版本 / 用途 |
| --- | --- |
| [ArmadaOS](https://github.com/armada-os/armada) | `8687635f562f6219a31999a8ef2f7048d76f1748`；系统、工具、会话与内核集成参考 |
| [ROCKNIX](https://github.com/ROCKNIX/distribution) | `5a0e41634ed464028b185cc0851c74b92f507ac1`；SM8250/Retroid Pocket 5 配置参考 |
| [单翼 armadaos-freedom](https://github.com/mydanyi/armadaos-freedom) | `2c8c433e806e5bc0a0e7195f450af305c1bca460`；移植分层路线参考 |
| [Y700 / tb323fu-linux](https://github.com/joonhoekim/tb323fu-linux) | `11a25bf89b65fff48112a91a0b25bc247e7736d8`；内置 DTB 与动态 RAM 映射等补丁参考 |
| [Goodix tfa98xx](https://github.com/Goodix-vas/tfa98xx) | `9ae7cc60b4f5a8d4e4e68a65a813758ed669dc16`；功放驱动参考 |
| Linux | 7.2.6；源码归档 SHA-256 `039aef84f2b0994aeda3f4fcfc3d02ec9d7a9bbb9020ea264c43f446c860f606` |
| KWin | `6.7.5-1.fc44.armada`；保留两项 Armada 补丁后构建，修复回归见验证记录 |

## 开发预览源码范围

本地工程包含设备树和配置片段、RM692A4 面板驱动、Synaptics TCM 触屏、音频/电源适配、boot 镜像打包器、rootfs 集成、SDDM/Decky 配置、KWin 构建补丁和按键 Recovery。

首批文档之后，开发预览 Release 提供已筛选的板级源码快照、Linux 7.2.6 基线与 Ubuntu 运行库来源包，保留作者/版权/SPDX。源码快照还包含从两份历史镜像中提取的启动脚本。完整用户空间整合、从干净环境重建和逐字节复现仍待验证，不对整个工作目录套用统一许可证。

完整原厂镜像、个人校准分区、Steam 游戏文件与系统整盘备份不发布。boot/REC 保留原厂引导容器所需 ramdisk/DTB 和驱动需要的固件；这些组件的版权和许可不因本项目发布而改变。参见镜像说明，不将 Linux 许可套用于整份镜像。
