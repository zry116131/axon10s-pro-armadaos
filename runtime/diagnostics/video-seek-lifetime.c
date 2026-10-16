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
    AVFrame *last;
    int64_t first_pts, last_pts;
    char first_hash[33], last_hash[33];
} Harness;

static int hash_image(Harness *h, AVFrame *f, char hex[33])
{
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
    for (int i=0; i<16; i++) snprintf(hex + i*2, 3, "%02x", digest[i]);

    return 0;
}
static int report_frame(Harness *h)
{
    int ret = hash_image(h, h->frame, h->last_hash);
    if (ret < 0) return ret;
    if (!h->count) {
        h->first_pts = h->frame->pts;
        memcpy(h->first_hash, h->last_hash, 33);
    }
    h->last_pts = h->frame->pts;
    h->count++;
    av_frame_free(&h->last);
    h->last = av_frame_clone(h->frame);
    if (!h->last) return AVERROR(ENOMEM);
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
        av_frame_unref(h->frame); /* Drop the working ref; last/held clones intentionally survive seek. */
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
    Harness h = {0}; const AVCodec *codec;
    AVFrame *held = NULL;
    /* Frame limits: last two phases drain to actual EOF. */
    const int limits[] = {60, 45, 45, 0, 0};
    const int targets[] = {-1, 5, 1, 8, 0};
    char err[AV_ERROR_MAX_STRING_SIZE], held_before[33], held_after[33];
    int ret=0, status=1;
    if (argc!=3) {
        fprintf(stderr,"usage: %s input.mp4 decoder-name\n",argv[0]);return 2;
    }
    setvbuf(stdout,NULL,_IOLBF,0);
    if((ret=avformat_open_input(&h.fmt,argv[1],NULL,NULL))<0)goto done;
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
    printf("OPEN decoder=%s instances=1 context=%p time_base=%d/%d\n",codec->name,
            (void*)h.dec,h.dec->pkt_timebase.num,h.dec->pkt_timebase.den);
    h.frame=av_frame_alloc();h.canon=av_frame_alloc();h.packet=av_packet_alloc();
    if(!h.frame||!h.canon||!h.packet){ret=AVERROR(ENOMEM);goto done;}
    for(int phase=0;phase<5;phase++) {
        h.phase=phase+1;
        if(phase) {
            /* Keep exactly one cloned decoder frame alive across flush AND
             * the next decode phase. No copy replaces its AVBufferRefs. */
            held=h.last;h.last=NULL;
            if(!held){ret=AVERROR_INVALIDDATA;goto done;}
            if((ret=hash_image(&h,held,held_before))<0)goto done;
            printf("HELD phase=%d step=before_flush pts=%" PRId64 " md5=%s\n",
                    h.phase,held->pts,held_before);
            int64_t target=av_rescale_q(targets[phase],(AVRational){1,1},h.dec->pkt_timebase);
            av_packet_unref(h.packet);av_frame_unref(h.frame);
            if((ret=av_seek_frame(h.fmt,h.video,target,AVSEEK_FLAG_BACKWARD))<0)goto done;
            printf("FLUSH_BEGIN phase=%d target_sec=%d instances=1 context=%p held_refs=1\n",
                    h.phase,targets[phase],(void*)h.dec);
            avcodec_flush_buffers(h.dec);
            if((ret=hash_image(&h,held,held_after))<0)goto done;
            printf("HELD phase=%d step=after_flush md5=%s match=%d\n",h.phase,
                    held_after,!strcmp(held_before,held_after));
            if(strcmp(held_before,held_after)){ret=AVERROR_INVALIDDATA;goto done;}
        }
        h.count=0;h.first_hash[0]=h.last_hash[0]=0;
        ret=decode_phase(&h,limits[phase]);
        printf("PHASE_END phase=%d target_sec=%d frames=%d result=%d first_pts=%" PRId64
               " last_pts=%" PRId64 " first_md5=%s last_md5=%s instances=1 context=%p\n",
                h.phase,targets[phase],h.count,ret,h.first_pts,h.last_pts,
                h.first_hash,h.last_hash,(void*)h.dec);
        if(ret!=(limits[phase]?1:2)||!h.count){if(ret>=0)ret=AVERROR_INVALIDDATA;goto done;}
        if(held) {
            if((ret=hash_image(&h,held,held_after))<0)goto done;
            printf("HELD phase=%d step=after_decode md5=%s match=%d\n",h.phase,
                    held_after,!strcmp(held_before,held_after));
            if(strcmp(held_before,held_after)){ret=AVERROR_INVALIDDATA;goto done;}
            av_frame_free(&held);
            printf("HELD_RELEASE phase=%d\n",h.phase);
        }
    }
    status=0;ret=0;
done:
    if(ret<0){av_strerror(ret,err,sizeof(err));fprintf(stderr,"ERROR phase=%d code=%d message=%s\n",h.phase,ret,err);}
    av_packet_free(&h.packet);av_frame_free(&h.frame);av_frame_free(&held);av_frame_free(&h.last);
    av_frame_free(&h.canon);sws_freeContext(h.sws);
    avcodec_free_context(&h.dec);avformat_close_input(&h.fmt);
    fprintf(stderr,"EXIT status=%d decoder_instances_max=1\n",status);return status;
}
