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


### Longer trial: initial access gap, then verified recovery

A separately reviewed 180-second installed-policy Steam trial was submitted as axon-long-suspend84.service. After its expected wake, SSH timed out, USB modem devices and fastboot were absent, and ping did not answer. No result JSON or post-entry kernel evidence could be retrieved. This is not a pass and does not distinguish failure to wake from loss of both communication paths after wake. No physical action was available and no remote reset was performed. Post-policy reboot validation and further hardware tests are deferred until access returns.

Runner comparison found no duration or RTC-unit conversion error. Review identified an inherited asynchronous-entry risk: if the Steam URI command times out before suspend actually starts, generic failure cleanup can clear the backup alarm while an accepted asynchronous sleep request remains pending. This is a possible harness defect, not an established explanation for this device's loss of access. A separate corrected runner must preserve the alarm when submission is uncertain and persist pre-entry phase evidence before any further trial.


Subsequent evidence resolves this access gap: the same #84 boot returned, and the original runner JSON reports operational-pass with no errors. BOOTTIME minus MONOTONIC gives 174.069180557 seconds suspended, success1→2/fail0, RTC128, empty alarm and preserved installed policy. Device wall-clock journal shows entry at15:09:38+08 and resume at approximately15:12:36; the earlier presumed deadline used an imprecise launch estimate. NetworkManager reconnect completed at15:12:51. No remote reset or physical assistance occurred. This validates the 180-second trial, not overnight reliability or battery energy. The generic asynchronous-cleanup risk remains worth fixing but is not evidenced in this successful cycle.

Post-long-cycle UI heartbeat returned7callbacks in2201ms with visible page. This shows responsiveness but is insufficient to claim normal animation smoothness; idle throttling/display state needs separate interpretation.


### Display recovery is not accepted

Read-only kernel evidence reveals repeated DPU frame-done/kickoff timeouts and software frame-event queue overflow after the first installed-policy short sleep, before the long test. The panel remains enabled, DPMS On and backlight743, but UI heartbeat is slow. PM success alone therefore does not accept full device recovery. The overflow message refers to a software event queue and is not proof of memory-bus underflow. A normal reboot baseline and comparative ICC/clock/IRQ investigation are required.

A proposed128MiB own-mapping pageout regression was rejected before allocation because cpu.max is absent. Exact84 has CFS_BANDWIDTH disabled, so the requested CPUQuota cannot be enforced. No pageout or policy change occurred; this trial is not reported as passed.


### Persistence and first display comparison

A normal reboot after policy installation confirmed #84, persisted s2idle, no failed units, zero kernel taint and active game service. Fresh boot had no DPU frame/kickoff errors. A separate instrumented systemctl30s trial using a runner with durable stage records and conservative alarm handling passed29.562796812s suspended, success+1/fail0. It did not reproduce the earlier DPU errors. Display ICC request multiplicities, display/DSI clock tree parent/rate/count and core_perf parameters matched before/after.

Post-wake core_irq callback0 is compatible with command-mode idle, which unregisters callbacks until the next kickoff; it is not by itself a display-off diagnosis. JavaScript RAF122/2.018s likewise does not prove physical scanout. Further bounded forced-damage observation is in progress; original display-recovery issue remains open.


### Early-boot recurrence and policy rollback

A separate normal boot submitted Steam sleep at monotonic29.992s. RTC woke after28.136263166s, PM success+1/fail0. DPU frame-done timeouts occurred at37.928,38.044 and67.008monotonic seconds, after suspend exit35.161. No pre-suspend wait_for or timeout-pending message was captured. Subsequent311canvas paints/6002.7ms progressed TX_DONE+361 and TE+416 across7.008s monitoring; static observation through approximately298monotonic seconds retained exactly three errors. This reproduces early recovery errors without demonstrating continuous display failure or identifying cause.

Because full display recovery is not accepted, the original fake sleep policy was restored from its exclusive pre-install backup, with metadata preservation and readback verification. #84 remains installed; ICC and ZRAM changes remain in place. Further native tests use temporary overrides and RTC backup. Native-policy persistence was verified historically, but it is not the current daily policy.


### #56 baseline comparison also reproduces display errors

Validated #56 was fastboot-booted temporarily; installed #84 and REC were not overwritten. Steam sleep submitted at monotonic28.692s under a temporary native override while permanent policy remained fake. PM/RTC passed27.763518635s, but the58.042s snapshot already contained15DPU frame/kickoff/queue errors. ICC still contained41INT_MAX tokens. Thus the defect also exists with the prior kernel and its initial bandwidth floor; #84 did not uniquely introduce it. This does not identify the original fault.

The paint probe drew220updates/6000.8ms with a683.4ms maximum callback interval; TX_DONE increased331 over7.133s while the TE callback count stayed488. These are intermittent progress, not full display acceptance. A bounded per-encoder event-ring diagnostic candidate is being built to distinguish kickoff, completion and timer ordering without changing their behavior.


### #85 bounded diagnostic: first failure follows idle

