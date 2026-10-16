# FFmpeg V4L2 pending-packet experiment — v1 rejected

**Do not apply v1.** Two-input-buffer hardware pressure testing returned zero frames and exit190: returning zero without a valid frame violates the receive callback contract. The isolated ownership stub missed this. A complete retry/poll path is still required.

Applies to upstream FFmpeg 8.1.3 `libavcodec/v4l2_m2m_dec.c`. Not installed on the phone; not a replacement for its downstream package.

The enqueue path explicitly retains `buf_pkt` on EAGAIN. A later transient `v4l2_try_start` failure returns zero through `fail`, which unrefs that pending packet. Return zero directly in the non-ENOMEM branch to preserve it. A successfully queued packet has already been unreferenced. Enqueue hard errors and ENOMEM still clean up; draining bypasses start as before. The existing return-code semantics are preserved.

A private C regression harness extracts the actual upstream receive function and stubs its dependencies: three EAGAIN/start-failure iterations lose the pending packet in the original, while the candidate retries the same packet and submits it exactly once. ENOMEM, enqueue hard error, ordinary success, accepted-packet/start failure, EAGAIN with successful start, EOF/draining and fetch EAGAIN also tested with ASan/UBSan. These checks establish control flow, not physical-device correctness.

The phone reports negativo17.org `ffmpeg-8.1.3-1.fc44`; its exact source-RPM patches have not been audited. Hardware tests use separate minimal upstream ARM64 binaries with identical build flags; only this patch differs. See the video trial record for actual results and limitations. Keep Steam hardware video decode disabled pending end-to-end acceptance.

Upstream source: https://raw.githubusercontent.com/FFmpeg/FFmpeg/n8.1.3/libavcodec/v4l2_m2m_dec.c

## v2: bounded internal retry candidate

`0002-pending-packet-poll-retry-experimental.patch` applies directly to pristine n8.1.3, **not on top of v1**. After a transient start failure it uses existing capture dequeue/poll to service source-change. While a packet remains pending, EAGAIN causes internal retry of that packet, with 20ms polls, 1ms yield and a two-second no-progress deadline. A real dequeued frame is required for return0. ENOMEM/enqueue errors retain cleanup. The deadline cannot interrupt blocked ioctls, repeated EINTR within poll or pre-existing no-pending blocking waits; external trial timeout remains mandatory.

Extended ASan/UBSan tests check frame validity, ownership, internal retry, timeout cleanup, no-pending EAGAIN, hard errors and EOS. This remains a candidate requiring broader hardware acceptance, including source changes and seeking. No system FFmpeg package was replaced.
