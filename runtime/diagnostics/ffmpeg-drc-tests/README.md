# Linux extracted-function regression tests

Apply experimental FFmpeg patches0002,0003,0004,0005 in order to upstream8.1.3 (do not apply rejected0001). Copy these three scripts and the resulting libavcodec/v4l2_m2m.h, v4l2_m2m.c, v4l2_m2m_dec.c, v4l2_context.c, v4l2_buffers.c into a disposable directory. Run python3 test-control.py, python3 test-visible.py and python3 test-lifecycle.py there on Linux with GCC and ASan/UBSan. The scripts generate test C files and executables beside themselves.

These extract candidate functions with controlled V4L2/FFmpeg dependencies and real pthread/semaphore primitives. They verify control flow and resource lifetime, not FFmpeg ABI or hardware compatibility. Hardware results and limitations are separately recorded in docs/VIDEO-DECODE-TRIALS.md. macOS unnamed semaphores are unsupported; use Linux.
