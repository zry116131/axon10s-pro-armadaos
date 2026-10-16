# Bounded VA startup recovery

Installed runtime safeguard for the observed Axon VA macro vote timeout. This does not fix or explain the original APR response timeout, and automatic recovery of a failing boot remains unverified. Manual reprobe previously restored the card; the installed service has been verified to skip #56 and do nothing on a normally bound #64 boot.

The script verifies board compatible, exact VA DT register identity, VA driver identity and override, bound Q6AFE on the actual `aprbus`, both RX/TX deferred-supplier signatures, and a recent matching vote(3)/VA -110 log pair. It reserves one attempt with an exclusive `/run` marker before writing only `3370000.codec` to platform `drivers_probe`. It never unbinds devices or changes voltages, mixers, boot or recovery partitions.

User-space waits are bounded and the service never restarts automatically. Kernel uninterruptible I/O cannot be forcibly bounded by this script or systemd; a stuck probe is reported without another attempt. Normal invocation when VA is already bound makes no changes. Missing evidence aborts. No changes to PipeWire ordering are made; late card enumeration following automatic recovery needs a real failing boot test.

Paths: script `/usr/local/libexec/axon-audio-startup-recover.py`, unit `/etc/systemd/system/axon-audio-startup-recover.service`. Enabled for both `multi-user.target` and this phone's active `axon-test.target`. The unit condition skips kernels without the VA driver, including fallback #56.

Validation: Python gate tests, exact recorded failure log matching, live identity readback, real systemd unit verification, #56 condition skip/no marker, #64 normal boot no-op/no marker, automatic speaker+microphone enumeration with persisted UCM. The unit is a safeguard pending a root-cause fix, not grounds to install #64 as the default kernel.
