#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(void)
{
    int fd = open("/dev/video-dec0", O_RDWR | O_NONBLOCK | O_CLOEXEC);
    int result = 1;
    struct v4l2_capability cap = {0};
    struct v4l2_format fmt = {0};
    struct v4l2_requestbuffers req = {0};
    if (fd < 0) { perror("open"); return 1; }
    if (ioctl(fd, VIDIOC_QUERYCAP, &cap) < 0) { perror("QUERYCAP"); goto done; }
    if (strncmp((const char *)cap.driver, "qcom-venus", sizeof(cap.driver))) {
        fprintf(stderr, "unexpected driver\n"); goto done;
    }
    fmt.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    fmt.fmt.pix_mp.width = 320;
    fmt.fmt.pix_mp.height = 240;
    fmt.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_VP8;
    fmt.fmt.pix_mp.field = V4L2_FIELD_NONE;
    if (ioctl(fd, VIDIOC_S_FMT, &fmt) < 0) { perror("S_FMT"); goto done; }
    if (fmt.fmt.pix_mp.pixelformat != V4L2_PIX_FMT_VP8) {
        fprintf(stderr, "unexpected format\n"); goto done;
    }
    req.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    req.memory = V4L2_MEMORY_MMAP;
    req.count = 1;
    if (ioctl(fd, VIDIOC_REQBUFS, &req) < 0) { perror("REQBUFS"); goto done; }
    printf("session initialized: allocated=%u, no QBUF/STREAMON\n", req.count);
    req.count = 0;
    if (ioctl(fd, VIDIOC_REQBUFS, &req) < 0) { perror("REQBUFS release"); goto done; }
    result = 0;
done:
    if (close(fd) < 0) { perror("close"); result = 1; }
    return result;
}
