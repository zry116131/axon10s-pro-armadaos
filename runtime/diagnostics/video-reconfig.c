/* Single-context Annex B reconfiguration test: no seek, flush or retained frame. */
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
        av_frame_unref(h->frame); /* Release before any next receive/reconfiguration; no retained clone. */
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
    Harness h={0}; const AVCodec *codec; const AVInputFormat *input;
    int ret=0,status=1; char err[AV_ERROR_MAX_STRING_SIZE];
    if(argc!=3){fprintf(stderr,"usage: %s concatenated.h264 decoder-name\n",argv[0]);return 2;}
    setvbuf(stdout,NULL,_IOLBF,0);
    input=av_find_input_format("h264");
    if(!input){ret=AVERROR_DEMUXER_NOT_FOUND;goto done;}
    if((ret=avformat_open_input(&h.fmt,argv[1],input,NULL))<0)goto done;
    if((ret=avformat_find_stream_info(h.fmt,NULL))<0)goto done;
    h.video=av_find_best_stream(h.fmt,AVMEDIA_TYPE_VIDEO,-1,-1,NULL,0);
    if(h.video<0){ret=h.video;goto done;}
    codec=avcodec_find_decoder_by_name(argv[2]);
    if(!codec){ret=AVERROR_DECODER_NOT_FOUND;goto done;}
    h.dec=avcodec_alloc_context3(codec);
    if(!h.dec){ret=AVERROR(ENOMEM);goto done;}
    if((ret=avcodec_parameters_to_context(h.dec,h.fmt->streams[h.video]->codecpar))<0)goto done;
    h.dec->pkt_timebase=h.fmt->streams[h.video]->time_base;
    if((ret=avcodec_open2(h.dec,codec,NULL))<0)goto done;
    printf("OPEN decoder=%s instances=1 context=%p demux=h264 time_base=%d/%d flushes=0 reopens=0\n",
            codec->name,(void*)h.dec,h.dec->pkt_timebase.num,h.dec->pkt_timebase.den);
    h.frame=av_frame_alloc();h.canon=av_frame_alloc();h.packet=av_packet_alloc();
    if(!h.frame||!h.canon||!h.packet){ret=AVERROR(ENOMEM);goto done;}
    h.phase=1;
    ret=decode_phase(&h,0);
    printf("DECODE_END frames=%d result=%d decoder_instances=1 flushes=0 reopens=0\n",h.count,ret);
    if(ret==2&&h.count>0){status=0;ret=0;}
    else if(ret>=0)ret=AVERROR_INVALIDDATA;
done:
    if(ret<0){av_strerror(ret,err,sizeof(err));fprintf(stderr,"ERROR frames=%d code=%d message=%s\n",h.count,ret,err);}
    av_packet_free(&h.packet);av_frame_free(&h.frame);av_frame_free(&h.canon);
    sws_freeContext(h.sws);avcodec_free_context(&h.dec);avformat_close_input(&h.fmt);
    fprintf(stderr,"EXIT status=%d frames=%d\n",status,h.count);return status;
}
