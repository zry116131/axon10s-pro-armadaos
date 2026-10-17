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


## Awake RTC check on56

A5-second relative wakealarm was armed only after confirming no existing alarm. At7seconds, pm8xxx_rtc_alarm IRQ count increased0→1 and alarm had automatically cleared; final cleanup wrote0 and verified empty. This confirms awake alarm delivery only, not wake from suspend. RTC epoch differs from wall clock; relative sysfs alarm avoids assuming synchronized time. No sleep policy changed.

Systemd suspend currently dispatches through Armada suspend-dispatch; device-env accepts ARMADA_SLEEP_CONFIG for a temporary per-service configuration. The permanent file remains suspend_mode=fake. Standard systemd-sleep hooks include wake ledger and conditional power-key gating; preserve normal hook flow during trials.


## Scoped collector prepared

Stock /usr/lib/armada/armada_sleep_debug.py qcom() iterates all regular qcom_stats files; ddr_stats can issue QMP freqsync. Private copy changes only that function to allowlist aosd/cxsd. Mock directory confirms no ddr_stats/ddr/SMEM opens; Python compile/import/standalone help and AST equality outside qcom pass. Not installed over system tool. Patch retained in experiments/81-sleep-collector-residency-only.patch.

Existing trace uses private instance,1024KiB/CPU buffer,8,000,000-byte export cap with loss/truncation metadata,24event allowlist and stop cleanup. Includes power callbacks and RPMh sleep/wake filter, but no PSCI-domain events: do not claim those are captured by this tool. Can combine existing CPU s2idle counters with firmware residency.


## #81 temporary boot did not reach a confirmed running candidate

Full compile completed; image validation confirms baseline56 DT/initramfs bytes exactly and only reviewed config differences. Image SHA256 `7a363029f41ede799f56ae182e432c0c6d8d9294722ec54fe1b3008f3b6ec26f`. Vendor TFA code emitted compilation warnings during broad rebuild; no successful warning-free-build claim. Fastboot acknowledged temporary boot, but subsequent USB/SSH identified restored installed56. No81 userspace journal exists. Archived console-ramoops contains bootloader output for normal slot boot, not an identified81 kernel panic; cause unproven. No suspend test occurred and no runner/settings were deployed.56 system running, Steam game active, only2GiB ZRAM, no failed system units.

Probe audit: exact rpmh-stats DT causes late_initcall reads at0x0c3f0048/68/88 (names) and0x0c3f00b8 (DDR magic), all within declared0x400 resource. Mapping does not guarantee firmware/security access, but there is no demonstrated out-of-bounds address or saved panic. This node lacks qcom,qmp: qmp_get returns-ENODEV and driver clears the handle; this exact node therefore sends noQMP atprobe, and its ddr_stats reader would not sendQMP either. Earlier collector exclusion addressed generic potential and keeps the intended two-record scope; it is not evidence that this board was sending QMP.

#82 isolation candidate restores QCOM_STATS=m while retaining81 event tracing, with only release name otherwise different. Compile started. First objective is boot isolation, not suspend validation or a claimed fix. No relaxation of81 runner guards.


## #82 trace-only startup succeeds

Image SHA256 `a85423869a124b3d59ebd9880648cfe508454603d067dddab29a2cd3f3dee311`; compile, package and exact56 DT/initramfs preservation passed. Only QCOM_STATS restored to baseline=m relative to81, besides release name. Temporary boot confirmed kernel7.2.6-axon10s-sleeptrace1 #82, system running, game-mode service active, no failed system units and only2GiB ZRAM. power/suspend_resume, device_pm_callback_start/end and rpmh_send_msg interfaces exist. No suspend test or collector deployment occurred.

This successful boot shows minimal event tracing can run on this device and makes built-in stats initialization the next isolation target. One differential boot does not prove a specific failing MMIO instruction or exclude timing-sensitive causes. Preserve82 as a usable callback-tracing diagnostic; do not claim firmware residency is available. Next tasks are device suspend/resume tracing and separately obtaining safe firmware-residency evidence.

The local guarded81 runner was reviewed before deployment: raised child per-file limit4MiB→64MiB because collector's8MB raw trace can expand to48MB JSON; actual subprocess export test passes. Alarm ownership intent/partial-write cleanup and foreign-alarm preservation are mock-tested. Runner remains local-only and requires81+firmware stats; it was not weakened or executed on82.

After82 normal reboot, SSH confirms installed56, system running, active game mode, no failed units, only2GiB ZRAM. No boot/REC writes or persistent sleep-policy changes.


## #82 devices checkpoint completed

Separate exact82 devices-only runner rejects RTC mode, always selects pm_test=devices, and explicitly does not validate SoC residency. Original81 runner retained. All original guards and cleanup retained; no firmware-stat requirement for this software callback checkpoint. Mock failure cleanup/mode rejection tests and parent review passed. Temporary collector/runner copies under/run verified bySHA; a detached systemd service ran exactly once.

