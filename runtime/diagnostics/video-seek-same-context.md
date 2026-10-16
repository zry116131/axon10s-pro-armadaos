# Same-context seek diagnostic

Build against the exact FFmpeg candidate libraries being evaluated, including libavformat, libavcodec, libswscale and libavutil. Do not silently link the system library when evaluating a private patch. For an installed development build:

```sh
cc -O2 -Wall -Wextra -Werror video-seek-same-context.c \
  $(pkg-config --cflags --libs libavformat libavcodec libswscale libavutil) \
  -o video-seek-same-context
ulimit -c 0
timeout -k 2 25 ./video-seek-same-context synthetic.mp4 h264 partial
timeout -k 2 25 ./video-seek-same-context synthetic.mp4 h264_v4l2m2m partial
timeout -k 2 25 ./video-seek-same-context synthetic.mp4 h264 eof
timeout -k 2 25 ./video-seek-same-context synthetic.mp4 h264_v4l2m2m eof
```

Use the same synthetic 20-second, 30fps H264 fixture for all four invocations and run hardware tests sequentially. Partial mode decodes 60 frames, seeks backward to the keyframe at/before 5 seconds, flushes, then decodes to EOF. EOF mode decodes the complete input, seeks to zero and flushes. Each process opens exactly one decoder context; no close/reopen workaround is used.

Compare phase1 and phase2 ordered tuples of PTS, width, height and MD5 between software and hardware. Report timebase too. Hashes normalize this test's 8-bit420 frames to YUV420P with swscale and remove row padding. They do not prove fidelity for higher bit depth or other chroma formats. Keyframe preroll is expected; do not assume phase2 starts exactly at 5 seconds. Exit0 alone is insufficient: extra old frames, missing frames, timestamps or hash mismatches fail acceptance. Zero-frame phase2 and unexpected EAGAIN after drain are explicit errors. External timeout also covers cleanup that may block in a defective driver.

This is a diagnostic, not a seek implementation. See docs/VIDEO-DECODE-TRIALS.md for the observed failure with the experimental token/v2 build on temporary kernel #71. It does not change Steam settings or system packages.

## Retained-frame lifetime variant

Build `video-seek-lifetime.c` against the same candidate libraries. Invoke `timeout -k 2 35 ./video-seek-lifetime synthetic.mp4 h264` and then `h264_v4l2m2m` sequentially. It keeps one real cloned frame across each flush and the following phase. Sequence: initial60 frames, seek5s/45 frames, seek1s/45 frames, seek8s/to EOF, seek0/to EOF. Compare phase counts, first/last PTS and hashes with software, and require every HELD comparison to match. The external AVCodecContext is unchanged even when the candidate internally recreates a hardware session. This test checks retained-frame integrity and boundary summaries; it does not hash every middle frame for comparison.