Temporary kernel7.2.6-axon10s-dpudiag1 #85 adds a board-scoped16-record memory ring, with at most three timeout dumps per encoder. No timer, callback or resource-control behavior was intentionally changed. Embedded DT/initramfs match installed84 exactly; permanent policy remains fake. Payload SHA2564deea046013980d6b069e375aa9cd563fb23bec282f4164358d2c2bb594fe8f2. Installed boot and REC were not overwritten.

The first request at24.511s did not produce a PM transition. The corrected harness reported submission-uncertain, retained its alarm/runtime override, and a deliberate reboot cleared that session before another attempt. After page readiness at35.199s in a fresh boot, Steam/RTC sleep passed27.315182542s with success0→1/fail0. A display timeout occurred about3.336s after PM exit, beyond the harness's immediate successful snapshot.

The ring shows two earlier completed frames, then the idle callback (event detail8), a new kickoff53.895ms later and an83ms watchdog firing86.053ms after arm. No instrumented DONE callback appears between that kickoff and timeout. This first failure does not show the proposed timer-arm-after-completion ordering. The record cannot prove whether hardware generated an interrupt or explain why completion was absent. Ring fields are independent samples and instrumentation affects timing.

Five later software event-queue overflows were observed. Source inspection identifies a possible secondary accounting problem: an event dropped when the four-slot pool is full does not decrement frame_pending, while pending>1 suppresses idle scheduling. Late DONE after a timeout may also affect accounting, so five overflow messages cannot be equated to five leaked frames. A later bounded canvas probe completed318draws/6002ms with TX_DONE+319 over7.010s; the event workers were sleeping when inspected. These results establish later progress, not reliable recovery or a physical panel pass. A burst probe failed in its own JavaScript before completing; its failed result is retained and excluded from driver conclusions.

The next diagnostic adds resource/IRQ/TE call boundaries and pending counts to distinguish the initial failure from secondary idle inhibition. It remains a diagnostic, with no claimed fix or standby-energy result.


### #86 confirms pending-based idle inhibition, with overflow preceding timeout

Temporary diagnostic86 (payload bca62d0094009a010078ffab482d12164f5abb90cc6ed291d20bbf12894e8f39) extends the ring to32records and adds resource/IRQ/post-kickoff call boundaries. Exact84DT/initramfs/clock overlay remain preserved; build has no warnings. Independent source review found no intentional control-flow change, but timing perturbation remains.

Steam RTC trial at page readiness35.937s passed28.751135197s. PM exit was41.860monotonic seconds. DONE-event overflows occurred at43.664/44.118/56.253s with pending5/6/7, preceding the first encoder timeout at60.481s. Thus overflow can occur without a preceding encoder timeout. At the first timeout the ring shows several completed frames, each IDLE_SKIP_PENDING=4, then a new kickoff and TE callback return, with no DONE before the watchdog. No resource-off transition is present in that finite window. This confirms software pending counts inhibit idle scheduling; it does not establish the initial reason for queue exhaustion or missing completion.

The first ring's ARM_POST→TIMEOUT_ENTER interval is86.125ms. DONE eventually arrives after137.203ms. Later dump printing visibly adds latency, so later errors cannot be treated as undisturbed repetitions. The observed TE callback has no hardware status return. A subsequent canvas probe drew286times/6002ms with TX_DONE+338 over7.008s and cleaned up; physical scanout remains unverified.

Actual core_perf/enable_bw_release reads0, excluding the worker's optional ICC bandwidth-release wait as the explanation in this run. A bounded worker scheduling/stack capture is prepared for a fresh boot to examine the first overflow. Permanent policy remains fake;86 is not installed.


### #86 sampled control: scheduling delay near the first overflow

A fresh86 boot with the same native Steam trial passed27.894784519s. A bounded100ms sampler captured427records across35.700–85.629monotonic seconds, terminating on its time limit at509844bytes. PID199 accumulated24.628ms runtime and1473.332ms runqueue wait;13stat samples were runnable. All sampled stacks showed kthread_worker_fn; field reads were sequential and do not prove that every intervening state was idle.

The firstoverflow at43.178054 overlapped a sample whose scheduler wait grew244.898ms. That sample began43.177783 and finished43.327356, so the entire wait cannot be placed strictly before overflow. This supports investigating scheduling delay while leaving cause open. Optional worker bandwidth release was disabled in the preceding identical86 run. Firstoverflow preceded encoder timeout by2.609s.

Configuration audit found forced `console=ttyMSM0,115200n8 loglevel=8 ignore_loglevel`. The GENI legacy console has synchronous polling paths. One86 diagnostic snapshot spans0.703s of captured events but its printing spans12.711s; this is an observer-effect warning, not proof of the original fault. A same-kernel temporary comparison will set ignore_loglevel=N and console level4, preserving the other three printk values, error output and kernel ring/journal. Original values are saved exclusively, and an independent restore timer is armed before either write. No persistent command-line change is made for this comparison.


### Temporary console filtering: promising recovery, then matched control recurrence

