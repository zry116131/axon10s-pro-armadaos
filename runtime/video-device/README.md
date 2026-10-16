# Venus decoder naming for Steam CEF

Steam's ARM64 CEF126 V4L2 backend uses `/dev/video-decN`. This phone exposes `qcom-venus-decoder` as `/dev/video1` under temporary kernel#71, while video0 is the encoder. The udev rule matches the actual driver and decoder name, not an assumed video number. It adds video-dec0 without changing the original node, ownership, access mode or sandbox policy. Existing armada membership in video grants RW access.

The rule was installed at `/etc/udev/rules.d/70-axon-venus-decoder.rules`, then rules reloaded and only the matching decoder change event triggered. After removing the manually created test alias, udev recreated it and listed it in DEVLINKS; armada RW checks passed. SHA256: `6c6ebecc8513f51135cce928a732c66464d868cc6bd3d089d2c6fa574d30e0dc`.

This does not enable unavailable hardware. Stable installed kernel#56 disables Venus and produces no matching node. Do not create a dangling alias manually on it. Steam hardware video remains disabled after rollback. The rule only applies when a matching Venus decoder node exists. Remove this exact rule and reload udev rules to roll back; remove only a verified symlink owned by this rule, never a device node.

On temporary#71, Steam's native setting was temporarily enabled, its actual gamescope-session-plus@steam user service restarted, and absence of the disable-accelerated-video-decode switch verified. CDP Media events identified V4L2VideoDecoder/platform=true for the synthetic H264 players:320x240/3s/90frames/0dropped and1280x720/20s with forward/backward seeks/579total/1dropped. Playback ended naturally; GPU processCrashCount stayed0. However, full kernel-log review found an earlier Venus firmware fatal error during Steam startup in vpx_decoder.c, followed by recovery. The later H264 successes do not make global hardware decode safe; its setting was restored to false. SystemInfo videoDecoding was empty even when real playback used V4L2, so that capability list alone is not a definitive test on this build.

The probe uses an invisible1px HTML video in the actual Steam game-mode page, cleans it up, and records per-player decoder properties. It checks the decode/playback pipeline, not full-screen presentation quality, pixel hashes or sustained game-overlay interaction. Other retained VP9 players were VpxVideoDecoder/platform=false; no claim is made that VP9/HEVC is accelerated. The system FFmpeg library was not involved or replaced.

Official Chromium126 references (Steam may carry downstream changes):
- https://chromium.googlesource.com/chromium/src/+/126.0.6478.183/media/gpu/v4l2/v4l2_device.cc
- https://chromium.googlesource.com/chromium/src/+/126.0.6478.183/media/gpu/v4l2/v4l2_video_decoder.cc
- https://chromium.googlesource.com/chromium/src/+/126.0.6478.183/content/renderer/render_thread_impl.cc
