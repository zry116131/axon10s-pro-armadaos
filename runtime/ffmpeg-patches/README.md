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

## Decoder PTS token candidate

`0003-decoder-pts-token-experimental.patch` applies after 0002 to upstream 8.1.3. Decoder submission uses positive timestamp tokens and a bounded 4096-entry map to restore the exact original signed PTS on capture. Only successful QBUF commits a token. Unknown or evicted tokens fail explicitly; encoder timestamp behavior is unchanged. Roughly 64 KiB is added per context. Drivers must preserve timestamps; retention is bounded to 4096 later submissions.

ASan/UBSan helper and enqueue tests passed, including failed QBUF, wrap protection, reordered output and signed extrema. On temporary kernel #71, initial seek5 (450 frames), ring reuse (5000 frames) and two-input-buffer pressure (600 frames) matched software frame hashes and timestamps exactly and exited normally. Same-context repeated seeking and genuine resolution reconfiguration remain unverified. This isolated binary is not installed as the system FFmpeg and does not enable Steam hardware video.

## Flush with retired hardware sessions

`0004-retired-session-flush-experimental.patch` applies after 0002 and 0003. The public AVCodecContext remains alive; its flush callback retires the old private V4L2 context and rebuilds the hardware session. A context mutex serializes callback QBUF against retirement. A failed STREAMOFF retains that retired context and both queue mappings, returns a stored error on receive, and permits a later explicit flush to retry. Successful stopping allows a new context; retained old AVFrames keep their original mappings until final release. Final close clears late references to avctx/priv, and shared cleanup releases both queues only when the context is no longer referenced. Closing an fd alone is not treated as proof of stopped DMA while MMAPs retain file references.

Five final sources reconstruct exactly from the patch. Linux aarch64 GCC ASan/UBSan extracted-function tests cover both stop failures, partial initialization, error propagation, retry, late references and a real pthread QBUF/retirement barrier. macOS unnamed sem_init is unsupported, so the lifecycle harness is explicitly Linux-only. Encoder-style shared cleanup was mocked; actual encoder and other codec integration remain untested.

On temporary kernel #71, partial seek phase2 now matches all480 software frames; EOF/seek0 matches all600 frames. A separate five-phase retained-frame test completed forward/backward seeks and EOF replay; phase counts and first/last PTS/hash matched software, and all eight old-frame before/after comparisons passed. That latter test does not compare every middle frame. Real resolution changes, sustained player usage, downstream package integration and Steam CEF integration are still pending. Do not treat this isolated build as a system package replacement.

## Stateful resolution changes

`0005-stateful-resolution-change-experimental.patch` applies after 0002, 0003 and 0004. SOURCE_CHANGE keeps old capture frames through LAST, then reconfigures only CAPTURE while OUTPUT and timestamp mapping remain alive. Decoder EOS events are informational. Nonblocking DQEVENT accepts ENOENT (actual kernel behavior) and EAGAIN as an empty event queue, retries EINTR and propagates other failures before reconfiguration/EOF. Only empty ERROR non-LAST returns during pending DRC are recycled without becoming frames or EOS. Strict real-frame timestamp validation remains intact.

Visible COMPOSE is saved before Venus S_FMT overwrites crop; visible dimensions are applied after reconfiguration without changing allocated format/stride. Nonzero offsets and invalid reported rectangles fail. Reinit stop failure retains mappings; reference waits recheck predicates; callbacks detach their context reference under the queue lock before publishing the final release.

On temporary #71, 120-frame128x128→640x360 and180-frame128x128→640x360→128x128 sequences matched every software frame's visible size and YUV420P hash and reached natural EOF. Five-phase seek/EOF/held-frame regression passed phase counts and boundary PTS/hash plus eight retained-frame checks. Actual-function Linux ASan/UBSan event/reinit, crop-reset and lifecycle tests passed and were independently rerun. Earlier failed iterations and mock assumptions are recorded in VIDEO-DECODE-TRIALS.md.

This remains isolated experimental FFmpeg, not the system package or Steam CEF integration. Raw DRC inputs do not validate timestamps. DRC harness releases each frame immediately; retaining old frames while requesting reconfiguration on the same thread can still block. Multi-memory-plane reference accounting is an existing unresolved limitation (phone NV12 uses one memory plane). Other codecs/encoders, sustained player integration and arbitrary event orderings remain unvalidated.
