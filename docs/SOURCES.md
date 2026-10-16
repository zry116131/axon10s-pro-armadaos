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

## 待整理的实现范围

本地工程包含设备树和配置片段、RM692A4 面板驱动、Synaptics TCM 触屏、音频/电源适配、boot 镜像打包器、rootfs 集成、SDDM/Decky 配置、KWin 构建补丁和按键 Recovery。

首批只公开文档。源码目录混有调试历史、上游驱动和本机安装工具，需逐文件保留作者/版权/SPDX、标记本地修改、清除设备默认值并验证构建依赖。尚未完成可复现开源发行包，不对整个工作目录套用统一许可证。

原厂镜像、固件、个人校准数据、Steam 游戏文件、系统整盘备份与商业软件不随本文档发布。后续二进制发布须同时满足各组件许可与对应源码要求。
