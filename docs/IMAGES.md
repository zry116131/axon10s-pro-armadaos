# Axon 10s Pro ArmadaOS · #93 开发预览镜像

版本：**v0.2.0-dev.20261017**。仅针对 **ZTE A2020 SP / P865A02（SM8250）**。

[下载 #93 开发预览](https://github.com/zry116131/axon10s-pro-armadaos/releases/tag/v0.2.0-dev.20261017)

**后续发现：#93 内置触屏驱动存在启动识别回复匹配和无参数命令头问题，可能开机初始化失败。当前开发设备已采用[触屏恢复补丁](../runtime/touch-recovery93/README.md)。本页 boot 镜像尚未重编入此修复。**

## 文件与身份

- `axon10s-pro-armada-boot93-e116ddc5.img`：73,162,752 字节，Android boot v2 启动镜像。
- `boot93.config`、`boot93.dtb`：该镜像对应的内核配置和 Linux 设备树。
- 源码参考包：本次构建的源码及构建输入参考，范围见包内说明；Linux 基线与用户空间来源包仍见旧版 Release。
- `image-manifest.json`、`SHA256SUMS`：文件身份与完整性校验。

镜像 SHA-256：

```text
e116ddc5572767a06a9bbce669255f87b9d579c9448201f69d20efeea487cbf1
```

发布文件与已经固化的 #93 启动负载逐字节一致。开发设备完成写入、整分区回读及正常重启验证。整分区备份含尾部数据，其哈希与上述发布负载不同。

## 本版变化与验证

- 集成显示时钟、互连带宽同步、音频状态和 DSP 请求匹配修复。
- H.264 硬解兼容配置已启用；Steam 内 720p H.264 硬解及 VP8/VP9 软件回退通过受控测试。
- 音视频并行、原生 s2idle 定时唤醒及恢复后音视频测试通过。
- 清理残留诊断对象后完整重编译，检查未包含旧 SoundWire 诊断符号。

**#93 的长期游戏稳定性、真实游戏内存不足行为、物理触摸/按键完整回归、深层休眠驻留与拔线待机功耗尚未验收。** 早期版本的电源键和触摸实机反馈不能替代 #93 验收。VP8/VP9 硬解仍未解决，部分 SoundWire 告警仍存在。

## 安装前提与边界

**这是启动镜像，未包含完整 ArmadaOS rootfs 或一键安装器。** 仅刷 boot 无法获得 Steam、KWin、音频用户空间配置、2 GiB ZRAM、OOM 策略或持久化休眠设置。这些需要已经适配好的根文件系统；相关公开配置见仓库 `runtime/`，不要整体盲目执行研究脚本。

镜像仍依赖既有的 `AXON_ARMADA` 根分区标签、板级标记与布局检查。布局与 REC 维护条件见[旧版镜像说明](IMAGES-43.md#布局与运行条件)。这些检查对应开发设备，不能照抄分区数字用于其他手机。本次不提供 GPT 修改、自动分区迁移或通用刷写命令。

保留已知可启动镜像和可用恢复路径后再进行设备适配。REC 本次未更改，原专用 REC 及其配置仍可在[旧版 Release](https://github.com/zry116131/axon10s-pro-armadaos/releases/tag/v0.1.0-dev.20261016)下载，其开发维护权限和适用范围不变。回退至不含本版 H.264 兼容配置的旧内核时，应同步关闭 Steam 硬件视频解码并重启游戏模式。

本镜像包含开发用物理 USB root 调试入口，未完成日常分发的访问控制加固。固件、原厂 ramdisk 和硬件引导组件保留各自权利人的许可；Linux 和第三方来源说明见[源码说明](SOURCES.md)及源码参考包。未上传个人 rootfs、账号、Wi-Fi 凭据、GPT 备份、设备校准分区或游戏数据。

## 校验

Linux：`sha256sum -c SHA256SUMS`

macOS：`shasum -a 256 -c SHA256SUMS`

将本次全部附件放在同一目录执行。此次发布复用已完成的实机验收，没有额外刷写手机。测试细节见[视频记录](VIDEO-DECODE-TRIALS.md)、[音频记录](AUDIO-TRIALS.md)和[休眠记录](SUSPEND-TRIALS.md)。
