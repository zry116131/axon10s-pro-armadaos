# A 槽启动成功标记修复（2026-10-17）

原 rootfs 的 configure.sh 屏蔽 qbootctl.service，未建立替代的启动成功确认流程。多次启动后，bootloader 实测 A 槽 retry=0、successful=no、unbootable=yes，并自动转到 B 槽，导致恢复时停留 fastboot。

先将活动槽恢复 A，确认正常运行已安装且校验过的 #45。该设备使用 Qualcomm GPT 属性，不能按通用 AOSP misc 结构直接修改。备份六个 UFS LUN 的主备 GPT 和 misc 首页，验证两份表及 CRC 一致。固定使用 linux-msm/qbootctl commit `39a6e6daaf029fb0a083777679a15ea2c18f72de`，ARM64 静态构建，明确指定槽 a。

工具审查注意事项：此版本 -m 会遍历既定 A/B 分区列表；当 boot_a unbootable=1 时还有 XOR 翻转路径。本次先确认 boot_a 活动、可启动且安装镜像与 #45 哈希一致，再标记，未进入该分支。系统中目标磁盘有软件只读保护；首次写入被拒绝后，回读证明全部 GPT 未变。仅在第二次受控写入期间临时解除所需磁盘保护，并在退出时恢复。

写后独立回读证明：只改变 boot_a、vbmeta_system_a 的 successful bit，以及对应主备 GPT CRC；其他条目、几何、头部及四个其余 LUN 均完全一致。bootloader 随后确认 current-slot=a、successful=yes、unbootable=no、retry=6。

随后两次正常启动均返回 #45，主备 GPT 与预期成功标记状态保持逐字节一致，retry 仍为6，Steam游戏模式和两级swap正常。当前修复针对已经验收的安装 #45；后续刷入内核可能重新清除成功标记，部署流程必须在新安装版本通过验证后再次显式确认。不能让临时 fastboot 候选自动将磁盘中的另一内核标记为成功，因此原屏蔽服务尚未直接取消。

备份、设备标识及原始分区表留在私有维护环境。参考：[Linux qbootctl](https://github.com/linux-msm/qbootctl)、[Qualcomm bootctrl](https://android.googlesource.com/platform/hardware/qcom/bootctrl/+/refs/heads/android14-qpr2-s5-release/boot_control.cpp)。

## #54 PON 更新

后续直接写入已验证的 #54 boot_a 并完整读回，GPT未修改，已成功标记保持有效。正常启动后六LUN主/备GPT比较仍通过，未再次执行qbootctl。#45完整启动分区备份已额外保存于手机和维护机。
