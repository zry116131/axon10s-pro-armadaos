# 后续计划

2026-10-17 已恢复主动适配。设备持有者授权无人值守推进；当前已安装并正常启动的版本为 #93，后续候选先临时启动验证，并保留原 boot/REC 回滚路径。

1. **版本收尾**：已完成 #43 游戏模式/触摸和 #44 无供电 HUB/键鼠固化、正常启动软件检查与实机确认；继续观察长期稳定性，新增变更仍需恢复路径回归。
2. **休眠**：修正触屏与父 I2C 的电源管理顺序，验证电源键唤醒，再测 Wi-Fi、蓝牙、音频及待机功耗。
3. **接口与显示**：补测有线 USB 手柄、PD HUB、双角色反向热插拔与休眠恢复；外接显示器及开机白条。
4. **完整硬件能力**：充电、无线充电、电池健康、其他音频通路。
5. **游戏专项**：用户恢复测试后采样性能/发热，处理内存压力、杀戮尖塔闪烁和跨游戏输入回归。
6. **可复现源码交付**：整理内核补丁、设备树、构建配置、用户空间集成与 REC 源码的来源和许可；现有 #43/REC 开发预览已公开；后续整理 #44 对应材料，并在干净环境验证完整重建流程。
7. **更新维护**：制定保留本机内核、GPT 和 Recovery 的更新/回滚方案。暂不宣称兼容官方整套 OTA。

OptiScaler 属于后续可选增强，尚未安装或完成游戏验收，不列入基础适配已完成项。


## Required next milestone: native low-power standby

User reaffirmed on2026-10-17 that deep sleep and standby drain must be repaired. Completion requires measured standby power reduction, repeated reliable power-key wake, and display/touch/Wi-Fi/audio recovery. Screen-off simulation or CPU idle counters alone do not satisfy it. Current #56 exposes only `[s2idle]` in mem_sleep; command line retains clk_ignore_unused/pd_ignore_unused and verbose console options. These are diagnostic leads, not proof of the cause or authorization to remove them without dependency review. Preserve USB and boot/REC recovery; begin with existing suspend/wakeup evidence and read-only power-domain/residency inspection.


## 2026-10-17 native-wake and ICC checkpoint

Temporary82 passed RTC wake, user-confirmed immediate power-key wake, and repeated timed wake with no failed system-suspend callbacks. Display/touch were user-confirmed after the first RTC cycle. This removes the earlier assumption that every native suspend necessarily hangs; power measurement and longer reliability remain open.

Three enabled consumers lacked matching kernel modules: two BWMON devices and QCE. Manually supplying exact82 modules bound all three and allowed all12ICC providers to synchronize; INT_MAX initial votes disappeared. A subsequent28.615s RTC sleep returned with2187successful callbacks. Candidate83 will incorporate the needed drivers into stable56-derived kernel configuration; it is not yet boot-tested or installed. APSS SMEM631 observer returned EINVAL before and after suspend and was unloaded; it supplied no firmware-residency evidence. USB charging prevents an isolated battery standby comparison in the current unattended setup.


### 2026-10-17 runtime checkpoint: installed #84

#84 is installed and normally boots with all12ICC providers synchronized, initial INT_MAX requests removed, generic QCE isolated, original CPU crypto/storage ICE retained, and only2GiBLZ4ZRAM. Boot/REC/GPT verification and #56 rollback backup are recorded. Native s2idle policy survives reboot. Short systemctl/Steam and180-second RTC trials complete, but firmware residency and isolated battery power remain unmeasured.

Display recovery remains open: early-boot native sleep produced DPU frame timeouts, while later systemctl/Steam trials showed hundreds of forced-damage completion interrupts without errors. PM success is not full display acceptance. Investigate this distinction before declaring deep-sleep repair complete. The proposed extra memory test stopped at its CPUQuota guard because CFS_BANDWIDTH is disabled; no test allocation occurred.


### 2026-10-17 runtime checkpoint: installed #87

#87 retains84ICC/DSI/ZRAM/DT/initramfs and removes forced verbose serial logging from production CMDLINE (loglevel4; noignore_loglevel). Matched46s controls reproduced DPU errors with verbose output and completed without specified errors with temporary console filtering. Non-diagnostic87 passed short and177.4s native suspend, later drawing/idle transition and USB checks; boot_a installation had full readback, unchangedREC/GPT and restoredRO, and ordinary reboot succeeded. An additional installed87shortnative trial passed. The original84fullpartition backup is independently stored onphone/Mac.

Permanent native sleep has been enabled atomically with a separate original-policy backup; its installed-policy27.7s cycle and reboot-persistence checks passed, as recorded inSUSPEND-TRIALS.md. This is a functional reliability improvement, not measured deep-power acceptance. Isolated standby power, firmware residency,87physicaltouch/key acceptance and gameGPU regression remain open. Hardwarevideo remains globallyoff pendingVPxfirmware compatibility; no unsupported hardware capability is claimed fixed.


### 当前验收缺口与已交付候选

#87 完成了真实游戏启动/Steam退出、界面返回和128MiB自身映射ZRAM读回验证；这些检查不覆盖游戏实际OOM及长期游戏帧时间。已部署的[OOM会话策略](../runtime/game-mode-oom/README.md)现已收进项目，实时读回continue。该服务未委派且包含UI等20个直接进程，不可通过降低整个组的内存上限测试游戏OOM。

#90仅临时启动，音频测试及两轮RTC休眠已记录；[Q6AFE事务补丁](../runtime/kernel-patches/AUDIO-VOTE-MATCHING.md)可复现该源码。SoundWire告警、ADC/主观音质、DSP重置/回调退出边界仍未完成。该节点机器返回#87；当前已推进至下述#93安装节点。VPx固件LOAD失败仍缺同固件原厂成功时序；待机功耗/深层驻留仍缺可用测量证据。上述项目保持未验收，不以现有局部通过替代。


### 当前安装节点：#93

#93 全量清理重建，消除了 #90/#92 遗留的 SoundWire 诊断对象；音频事务修复和 H.264 兼容配置已集成。临时实测通过音视频并发、VP8/VP9 软件回退、28.39秒原生休眠和恢复后音视频；已安装到boot_a，完整分区回读一致，REC/GPT不变并恢复只读。普通重启进入#93，游戏模式与2GiBZRAM正常。完整#87回滚备份同时保存于手机和电脑。

硬件视频开关已启用，并在安装后重新启动游戏模式验证：H264720p90帧硬解、VP8/VP9各60帧软件回退均结束且0丢帧。此后界面心跳100帧/2012ms、最长间隔83.5ms，说明界面可响应，不构成流畅度改善的充分证明。旧release模块目录未复用或强加载；当前功能未加载动态模块，核心驱动已内置，通用掌机配置中的可选模块仍不代表本机支持。

保留此前未验收项：VPx固件硬解、SoundWire bit9、模拟音频质量、实际游戏OOM/长时间GPU稳定性、#93物理触摸/按键、深层驻留与隔离待机功耗。代码与记录已同步 GitHub；#93 启动镜像见 v0.2.0-dev.20261017 开发预览，完整 rootfs 和通用安装流程仍未提供。
