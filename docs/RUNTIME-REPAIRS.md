> 当前节点（2026-10-17）：#87 已安装并完成普通重启验证。保留 #84 的 ICC、DSI 和唯一 2 GiB LZ4 ZRAM 方案，关闭强制详细串口输出，保留错误输出及系统日志。临时启动阶段通过短时和 180 秒原生休眠（实际约 177.4 秒），恢复后绘制与 USB 通信正常，未见指定 DPU 超时/溢出；安装后又通过一次约 28 秒原生休眠。日常睡眠策略已原子切换为 s2idle，独立入口实测约 27.7 秒并完成重启持久性验证；视频硬解全局保持关闭。详见 [休眠验证](SUSPEND-TRIALS.md) 和 [日志配置](../runtime/kernel-patches/CONSOLE-QUIET.md)。实际待机耗电、固件深睡驻留以及 #87 物理触摸/按键验收尚未测得。

> 后续节点：#45 ZRAM已安装并完成正常重启软件验证，详见 [ZRAM验证](ZRAM-VALIDATION.md)。下文保留本轮早期#44检查时点。

# #44 运行时修复与底层检查（2026-10-16 晚）

设备持有者已恢复主动适配，并授权由当前维护端承接 GitHub 关键节点更新。运行内核仍是 #44；本轮尚未更换 boot 或 REC，公开 Release 仍为 #43。以下记录区分配置生效、受控测试和用户验收。

## 已实施

| 项目 | 改动与证据 | 验证边界 |
| --- | --- | --- |
| 游戏模式方向与轻量 UI | Gamescope 独立会话设置方向；Steam 减少动画、低性能库模式、禁用动态头像等设置已回读 | 未完成长期帧时间对比；桌面 Big Picture 与独立 Gamescope 会话分别处理 |
| CPU/GPU 策略 | SM8250 三簇使用实际支持的 schedutil；Balanced CPU 上限 1516800/2054400/2361600 kHz，GPU 305–587 MHz | 运行时读回一致；没有超频，没有关闭温控，持续热稳定性待测 |
| 充电图标 | 针对本机 fuel-gauge 电流方向添加 UPower 兼容层 | 用户已确认图标正常；不代表底层充电器驱动完整 |
| 普通 swap | 启用 2 GiB 磁盘 swap，优先级 10、swappiness 40，持久配置已写入 | 受控换页数据校验通过；当前内核无 ZRAM/ZSWAP，64 MiB 是测试规模 |
| OOM 会话策略 | Gamescope 服务 OOMPolicy 从 stop 改为 continue | 独立受限 cgroup 验证策略差异，会话配置读回一致；尚未通过游戏 OOM 全流程回归，UI 自身被杀仍可能退出 |
| Steam 视频兼容 | 关闭硬件视频解码，保留 GPU 加速 WebViews | 参数和设置回读符合预期；新日志未重现缺失视频设备错误，不等于 CEF 崩溃根因已修复 |
| 背光事件噪声 | 保留原 systemd-backlight 屏蔽，仅清除本面板匹配的无效启动请求 | udev 校验通过，设备属性中请求消失，亮度未变，观察窗口内错误计数为零；未做重启验证 |

## 新确认的底层缺口

- Venus 设备树 disabled；视频驱动配置为模块但当前模块目录无 `.ko`，没有 `/dev/video*`。SoC 有视频硬解硬件，不等于当前 Linux/Steam 调用链可用。
- ZRAM、ZSWAP、PSI 未启用。正在复建匹配 #44 的构建环境；压缩内存尚未交付。
- 显示初始化存在 DSI PLL lock failed 和时钟重复 disable/unprepare 警告。尚未建立它与 CEF GPU 子进程冻结的因果关系。
- 第二个 PMIC PON 注册同名 reboot-mode 返回 -EEXIST；主 PON 和电源键驱动正常绑定。
- fuel-gauge 未找到 charger supply；Linux 充电器关联和健康度接口不完整。不能据此推断无物理充电或无硬件保护。
- 当前音频源代码移除了采集后端连接，PipeWire 无麦克风源。需要板级音频适配，单加 UCM 不足以解决。
- 原生休眠仍未验收；开发 cmdline、PSCI 提示与启动镜像对齐问题需结合原启动链逐项核实。

CEF GPU 子进程曾退出并恢复；日志出现共享图像/缓冲区错误，缺少精确崩溃栈。直接重载其内部页面后出现过白屏，重启独立游戏模式会话恢复；不再使用内部页面 reload 作为恢复手段。当前不能宣布 GPU 冻结彻底解决。

## 恢复与后续顺序

已保存当前完整 boot 分区、内核配置及运行 DTB；完整 boot 备份校验与实机分区一致。直连 USB 的诊断串口和 root shell 已验证，SSH 同时可用。专用 REC 保留，尚未进入或改写。

下一阶段先验证同源模块构建与 ABI，再做 ZRAM 的小规模数据完整性及内存压力验证；视频解码需分别验证设备树、固件、内核驱动、原生解码及 Steam 用户态，不能仅凭设备节点验收。需要改 boot 时保持 #44 USB 双角色能力和可返回的 REC。

背光修复位于 `runtime/99-zz-axon-backlight.rules`。部署前确认该面板名、原服务屏蔽及实际 SYSTEMD_WANTS 完全匹配；用 `udevadm verify` 校验后再 reload 和对指定面板触发 change。回滚时只移除本规则并 reload/trigger。该规则不会解除原背光服务屏蔽。

所有原始日志、内网地址、账号、游戏数据、整分区备份留在私有维护环境，不随进度文档发布。


### #87 game launch/exit regression

