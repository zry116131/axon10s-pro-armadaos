/* Experimental read-only media harness: never reopen the decoder after seeking. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/imgutils.h>
#include <libavutil/md5.h>
#include <libavutil/pixdesc.h>
#include <libswscale/swscale.h>

typedef struct Harness {
    AVFormatContext *fmt;
    AVCodecContext *dec;
    AVFrame *frame, *canon;
    AVPacket *packet;
    struct SwsContext *sws;
    int video, phase, count, width, height;
} Harness;

static int report_frame(Harness *h)
{
    AVFrame *f = h->frame;
    uint8_t digest[16], *packed;
    int ret, size;
    if (f->width != h->width || f->height != h->height) {
        av_frame_unref(h->canon);
        h->canon->format = AV_PIX_FMT_YUV420P;
        h->canon->width = f->width; h->canon->height = f->height;
        if ((ret = av_frame_get_buffer(h->canon, 32)) < 0) return ret;
        h->width = f->width; h->height = f->height;
    }
    h->sws = sws_getCachedContext(h->sws, f->width, f->height, f->format,
                                f->width, f->height, AV_PIX_FMT_YUV420P,
                                SWS_POINT | SWS_BITEXACT, NULL, NULL, NULL);
    if (!h->sws) return AVERROR(ENOMEM);
    ret = sws_scale(h->sws, (const uint8_t * const *)f->data, f->linesize,
                    0, f->height, h->canon->data, h->canon->linesize);
    if (ret != f->height) return AVERROR_INVALIDDATA;
    size = av_image_get_buffer_size(AV_PIX_FMT_YUV420P, f->width, f->height, 1);
    if (size < 0) return size;
    packed = av_malloc(size);
    if (!packed) return AVERROR(ENOMEM);
    ret = av_image_copy_to_buffer(packed, size, (const uint8_t * const *)h->canon->data,
                                  h->canon->linesize, AV_PIX_FMT_YUV420P,
                                  f->width, f->height, 1);
    if (ret < 0) { av_free(packed); return ret; }
    av_md5_sum(digest, packed, ret); av_free(packed);
    printf("FRAME phase=%d index=%d pts=%" PRId64 " best_effort=%" PRId64
           " width=%d height=%d source_fmt=%s hash_fmt=yuv420p md5=",
           h->phase, h->count++, f->pts, f->best_effort_timestamp,
           f->width, f->height, av_get_pix_fmt_name(f->format));
    for (int i=0; i<16; i++) printf("%02x", digest[i]);
    puts(""); fflush(stdout);
    return 0;
}
/* 0 means input needed, 1 means requested frame limit, 2 means decoder EOF. */
static int receive_available(Harness *h, int limit)
{
    for (;;) {
        int ret = avcodec_receive_frame(h->dec, h->frame);
        if (ret == AVERROR(EAGAIN)) return 0;
        if (ret == AVERROR_EOF) return 2;
        if (ret < 0) return ret;
        ret = report_frame(h);
        av_frame_unref(h->frame); /* No hardware frame refs held over seek. */
        if (ret < 0) return ret;
        if (limit > 0 && h->count >= limit) return 1;
    }
}
static int decode_phase(Harness *h, int limit)
{
    int ret, drained;
    for (;;) {
        ret = av_read_frame(h->fmt, h->packet);
        if (ret == AVERROR_EOF) break;
        if (ret < 0) return ret;
        if (h->packet->stream_index != h->video) { av_packet_unref(h->packet); continue; }
        for (;;) {
            ret = avcodec_send_packet(h->dec, h->packet);
            if (ret != AVERROR(EAGAIN)) break;
            int before = h->count;
            drained = receive_available(h, limit);
            if (drained != 0) { av_packet_unref(h->packet); return drained; }
            if (h->count > before) continue;
            /* send/receive both EAGAIN cannot make progress under the API contract. */
            av_packet_unref(h->packet); return AVERROR_BUG;
        }
        av_packet_unref(h->packet);
        if (ret < 0) return ret;
        drained = receive_available(h, limit);
        if (drained != 0) return drained;
    }
    ret = avcodec_send_packet(h->dec, NULL);
    if (ret < 0 && ret != AVERROR_EOF) return ret;
    ret = receive_available(h, limit);
    if (ret == 0) return AVERROR_BUG; /* EAGAIN after flush is not a successful EOF. */
    return ret;
}
int main(int argc, char **argv)
{
    Harness h = {0}; const AVCodec *codec; int ret = 0, status = 1;
    int eof_mode; int64_t target; char err[AV_ERROR_MAX_STRING_SIZE];
    if (argc != 4 || (strcmp(argv[3], "partial") && strcmp(argv[3], "eof"))) {
        fprintf(stderr, "usage: %s input.mp4 decoder-name partial|eof\n", argv[0]); return 2;
    }
    eof_mode = !strcmp(argv[3], "eof");
    setvbuf(stdout, NULL, _IOLBF, 0);
    if ((ret = avformat_open_input(&h.fmt, argv[1], NULL, NULL)) < 0) goto done;
    if ((ret = avformat_find_stream_info(h.fmt, NULL)) < 0) goto done;
    h.video = av_find_best_stream(h.fmt, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (h.video < 0) {ret=h.video;goto done;}
    codec = avcodec_find_decoder_by_name(argv[2]);
    if (!codec) {ret=AVERROR_DECODER_NOT_FOUND;goto done;}
    h.dec = avcodec_alloc_context3(codec);
    if (!h.dec) {ret=AVERROR(ENOMEM);goto done;}
    if ((ret = avcodec_parameters_to_context(h.dec, h.fmt->streams[h.video]->codecpar)) < 0) goto done;
    h.dec->pkt_timebase = h.fmt->streams[h.video]->time_base;
    if ((ret = avcodec_open2(h.dec, codec, NULL)) < 0) goto done;
    printf("OPEN decoder=%s instances=1 time_base=%d/%d mode=%s\n", codec->name,
            h.dec->pkt_timebase.num,h.dec->pkt_timebase.den,argv[3]);
    h.frame=av_frame_alloc();h.canon=av_frame_alloc();h.packet=av_packet_alloc();
    if (!h.frame || !h.canon || !h.packet) {ret=AVERROR(ENOMEM);goto done;}
    h.phase=1;
    ret=decode_phase(&h,eof_mode?0:60);
    printf("PHASE_END phase=1 frames=%d result=%d instances=1\n",h.count,ret);
    if (ret != (eof_mode?2:1)) {if(ret>=0)ret=AVERROR_INVALIDDATA;goto done;}
    target = av_rescale_q(eof_mode?0:5, (AVRational){1,1}, h.dec->pkt_timebase);
    av_packet_unref(h.packet);av_frame_unref(h.frame);
    ret=av_seek_frame(h.fmt,h.video,target,AVSEEK_FLAG_BACKWARD);
    printf("SEEK target=%" PRId64 " ret=%d instances=1\n",target,ret);
    if(ret<0)goto done;
    avcodec_flush_buffers(h.dec);
    puts("FLUSH instances=1 reopen=0");
    h.phase=2;h.count=0;
    ret=decode_phase(&h,0);
    printf("PHASE_END phase=2 frames=%d result=%d instances=1\n",h.count,ret);
    if(ret==2 && h.count>0){status=0;ret=0;}
    else if(ret>=0)ret=AVERROR_INVALIDDATA;
done:
    if(ret<0){av_strerror(ret,err,sizeof(err));fprintf(stderr,"ERROR phase=%d code=%d message=%s\n",h.phase,ret,err);}
    av_packet_free(&h.packet);av_frame_free(&h.frame);av_frame_free(&h.canon);
    sws_freeContext(h.sws);avcodec_free_context(&h.dec);avformat_close_input(&h.fmt);
    fprintf(stderr,"EXIT status=%d\n",status);return status;
}