Cyclee0a1756551fa4c3a8fb6c60ce2a895f8: dispatcher returned in8.58s, no runner errors. Trace captured24selectedevents, no truncation/eventerrors or per-CPU overrun/dropped events.2134 completed PM callbacks,0errors,0unmatched starts. Kernel success+1/fail+0 but timekeeping suspended0s, expected for checkpoint; not actual deep-sleep success. Before/after snapshots complete. No new system failed units. Live readback pm_test=none, empty RTC alarm, trace instance absent and temporary sleep.conf absent. Permanent fake-suspend policy unchanged. Summary in experiments/82-devices-checkpoint.json.

Next controlled diagnostic is RTC-woken actual s2idle with callback tracing, while explicitly retaining firmware-residency and battery-power validation as incomplete. Successful devices checkpoint does not test all late/noirq entry/wake paths.


## #82 actual RTC wake returned

Separate RTC-only82 runner retains exact kernel/board/collector guards, permits onlyrtc with pm_test=none, arms+30s and performs owned cleanup. Scope explicitly operational suspend/wake; missing firmware residency remains outstanding. Syntax/mock tests, source review and remote hash62692800e96ffb37fe88d3542ffb2eda698893be36d4a10da3070bdaef183926 verified before detached execution.

Cycleedc6b4d68e924528983b8aaf6138de58: dispatcher returned in33.94s, timekeeping suspended28.613s, kernel suspend success+1/failure+0, last wakeIRQ128 pm8xxx_rtc_alarm.2190 completed callbacks,0errors,0unmatched; trace captured without truncation/eventerrors/buffer loss. CPU0..7 deeper state's s2idle usage each0→1; clusterS2idle0→1. These are software accounting, not firmware residency. UFS reports sleep device power/HIBERN8 link before entry. System running/no failed units; pm_test restorednone, alarmempty, temporarytrace/policyabsent. No persistent policy change; stillfake.

USB/charging connected, Bluetooth off, no gameplay/audio workload. This is one timed wake, not battery-power or repeated power-key wake validation. User confirmed display and touch normal after resume. Independent raw audit accounted for all9586 trace records and2190callback pairs with no loss or failed system-suspend callbacks; BOOTTIME minus MONOTONIC independently gives28.612622seconds suspended. Summary in experiments/82-rtc-wake.json.


## #82 power-key wake and repeat RTC wake

Cycle ec0c35687e2d421b9ff1680b00a30b55 retained the30-second backup alarm but woke from IRQ129 pm8941_pwrkey after7.076129seconds. Power-key IRQ0→2, RTC IRQ unchanged; success+1/fail+0. Independent review paired2187 successful callbacks and accounted for9521trace records with no loss or unmatched events. User confirmed immediate screen-on after a short power press. Runner errors empty; live readback confirmed pm_test none, alarm empty, no temporary trace/config. The runner mode rtc describes the backup mechanism, not this trial's actual wake source.

Repeat cycle ad4d5fb0fbc64e67a29fe8876ceeb10c woke from RTC128 after28.331seconds; success+1/fail+0,2187callbacks without errors/unmatched starts, no trace loss. SSH recovered and USB independently confirmed running82. No firmware residency or battery-power result yet; USB charging remains connected.

## Interconnect initialization floor identified

Read-only live summary shows INT_MAX initial aggregate votes despite much smaller consumer requests. Twelve ICC providers are bound;163d000,1700000,9100000.interconnect have state_synced=0. Their available (not active) consumer links point to unbound1dfa000.crypto,9091000.pmu,90b6400.pmu. Exact82 config has CRYPTO_DEV_QCE=m and QCOM_ICC_BWMON=m, but installed module tree only names the older7.2.6-axon10s release.

Generic ICC core retains init_avg/init_peak until all providers sync. QCOM RPMh aggregation applies this initial floor to AMC/WAKE/SLEEP buckets. This establishes an unresolved software vote, not measured hardware frequency or power. Preferred next candidate supplies matching existing drivers without disabling DT capabilities or forcing state_synced. QCE itself has a fixed393600kB/s probe request across buckets, so removing the INT_MAX floor will not prove optimal sleep power.


## #82 matching-module repair verified at runtime

Matching82 icc-bwmon bound9091000/90b6400.pmu and released9100000.interconnect synchronization. Matching82 qcrypto then bound1dfa000.crypto, releasing163d000/1700000; all12providers state_synced=1. Full live summary contains zero INT_MAX tokens after the repair. No forced sync_state, DT disable, persistent module installation, or boot write occurred. DES/XTS fallback modules supplied as built for the same kernel.

Cycle a073e80154534f59b9234301704564cf after these loads suspended28.615s and woke fromRTC128; success+1/fail+0,2187successful callback pairs, no unmatched starts/trace loss. This validates one native-sleep cycle with the repaired votes, not measured battery-power improvement. QCE's proc-crypto selftest field says passed, but CONFIG_CRYPTO_SELFTESTS is disabled; no hardware-vector claim is made from that field.

