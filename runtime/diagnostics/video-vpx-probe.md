# VPx first-frame and drain diagnostic

Requires existing Python GI/GStreamer video bindings, explicit v4l2vp8dec/v4l2vp9dec, and a temporary validated Venus-enabled kernel. Stable kernel#56 has no decoder. Do not enable Steam hardware video for these isolated tests.

Create two synthetic references with system FFmpeg/libvpx:

```sh
ffmpeg -v error -f lavfi -i testsrc2=size=320x240:rate=30 -frames:v 60 -c:v libvpx -threads 2 -deadline realtime -cpu-used 6 -b:v 700k -g 30 -pix_fmt yuv420p -an -n vp8.webm
ffmpeg -v error -f lavfi -i testsrc2=size=320x240:rate=30 -frames:v 60 -c:v libvpx-vp9 -threads 2 -deadline realtime -cpu-used 6 -b:v 700k -g 30 -profile:v 0 -pix_fmt yuv420p -an -n vp9-p0.webm
ffmpeg -v error -i vp8.webm -map 0:v:0 -pix_fmt yuv420p -f framemd5 -n vp8.software.md5
ffmpeg -v error -i vp9-p0.webm -map 0:v:0 -pix_fmt yuv420p -f framemd5 -n vp9.software.md5
ulimit -c 0
timeout -k 2 25 python3 video-vpx-probe.py vp8.webm vp8 stop > vp8-stop.log 2>&1
# Check the process exit code, then compare reported frames:
python3 compare-video-vpx.py vp8.software.md5 vp8-stop.log stop
```

Use vp9 with its corresponding fixture/reference. Stop requests pipeline shutdown after30 reported frames; input is throttled, but asynchronous teardown may decode additional frames, so30 is not a hardware submission limit. Drain mode requires60 frames and actual EOS. The probe logs sink input buffer count/EOS with monotonic time to distinguish EOF from pipeline-error EOS. Its cleanup checks NULL transition status; external timeout is still required for blocked ioctls/driver shutdown.

Run one hardware decoder at a time. If a firmware SFR occurs, save kernel and application logs and verify recovery before another trial. Do not proceed to drain/concurrency runs when first-frame decode already fails. See VIDEO-DECODE-TRIALS.md: both#71 and input-size-only#72 failed first-frame VP8/VP9, and#72 is not an accepted repair. Visible MD5 comparison does not cover timing or physical display output.
