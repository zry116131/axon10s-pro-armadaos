from pathlib import Path
import subprocess
import sys
if sys.platform != "linux":
 raise SystemExit("Run this harness on Linux: macOS unnamed sem_init returns ENOSYS; no semaphore mock is used.")
p=Path(__file__).resolve().parent
def func(file,signature):
 s=(p/file).read_text();a=s.index(signature);i=s.index('{',a)+1;depth=1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
prefix=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdatomic.h>
#include <pthread.h>
#include <semaphore.h>
#include <errno.h>
#include <stddef.h>
#include <time.h>
#define av_cold
#define AV_LOG_ERROR 1
#define VIDIOC_STREAMOFF 0
#define VIDIOC_STREAMON 1
#define AVERROR(x) (-(x))
#define AVERROR_EOF (-1234)
#define V4L2_TYPE_IS_OUTPUT(t) ((t)==1)
#define V4L2BUF_AVAILABLE 0
#define av_log(...) ((void)0)
#define AVMutex pthread_mutex_t
#define ff_mutex_init pthread_mutex_init
#define ff_mutex_lock pthread_mutex_lock
#define ff_mutex_unlock pthread_mutex_unlock
#define ff_mutex_destroy pthread_mutex_destroy
#define av_err2str(e) "test-error"
typedef struct V4L2m2mContext V4L2m2mContext;
typedef struct AVCodecContext {void*priv_data;} AVCodecContext;
typedef struct AVPacket {int size;} AVPacket;
typedef struct AVFrame {int placeholder;} AVFrame;
typedef struct V4L2Context {int type,streamon,num_buffers;const char*name;void*buffers;} V4L2Context;
struct V4L2m2mContext {int fd;AVCodecContext*avctx;V4L2Context output,capture;V4L2m2mContext*self_ref;atomic_uint refcount;int reinit,draining,drc_ready,drc_error;sem_t refsync;AVMutex queue_lock;int queue_lock_initialized,refsync_initialized,retired;void*priv;AVFrame*frame;AVPacket buf_pkt;};
typedef struct V4L2m2mPriv {V4L2m2mContext*context;int num_capture_buffers,num_output_buffers,flush_error;} V4L2m2mPriv;
typedef struct V4L2Buffer {V4L2Context*context;atomic_uint context_refcount;const V4L2m2mContext*context_ref;int status;} V4L2Buffer;
typedef void* AVRefStructOpaque;
static V4L2m2mContext*ctx_to_m2mctx(V4L2Context*c){return (void*)((char*)c-(c->type==1?offsetof(V4L2m2mContext,output):offsetof(V4L2m2mContext,capture)));}
#define buf_to_m2mctx(b) ctx_to_m2mctx((b)->context)
static int fail_stop_type,stop_calls[3],releases,destroys,closed,init_stage;
static int frame_alloc_fail, inject_event_error;
static atomic_int qbufs,retire_done;
struct RefHeader{atomic_int refs;void(*destroy)(AVRefStructOpaque,void*);};
static void*av_refstruct_alloc_ext(size_t n,int flags,void*unused,void(*destroy)(AVRefStructOpaque,void*)){
 struct RefHeader*h=calloc(1,sizeof(*h)+n);assert(h);atomic_init(&h->refs,1);h->destroy=destroy;return h+1;
}
static struct RefHeader*header(void*p){return ((struct RefHeader*)p)-1;}
static V4L2m2mContext*hold(V4L2m2mContext*s){atomic_fetch_add(&header(s)->refs,1);return s;}
static void av_refstruct_unref(void*p){
 V4L2m2mContext*s,*null_ref=NULL;memcpy(&s,p,sizeof(s));memcpy(p,&null_ref,sizeof(null_ref));if(!s)return;struct RefHeader*h=header(s);
 if(atomic_fetch_sub(&h->refs,1)==1){h->destroy(NULL,s);destroys++;free(h);}
}
static AVFrame*av_frame_alloc(void){return frame_alloc_fail?NULL:calloc(1,sizeof(AVFrame));}
static void av_frame_free(AVFrame**p){free(*p);*p=NULL;}
static void av_packet_unref(AVPacket*p){p->size=0;}
static void ff_v4l2_context_release(V4L2Context*c){if(c->buffers){releases++;free(c->buffers);c->buffers=NULL;}}
static int test_close(int fd){assert(fd>=0);closed++;return 0;}
#define close test_close
static int ioctl(int fd,int cmd,int*t){assert(fd>=0);if(cmd==VIDIOC_STREAMOFF){stop_calls[*t]++;if(fail_stop_type==*t){errno=EIO;return -1;}}return 0;}
static pthread_mutex_t qlock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t qcond=PTHREAD_COND_INITIALIZER;
static int block_qbuf,qentered,qrelease;
static int ff_v4l2_buffer_enqueue(V4L2Buffer*b){
 assert(!buf_to_m2mctx(b)->retired);atomic_fetch_add(&qbufs,1);
 pthread_mutex_lock(&qlock);if(block_qbuf){qentered=1;pthread_cond_broadcast(&qcond);while(!qrelease)pthread_cond_wait(&qcond,&qlock);}pthread_mutex_unlock(&qlock);return 0;
}
static int v4l2_decode_init(AVCodecContext*);
static int v4l2_finish_drc(AVCodecContext*a){assert(0);return 0;}
static int ff_decode_get_packet(AVCodecContext*a,AVPacket*p){return AVERROR_EOF;}
static int ff_v4l2_context_dequeue_frame(V4L2Context*c,AVFrame*f,int t){return AVERROR_EOF;}
static int ff_v4l2_context_enqueue_packet(V4L2Context*c,AVPacket*p){if(inject_event_error){V4L2m2mContext*s=ctx_to_m2mctx(c);s->drc_ready=1;s->drc_error=-EIO;return 0;}return AVERROR_EOF;}
static int v4l2_try_start(AVCodecContext*a){return AVERROR_EOF;}
static int64_t av_gettime_relative(void){return 0;}
static int av_usleep(unsigned n){return 0;}
'''
functions='\n'.join(func(f,s) for f,s in [
 ('v4l2_context.c','int ff_v4l2_context_set_status('),
 ('v4l2_m2m.c','static void v4l2_m2m_destroy_context('),
 ('v4l2_m2m.c','int ff_v4l2_m2m_codec_retire('),
 ('v4l2_m2m.c','av_cold int ff_v4l2_m2m_codec_end('),
 ('v4l2_m2m.c','int ff_v4l2_m2m_create_context('),
 ('v4l2_buffers.c','static void v4l2_free_buffer('),
 ('v4l2_m2m_dec.c','static int v4l2_receive_frame('),
 ('v4l2_m2m_dec.c','static void v4l2_decode_flush('),
 ('v4l2_m2m_dec.c','static av_cold int v4l2_decode_close(')])
main=r'''
static int v4l2_decode_init(AVCodecContext*a){
 V4L2m2mPriv*p=a->priv_data;V4L2m2mContext*s;int r;
 if(init_stage==1)return AVERROR(ENOMEM);
 r=ff_v4l2_m2m_create_context(p,&s);if(r<0)return r;
 s->avctx=a;s->output.type=1;s->capture.type=2;
 if(init_stage==2)return AVERROR(EIO);
 s->fd=100;s->output.buffers=malloc(1);s->capture.buffers=malloc(1);
 if(init_stage==3)return AVERROR(EIO);
 return 0;
}
static V4L2Buffer held_frame(V4L2m2mContext*s){
 atomic_fetch_add(&s->refcount,1);
 return (V4L2Buffer){&s->capture,1,hold(s),0};
}
static void live(V4L2m2mContext*s){s->output.streamon=s->capture.streamon=1;s->buf_pkt.size=7;}
static void*callback_thread(void*p){v4l2_free_buffer(p,NULL);return NULL;}
static void*retire_thread(void*p){int r=ff_v4l2_m2m_codec_retire(p);assert(!r);atomic_store(&retire_done,1);return NULL;}
int main(void){
 V4L2m2mPriv p={0};AVCodecContext a={&p};AVFrame frame={0};
 /* Fail either STREAMOFF: preserve context/mappings and explicit receive error.
    Retry stops only the queue which failed, then rebuilds under same AVctx. */
 for(int type=1;type<=2;type++){
  assert(!v4l2_decode_init(&a));V4L2m2mContext*old=p.context;live(old);V4L2Buffer held=held_frame(old);
  int before=releases;fail_stop_type=type;v4l2_decode_flush(&a);
  assert(p.context==old&&p.flush_error==-EIO&&old->retired&&old->buf_pkt.size==0&&releases==before);
  assert(v4l2_receive_frame(&a,&frame)==-EIO);
  int qbefore=atomic_load(&qbufs);v4l2_free_buffer(&held,NULL);assert(atomic_load(&qbufs)==qbefore);
  fail_stop_type=0;v4l2_decode_flush(&a);assert(!p.flush_error&&p.context&&p.context->avctx==&a);
  assert(releases==before+2);v4l2_decode_close(&a);assert(!p.context);
 }
 /* Partial init failure (before allocate, after context, after queue setup),
    error propagation without dereferencing NULL, later successful flush. */
 for(int stage=1;stage<=3;stage++){
  init_stage=stage;v4l2_decode_flush(&a);assert(p.flush_error<0&&!p.context);
  assert(v4l2_receive_frame(&a,&frame)==p.flush_error);
  v4l2_decode_close(&a);init_stage=0;v4l2_decode_flush(&a);assert(!p.flush_error&&p.context);v4l2_decode_close(&a);
 }
 frame_alloc_fail=1;v4l2_decode_flush(&a);assert(p.flush_error==-ENOMEM&&!p.context);frame_alloc_fail=0;
 v4l2_decode_flush(&a);assert(!p.flush_error);v4l2_decode_close(&a);
 /* Old frame survives successful flush and new session lifetime. */
 assert(!v4l2_decode_init(&a));V4L2m2mContext*old=p.context;live(old);V4L2Buffer h=held_frame(old);
 int before=releases,d_before=destroys;v4l2_decode_flush(&a);
 assert(!p.flush_error&&p.context!=old&&old->retired&&!old->avctx&&!old->priv);
 assert(old->capture.buffers&&old->output.buffers&&releases==before&&destroys==d_before);
 v4l2_decode_close(&a);assert(releases==before+2);v4l2_free_buffer(&h,NULL);assert(releases==before+4);
 /* Final close after failed stop: frame owns all old resources; late callback
    cannot use dead avctx/priv or queue, final unref is exactly-once cleanup. */
 assert(!v4l2_decode_init(&a));old=p.context;live(old);h=held_frame(old);before=releases;
 fail_stop_type=2;v4l2_decode_flush(&a);v4l2_decode_close(&a);assert(!p.context&&!old->avctx&&!old->priv&&releases==before);
 int qb=atomic_load(&qbufs);v4l2_free_buffer(&h,NULL);assert(atomic_load(&qbufs)==qb&&releases==before+2);fail_stop_type=0;
 /* Concurrent callback paused INSIDE QBUF: retirement must wait until it
    completes, then every subsequent callback is forbidden to QBUF. */
 assert(!v4l2_decode_init(&a));old=p.context;live(old);V4L2Buffer h1=held_frame(old),h2=held_frame(old);
 block_qbuf=1;qentered=qrelease=0;atomic_store(&retire_done,0);pthread_t t1,t2;
 pthread_create(&t1,NULL,callback_thread,&h1);
 pthread_mutex_lock(&qlock);while(!qentered)pthread_cond_wait(&qcond,&qlock);pthread_mutex_unlock(&qlock);
 pthread_create(&t2,NULL,retire_thread,old);
 struct timespec delay={0,20000000};nanosleep(&delay,NULL);assert(!atomic_load(&retire_done));
 pthread_mutex_lock(&qlock);qrelease=1;pthread_cond_broadcast(&qcond);pthread_mutex_unlock(&qlock);
 pthread_join(t1,NULL);pthread_join(t2,NULL);assert(old->retired&&atomic_load(&retire_done));
 qb=atomic_load(&qbufs);pthread_create(&t1,NULL,callback_thread,&h2);pthread_join(t1,NULL);assert(atomic_load(&qbufs)==qb);
 block_qbuf=0;v4l2_decode_close(&a);
 /* Event error discovered while reclaiming OUTPUT must win over ready DRC. */
 assert(!v4l2_decode_init(&a));p.flush_error=0;inject_event_error=1;
 assert(v4l2_receive_frame(&a,&frame)==-EIO);assert(p.context->drc_ready);
 inject_event_error=0;v4l2_decode_close(&a);
 /* Encoder-compatible ownership: no decoder flush required, ordinary close
    retires callback and safely defers its retained frame, same shared helpers. */
 assert(!v4l2_decode_init(&a));old=p.context;live(old);h=held_frame(old);h.context=&old->output;
 before=releases;ff_v4l2_m2m_codec_end(&p);assert(releases==before);v4l2_free_buffer(&h,NULL);assert(releases==before+2);
 puts("PASS: extracted lifecycle functions; both STREAMOFF failures preserve mappings; partial init/allocate failure/retry/close/error propagation; held-frame delayed cleanup; real pthread QBUF-retirement barrier; encoder-style late output reference");
}
'''
(p/'test-lifecycle.c').write_text(prefix+functions+main)
subprocess.run(['cc','-std=c11','-O1','-g','-pthread','-Werror=discarded-qualifiers','-Werror=incompatible-pointer-types','-fsanitize=address,undefined',str(p/'test-lifecycle.c'),'-o',str(p/'test-lifecycle')],check=True)
r=subprocess.run([str(p/'test-lifecycle')],capture_output=True,text=True,timeout=20)
(p/'test-lifecycle.log').write_text(r.stdout+r.stderr);print(r.stdout);print(r.stderr, end="");r.check_returncode()