Optional APSS-only external observer used qcom_smem_get(ANY,631), no stats-SRAM/QMP/DDR probe. It returned unavailable errno=-22 both before and after an additional successful suspend. Observer was unloaded cleanly; out-of-tree taint remains for that temporary boot. Firmware residency remains unavailable.


## #83 built-in-driver candidate rejected after QCE test-associated reset

Image6c3769e45a40f9649d7b07ca9910d37f482987d96deb988b55fa00613dce821f booted temporarily as7.2.6-axon10s-iccfix1 #83. System/game mode ran, both BWMON devices and QCE bound, and all12ICC providers synchronized without initial INT_MAX votes. Stable56 DT/initramfs were preserved; config changes were BWMON/QCE/LIB_DES/XTS built-in plus release.

An optional explicit kernel known-answer harness targeted cbc-aes-qce and sha256-qce with1024-byte public reference data. During its loading/execution the device unexpectedly reset and returned to installed56. Archived console contains generic axon_qce_kat module-load/taint at63.667116s followed by bootloader output; no KAT completion/timeout or Linux panic was retained. PS_HOLD/WD labels do not identify the faulty component. The harness lacks persistent phase markers, so the exact reset stage is unknown. Independent source review found no concrete buffer-lifetime/SG overrun, but this does not exclude a harness, driver, DMA or firmware fault. No hardware-vector success is claimed.

83 was NOT flashed. Stable56 returned with active game mode, ZRAM-only swap, unchanged fake policy and read-only boot disk. Full96MiB installed56 backup exists on phone and Mac with SHA256c4767b32484dc0671dcf7238d835eca1d9f720f51fda9e9534c4db61bf76dbf8; fullREC37 hash remainsa8ba929e0fbccf13822673edd5458a3eb81d3c4054ab346bc2d74bada45b8335.

Next candidate84 retains baseline56 QCE configuration, builds in BWMON and disables only the unvalidated generic QCE DT node1dfa000.crypto. This removes its unbound ICC link while retaining CPU crypto and storage ICE; it is isolation of an unvalidated path, not a proven QCE root-cause fix. No cryptobam or security permission change is planned.

Reboot timing correction: the82 shutdown journal shows swap stop1534.329→1535.516 (~1.19s), no swap timeout. A USB snapshot of pending swap jobs was insufficient to label ZRAM stuck. No memory-service/timeout change was made.


## #84 installed and native sleep policy enabled

Kernel 7.2.6-axon10s-iccguard1 #84 builds in BWMON and disables only the generic QCE DT node. All 12 ICC providers synchronize and initial INT_MAX votes disappear. CPU crypto configuration and storage ICE remain unchanged; QCE isolation does not establish the cause of the #83 reset.

Temporary systemctl and Steam entries suspended 29.1414 and 25.3251 seconds respectively with RTC wake and no new suspend failures. The payload SHA256 is 7e20edd762b37b19ff11699c03cc227edabaf2606e40f63153fd267185d943a6. Full boot_a readback is a0721acb9dddadf437857e450f9223bb34a8df0ca502055c2affb6817f650190. All 24 GPT regions and REC37 were unchanged; boot disk read-only was restored. A subsequent normal reboot confirmed installed #84 and active game mode.

Permanent sleep.conf now contains suspend_mode=s2idle, with its original policy saved before atomic replacement. A separate installed-policy Steam trial, without a runtime override, suspended 28.737809572 seconds, incremented success by one with no failure increase, and woke on RTC IRQ128. Temporary policy paths were absent afterward. A later reboot is still needed to verify persistence across reboot after this policy installation.

These are functional native suspend/resume results. Firmware residency and battery standby consumption remain unmeasured with USB charging connected. Software UI heartbeat passed after the temporary Steam cycle; it does not replace physical touch or panel verification on #84.


### Longer trial remains unresolved

A separately reviewed 180-second installed-policy Steam trial was submitted as axon-long-suspend84.service. After its expected wake, SSH timed out, USB modem devices and fastboot were absent, and ping did not answer. No result JSON or post-entry kernel evidence could be retrieved. This is not a pass and does not distinguish failure to wake from loss of both communication paths after wake. No physical action was available and no remote reset was performed. Post-policy reboot validation and further hardware tests are deferred until access returns.

Runner comparison found no duration or RTC-unit conversion error. Review identified an inherited asynchronous-entry risk: if the Steam URI command times out before suspend actually starts, generic failure cleanup can clear the backup alarm while an accepted asynchronous sleep request remains pending. This is a possible harness defect, not an established explanation for this device's loss of access. A separate corrected runner must preserve the alarm when submission is uncertain and persist pre-entry phase evidence before any further trial.
