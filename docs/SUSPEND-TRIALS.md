# Native standby investigation

## Requirement

User explicitly requires deep-sleep/standby drain repair. Completion needs measured battery standby improvement, repeated reliable power-key wake, and display/touch/network/audio recovery. Fake screen-off sleep, a deep menu label, or successful software callbacks alone are insufficient.

## Stable56 baseline, 2026-10-17

Live kernel7.2.6-axon10s-dsiclkfix1; mem_sleep only[s2idle], configured suspend_mode=fake. No currently active wakeup source in the snapshot. Cluster debugfs idle_states reported39 entries/691ms, with22 rejections; these are software domain counters during awake operation, not firmware residency or measured standby power. RTC wakeup enabled, wakealarm empty. No suspend attempted this boot.

Prior2026-10-16 report from kernel7.2.6-axon10s:22.889s window, timekeeping suspended5.773s, success+1/failure+1 with-16, last wake IRQ129 pm8941_pwrkey (potentially stale). Tracefs capture absent, firmware residency empty. That report cannot establish reliable wake or identify the failed callback.

## Evidence gaps and source audit

Current DT has enabled c3f0000.sram qcom,rpmh-stats device, but stats driver is not bound. CONFIG_QCOM_STATS=m; running kernel has no matching installed stats module. CONFIG_FTRACE unset and tracefs absent. These explain missing observation interfaces without proving the underlying power fault.

[s2idle] does not exclude deep SoC idle: cpuidle-psci.c64..105 uses genpd suspend plus CPU_SUSPEND. DT includes CPU0x40000004/cluster0x4100c244 and apps_rsc linked to cluster. rpmh-rsc.c915..945 prepares sleep/wake votes on domain power-down; supported hardware can use autonomous solver. The deep menu requires separate PSCI SYSTEM_SUSPEND support (psci.c582..593). Need actual firmware counters and power measurements.

clk_ignore_unused/pd_ignore_unused skip late unused-resource cleanup, not all runtime/system PM. Console awake CX48 is not proof of retained sleep vote: qcom_geni_serial_suspend switches votes to ACTIVE_ONLY and suspends UART. No keep_bootcon/no_console_suspend. CMDLINE_FORCE is enabled, so bootloader-only flag edits would not override current command line. Do not remove flags blindly.

## Candidate81: observation only, not yet hardware tested

Restore56 config/DT/initramfs and stable DSI fix, add built-inQCOM_STATS and minimal FTRACE/ENABLE_DEFAULT_TRACERS event infrastructure. Existing config changes only those two options plus release name; newly selected ring-buffer/tracepoint dependencies reviewed. Function, syscall, latency, probe and Wi-Fi tracers disabled. No power policy, command-line or DT changes. Compilation started; package validation and hardware boot remain pending.

Next: verify firmware aosd/cxsd and power callback/PSCI/RPMh events exist, verify RTC recovery, then one bounded RTC-woken s2idle interval. Compare software suspend counters, firmware residency, and recovery separately. Firmware accumulated durations use architectural-counter ticks. Avoid ddr_stats synchronization/QMP path for initial readout. Do not treat connected-USB/charging measurements as isolated battery standby power.
