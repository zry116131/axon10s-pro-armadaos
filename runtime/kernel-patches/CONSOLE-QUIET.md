# Axon 10s Pro production console logging

The #84 bring-up kernel forces a verbose legacy serial console through
`CONFIG_CMDLINE_FORCE=y`, `loglevel=8` and `ignore_loglevel`. The GENI console has
synchronous polling paths. This setting is inappropriate as an unconditional
production default on this phone: matched sleep trials reproduced DPU timeouts
and event-queue overflow with verbose output, while temporary console filtering
completed two native sleep trials without the specified display errors.

For a build based on validated #84, retain every other command-line argument and
change only `loglevel=8` to `loglevel=4`, removing `ignore_loglevel`:

```text
CONFIG_CMDLINE="console=ttyMSM0,115200n8 earlycon=qcom_geni,0xa90000 loglevel=4 clk_ignore_unused pd_ignore_unused rdinit=/init panic=15 cpuidle.off=0 msm.separate_gpu_kms=0 snd_soc_tfa98xx.no_start=0 nokaslr"
CONFIG_CMDLINE_FORCE=y
```

The tested candidate release is `7.2.6-axon10s-consolequiet1` (#87). No DPU
instrumentation or driver change is included. BWMON, isolated generic QCE,
DSI clock fix, complete DT and initramfs remain as in #84. Compare the complete
config and embedded payloads, rather than merging an unrelated default config.

Console priority 4 prints priorities 0–3, including errors. Lower-priority
messages remain available through the kernel ring and journal; log generation
is not disabled. The existing 128KiB ring still has finite retention. Early
informational serial markers and console-type ramoops coverage can be reduced;
this does not guarantee complete logs after a hard reset. USB shell and REC
status output use their own gadget TTYs, and are not suppressed by this setting.

For temporary diagnostics, lowering console_loglevel alone is ineffective while
ignore_loglevel is enabled. Record both original values, change both settings,
and restore both after the diagnostic window. Preserve the kernel ring and do
not globally disable errors to hide a failing trial.

See `docs/SUSPEND-TRIALS.md` for the precise controls, timing differences,
recovery observations and installation status. PM success, later drawing
progress, physical touch acceptance and measured standby power are separate
checks. This mitigates a demonstrated source of timing interference; it is not
proof that every DPU/GPU fault or power-management problem is resolved.
