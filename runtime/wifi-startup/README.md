# One-shot Wi-Fi startup recovery candidate

This service addresses an observed startup failure on the Axon 10s Pro. In a #56 boot, ath11k failed to load board data with `-2` and created no Wi-Fi interface; a later, single rebind of PCI `0000:01:00.0` restored the interface. Initramfs and root board files matched. This does not establish whether switch_root timing, firmware lookup, or another initialization condition caused the failure.

The script requires all of the following before one rebind:

- Root DT compatible contains `zte,axon10s-pro`.
- Fixed PCI function `0000:01:00.0` has vendor `17cb`, device `1101`, remains bound to `ath11k_pci`, and has no driver override.
- That function has no net interface. Any existing interface makes the healthy path a no-op, before reading firmware or invoking dmesg.
- The current kernel log contains that exact function's `failed to load board data file: -2` message.
- Root `/lib/firmware/ath11k/QCA6390/hw2.0/board-2.bin.xz` hashes to `d7ad84920359fdce4d05d5a1b318a1e2749782dd51501ead9f6a3e1f9af7615d`.

A root-only exclusive `/run/axon-wifi-startup-recover.attempted` marker reserves the attempt before either sysfs store. The child writes only this function's fixed unbind and bind files. Firmware is never modified. Other PCI devices and USB are not rebound. The child rechecks PCI identity, binding, override and interface presence immediately before unbind. An interface that appeared meanwhile causes a successful skip. An absent matching failure signature also logs a successful skip; identity/file errors remain explicit failures. There is no retry, including after manual service restart in the same boot. Do not remove the marker to retry automatically.

The child wait is limited to 12 seconds, followed by a one-second SIGKILL wait; successful rebind has up to 15 seconds to expose an interface. The service has a 40-second start timeout, two-second stop timeout, and control-group killing. These bound ordinary userspace waits, not uninterruptible kernel I/O. A blocked unbind can leave the device unbound; a killed parent may not complete bind. The log explicitly requests recovery, and the attempt remains consumed. Interface presence does not prove association or internet connectivity. Historical errors in the same boot are accepted only while the same device is currently without an interface; it remains possible that a different later fault caused that absence. No atomic exclusion with spontaneous driver recovery is claimed.

Installation, after review: copy the Python script to `/usr/local/libexec/axon-wifi-startup-recover.py` and the unit to `/etc/systemd/system/axon-wifi-startup-recover.service`, then enable it for the actual `axon-test.target` (also listed for `multi-user.target`). Local filesystem, module-load and udev-trigger ordering are included. There is no NetworkManager dependency or ordering edge, allowing it to discover the restored interface without an ordering cycle. Udev-trigger completion is not udev-settle; the script deliberately skips rather than broadly waiting/reprobing on incomplete or unknown initialization.

Status: private fake-filesystem and mocked-process gate tests passed, including healthy no-command behavior, hash/error/identity rejection and one-attempt enforcement. Parent review and repeated gate tests passed. The script and unit are installed and enabled for axon-test.target. On temporary #71, direct invocation and the service both skipped the healthy interface without rebinding; systemd unit verification passed. Actual automatic recovery during a failing boot remains unverified. This is a startup recovery measure, not a root-cause fix.