A first quiet attempt was safely rejected for game-process presence before any PM transition. Its error-free awake observation is excluded from suspend acceptance; original console settings were automatically restored. A fresh attempt required three consecutive ready/no-game checks without weakening the runner guard.

Quiet boot e27b8c0e submitted at44.104s and passed27.813094572s PM/RTC sleep. The453-record sampler measured activeworker run+27.576822ms and runqueuewait+5.390615ms. At101.379s, filtered kernel evidence contained only PM entry/exit, no specified DPU timeouts/overflows. Readback showed ignore_loglevel=N/printk4 4 1 7. Paint311draws/6003ms progressed TX+312; a later burst98draws progressed TX+98 and33of63snapshots had TXcallback0, compatible with idle. Burst timestamps were relative, so it is not established that its entire interval preceded automatic console restoration. At169.105s there were still no specified errors, and original console values were restored/read back before reboot. No physical panel or battery-power claim follows.

To reduce startup-time confounding, matched launchers now use the same>=43s readiness window and three clear checks; only the quiet apply block differs. The detailed-console control submitted46.089s and passed26.819139259s PM but reproduced frame timeout57.828, overflow59.444/67.656 and kickoff wait failure. Its workerwait grew390.759010ms across50s. First ring records true idle, PM_GET_RESULT=1, IRQ/resource enable returns, TE callback return, then no DONE before88.302ms timeout, with no intervening resource-off record. Thus software restore calls completed; hardware completion versus IRQ/software delay is unresolved. A matched quiet repetition and a minimal non-diagnostic candidate are under validation.


The matched quiet repetition submitted46.425s versus control46.089s, and passed28.804935822s. At102.331s its filtered kernel evidence contained only PMentry49.244/exit51.356 and no specified DPU failure. Console readback remainedN/4 4 1 7. Across454samples activeworker wait grew129.659900ms, of which126.502657ms accrued in a sample overlapping PM recovery; this must not be described as uniformly negligible scheduling wait. No later>1ms wait increment was recorded. Original console values were explicitly restored/read back before reboot.

These controls support reducing verbose synchronous console output as a mitigation, while not identifying every hardware/IRQ cause. Candidate87 therefore contains no DPU diagnostic overlays or driver changes relative84. Its only configuration changes are release and forcedCMDLINE: remove ignore_loglevel and change loglevel8→4. DT/initramfs, including embedded bytes, match84; originalDPU source hashes and absence of diagnostic symbols/strings were verified independently. Final build has zero warnings; an earlier make clock-skew warning is retained separately. PayloadSHA2567ddd9a03b08b1da29a4d446de47069798e32b173c0e6ea4c213f930830ec8139. At this checkpoint it is built but not yet booted or installed.

Predeployment review caught an accidental model-string digit replacement in the87 trial harness; it was corrected before deployment and a literalP865A02 assertion was added. Kernel/board guards remain strict. The non-diagnostic candidate still requires real boot/suspend/display regressions before installation or re-enabling permanent native sleep.


### #87 temporary boot: first native cycle passes

Non-diagnostic87 boot36392618-bd81-49e1-aa29-2616efd82faa submittedSteam sleep45.905s and passed27.883168583s. By102.849s only PM entry/exit appeared in the specified DPU error filter. Console readback isN/4 4 1 7 without a temporary filtering service; permanent sleep policy remainsfake. Across452samples the activeworker accumulated22.775505ms runtime and3.279376ms schedulerwait, with no sampled interval exceeding1ms wait increment. This is one functional cycle, not long-term or physical-panel acceptance.

A180s trial was then submitted with explicit InvocationIDf9349ad45dce48eea18a008e44dc52a4. Repeated-unit collection now selects that exact invocation and refuses to reuse an earlier completed result if the requested one is missing or incomplete. Full84 rollback backup creation and any87installation remain deferred until runtime acceptance.


### #87 installed and normally booted

The180s temporary trial passed177.429108370s, with no specified DPU errors through subsequent paint/burst checks. Paint298draws/6004ms advancedTX+299; burst97draws/6003ms had31of64snapshots withTXcallback0. Both cleaned up; USB root shell returned the same87boot identity. Health checks found active independent game mode, taint0, no failed units, no game processes, permanentfake policy and only2GiBZRAM/swappiness40.

A full96MiB #84 backup was exclusively created on the phone, read back and copied to the maintenance Mac with SHA256a0721acb9dddadf437857e450f9223bb34a8df0ca502055c2affb6817f650190. The87 installer passed read-only preflight and ran detached from SSH. Fullboot_a readback SHA2563e26d3b20c4f7562e2d88a8ea56708d9495da21cc9a1590442e7b3bed4172526, REC37 and all24GPTregions unchanged, bootdiskRO restored, transactionwrite-verified. No sleep-policy change occurred.

A normal reboot without fastboot boot returned87 in bootbcab4066-5628-45ed-b87b-08edc0f6193c. At18.377s game mode wasactive, consoleN/4 4 1 7, taint0, no failed units, bootdiskRO1, permanentfake and onlyZRAM. This confirms installed startup. A separate installed-kernel native trial is in progress before any permanent policy enablement.
