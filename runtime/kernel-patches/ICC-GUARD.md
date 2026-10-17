# Axon 10s Pro interconnect startup guard

Candidate #84 is based on validated #56, preserving its DSI clock fix, initramfs and all unrelated device-tree properties.

Required configuration change:

```
CONFIG_QCOM_ICC_BWMON=y
```

Device-tree change: only `/soc@0/crypto@1dfa000` receives `status = "disabled"`. Leave `cryptobam@1dc4000`, UFS, inline storage crypto and CPU crypto configuration unchanged. The release used for this candidate is `7.2.6-axon10s-iccguard1`.

Two enabled BWMON consumers and an enabled generic QCE consumer previously had no matching loadable drivers. Their unfinished device links prevented three ICC providers from synchronizing; the global ICC initialization floor then retained INT_MAX requests, including sleep buckets. Loading matching drivers on temporary #82 released all twelve providers and removed this floor.

The separate #83 candidate made BWMON and QCE built-in. It booted and synchronized ICC, but unexpectedly reset during loading/execution of an explicit QCE known-answer test. The saved evidence does not identify the precise failing stage or prove a firmware root cause. #83 was rejected and never installed.

#84 keeps BWMON functional and isolates the unvalidated generic QCE node. Merely leaving its driver absent would recreate the enabled-but-unbound consumer. CPU AES/SHA implementations remain available; no security permission or storage-encryption change is involved. This is not a claimed repair of QCE hardware operations.

Offline acceptance requires exact baseline configuration comparison and a complete DT property comparison allowing only the one added status property. Runtime acceptance requires twelve synchronized providers, no initial INT_MAX aggregate votes, no registered QCE algorithms, healthy boot and independent suspend/recovery checks. See `docs/SUSPEND-TRIALS.md` for actual results and remaining power-measurement limits. Do not infer battery-power savings from request values alone.