On installed87 with persistent native sleep, a180-second bounded capture covered Silksong1030300 launch, process residency, Steam TerminateApp exit and menu return. All180 samples completed; no new classified kernel/CEF GPU events or global OOM kills, no CEF backlog. GPU-thread-hint process identity1607/start2252 and Gamescope identity1073/start1343 remained stable; both Xwayland identities remained stable. Minimum MemAvailable331492KiB, final2912192KiB. The game process4103 exited after the verified Steam exit API; this is not an in-game-menu graceful-exit claim. Returned Steam UI produced122RAF callbacks over2013ms, max16.8ms. Game-mode service remained active, taint0, no failed units, and only2GiBLZ4ZRAM. Physical scanout and game main-menu rendering are not proven by this telemetry; gameplay and OOM-pressure recovery remain separate validation.


### #87 own-mapping ZRAM integrity validation

The kernel lacks CFS bandwidth control, so CPUQuota is not treated as enforced. A separately reviewed candidate used RLIMIT_CPU soft10/hard12s plus1MiB cooperative pacing, with90s service limit, MemoryMax256MiB/SwapMax192MiB and exact87/board/service/game/RTC guards. Independent review caught and fixed combined systemctl service-output acceptance before deployment.

The real test completed with serviceexit0/resultsuccess:128 disjoint1MiB MADV_PAGEOUT requests against only its own guarded128MiB mapping; exact VMA Swap reached131072KiB. Before/after SHA256 botha626d17da2e502f5b4b8e3ebd23f0bf9daef6255688d8e0bb482b3ae3794a682. No new ZRAM IO error counters, cgroup memory-limit/OOM events, global OOM kills or filtered kernel faults; powerd, NetworkManager and game-mode service remainedactive. Swap configuration unchanged, only2GiBLZ4ZRAM. This validates patterned-data pageout/readback integrity, not incompressible game capacity, hard25%CPU quota, all-game OOM recovery or suspend residency.


### Offline audio vote late-reply isolation candidate

Actual #65 callback/send-helper deterministic schedules reproduced late timeout-A replies being returned as B's handle, including same/different blocks. The caller output pointer was not retained by the callback; freed-heap/dead-stack schedules did not detect delayed output access. A separate uninstalled draft isolates vote state/waitqueue and poisons further vote submissions after uncertain failure. Its response-opcode routing rejects invalid NULL-output/port combinations before send. Independent incremental review confirmed all five existing helper callsites conform and ordinary send/wait behavior is retained. Werror/ASan/UBSan tests cover rejection with zero sends, ordinary clock helper waiting through a late vote, and expired stack output. Unvote remains byte-identical.

This remains offline only: no kernel compilation or full candidate review, no real lock-contention validation, and no guarantee against duplicates from successful requests arriving during subsequent requests. Firmware token identity and APR teardown/drain semantics are unresolved. It is not installed and is not reported as a completed microphone fix.


Audio candidate follow-up: full source review found no additional blocker beyond the documented duplicate-success/token/teardown limitations. An isolated compile using87 generated headers/configSHA28dc85b837916e64d026e072cbb098bf0d6d8dbc849cede28e8509c11acedf44 produced an AArch64 relocatable object with no diagnostics; sourceSHA24bcdee187a281806f924a65d19682dad4f92f6f267ebb422aaa0a8bafa00519. No shared source/object or boot image was replaced. Separate actual-function pthread tests passed300 schedules:100 completion-first,100 timeout-first,100 competing callbacks with one accepted handle. They use real userspace locks/waits with ASan/UBSan, not Linux IRQ semantics or exhaustive race exploration. Deployment remains deferred while transaction identity and firmware response matching are unresolved.


Token evidence checkpoint: pinned official downstream `android-11.0.0_r0.18/include/ipc/apr.h` and `dsp/q6afe.c` confirm a32-bit header token and a separate vote hardware-block payload; the caller assigns both from hw_block_id. This does not establish arbitrary-generation echo on the installed DSP firmware. Existing runtime records contain no vote reply token, and current87 inspection found no usable APR/Q6AFE trace events. A default-off, at-most16-record observer design was independently reviewed; it would establish only existing-token behavior, not prove arbitrary-token compatibility. No packet-format change or device mutation was made.


### #88 temporary audio observer

Built from87 with13 audio modules made builtin, selective65 audio DT/machine/codec/mixer fixes, reviewed vote isolation and default-off bounded observer explicitly enabled by temporary CMDLINE. Original87 initramfs/USB, quiet console, ICC BWMON, QCE-disabled node and DSI fix retained; independent package review passed, no compiler warnings. ImageSHAae7b6e597803345acfc958f452fc867d5583009378b7a5d3c58bcfd9abcb17c1. Fastboot boot only, no partition flash.

Temporaryboot7552412b-57b5-426f-b56c-40040a475f6a reached activegame mode by18.200s, taint0, nofailedunits, bootdiskRO1 and ALSAcard present. Six observer records show two complete transactions: token3/request0x100f4 → token3/response0x100f5,size4 → ret0; token4 likewise. These prove echo of current hardware-block values only; arbitrary generation tokens remain unverified. SoundWire port-count mismatch warnings and missing DMIC sample-rate message remain recorded, not silently classified as fixed. No microphone acoustic-quality or suspend acceptance follows from this boot. A normal return to installed87 was requested after read-only collection.

Normal reboot returned installed87 in boot7c459ee7-9a8e-4de2-b84c-bce3daaaa681; at20.355s game modeactive, persistents2idle, consoleN/4 4 1 7, taint0, nofailedunits, bootdiskRO1 andonly2GiBZRAM. USB shell was also verified while temporary88 ran. No88installation occurred.
