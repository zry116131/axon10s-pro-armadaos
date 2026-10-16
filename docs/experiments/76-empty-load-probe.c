#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    unsigned int codec;
    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    if (argc != 2 || (strcmp(argv[1], "vp8") && strcmp(argv[1], "h264"))) {
        fprintf(stderr, "usage: empty-load vp8|h264\n"); return 2;
    }
    codec = !strcmp(argv[1], "vp8") ? V4L2_PIX_FMT_VP8 : V4L2_PIX_FMT_H264;
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
    printf("driver=%.16s card=%.32s\n", cap.driver, cap.card);
    fmt.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    fmt.fmt.pix_mp.width = 320;
    fmt.fmt.pix_mp.height = 240;
    fmt.fmt.pix_mp.pixelformat = codec;
    fmt.fmt.pix_mp.field = V4L2_FIELD_NONE;
    if (ioctl(fd, VIDIOC_S_FMT, &fmt) < 0) { perror("S_FMT"); goto done; }
    if (fmt.fmt.pix_mp.pixelformat != codec) {
        fprintf(stderr, "unexpected format\n"); goto done;
    }
    printf("OUTPUT format=%#x width=%u height=%u size=%u planes=%u colorspace=%u\n",
           fmt.fmt.pix_mp.pixelformat, fmt.fmt.pix_mp.width, fmt.fmt.pix_mp.height,
           fmt.fmt.pix_mp.plane_fmt[0].sizeimage, fmt.fmt.pix_mp.num_planes,
           fmt.fmt.pix_mp.colorspace);
    memset(&fmt, 0, sizeof(fmt));
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    fmt.fmt.pix_mp.width = 320;
    fmt.fmt.pix_mp.height = 240;
    fmt.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_NV12;
    fmt.fmt.pix_mp.field = V4L2_FIELD_NONE;
    if (ioctl(fd, VIDIOC_S_FMT, &fmt) < 0) { perror("S_FMT capture"); goto done; }
    if (fmt.fmt.pix_mp.pixelformat != V4L2_PIX_FMT_NV12) {
        fprintf(stderr, "unexpected capture format\n"); goto done;
    }
    printf("CAPTURE width=%u height=%u size=%u planes=%u colorspace=%u\n",
           fmt.fmt.pix_mp.width, fmt.fmt.pix_mp.height,
           fmt.fmt.pix_mp.plane_fmt[0].sizeimage, fmt.fmt.pix_mp.num_planes,
           fmt.fmt.pix_mp.colorspace);
    req.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    req.memory = V4L2_MEMORY_MMAP;
    req.count = 1;
    if (ioctl(fd, VIDIOC_REQBUFS, &req) < 0) { perror("REQBUFS"); goto done; }
    printf("session initialized: allocated=%u, no QBUF; will STREAMON empty queue\n", req.count);
    fflush(stdout);
    if (ioctl(fd, VIDIOC_STREAMON, &type) < 0) { perror("STREAMON empty"); goto done; }
    puts("STREAMON succeeded with zero QBUF/ETB");
    fflush(stdout);
    if (ioctl(fd, VIDIOC_STREAMOFF, &type) < 0) { perror("STREAMOFF"); goto done; }
    req.count = 0;
    if (ioctl(fd, VIDIOC_REQBUFS, &req) < 0) { perror("REQBUFS release"); goto done; }
    result = 0;
done:
    if (close(fd) < 0) { perror("close"); result = 1; }
    return result;
}
