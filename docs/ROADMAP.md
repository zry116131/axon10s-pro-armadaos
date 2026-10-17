# 后续计划

2026-10-17 已恢复主动适配。设备持有者授权无人值守推进；当前已安装稳定版本为 #56，后续候选先临时启动验证，并保留原 boot/REC 回滚路径。

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
