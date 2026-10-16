# Resolution-change comparison

Build video-reconfig.c against the exact FFmpeg libraries under test, with the raw H264 demuxer/parser and H264 software/V4L2M2M decoders enabled. It uses libavformat, libavcodec, libswscale and libavutil. Use a separate candidate build; changing installed system libraries is unnecessary.

Create synthetic input with a system FFmpeg that has libx264:

```sh
ffmpeg -f lavfi -i testsrc2=size=128x128:rate=30 -frames:v 60 -c:v libx264 -threads 2 -preset ultrafast -g 30 -bf 3 -pix_fmt yuv420p -f h264 -n small.h264
ffmpeg -f lavfi -i testsrc2=size=640x360:rate=30 -frames:v 60 -c:v libx264 -threads 2 -preset ultrafast -g 30 -bf 3 -pix_fmt yuv420p -f h264 -n large.h264
cat small.h264 large.h264 > small-large.h264
ulimit -c 0
timeout -k 2 25 ./video-reconfig small-large.h264 h264 > software.log 2>&1
timeout -k 2 25 ./video-reconfig small-large.h264 h264_v4l2m2m > hardware.log 2>&1
python3 compare-video-reconfig.py software.log hardware.log
```

Run hardware decoders sequentially, never concurrently on the test device. Check process exit codes separately from frame comparison. One AVCodecContext consumes the entire file without seek/flush/reopen; each output frame is released before the next receive. Expected output is120 frames,60 of each visible resolution. Raw timestamps may be absent, so the checker uses ordered frame index, dimensions and normalized visible YUV420P MD5. This is not timestamp validation and does not exercise externally held old frames during resolution changes.

For an independent system-native comparison, install nothing if Python GI, GStreamer/GstVideo bindings and the required plugins already exist:

```sh
timeout -k 2 25 python3 video-reconfig-gstreamer.py small-large.h264 > gstreamer.log 2>&1
python3 compare-video-reconfig.py software.log gstreamer.log
```

The GStreamer pipeline explicitly selects v4l2h264dec, converts to I420, and hashes only visible rows using per-sample metadata. Errors, unsupported layout and more than240 output frames fail. This exercises that native pipeline, not Steam CEF or UI playback. See the video trial document for observed candidate results.
