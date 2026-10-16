from pathlib import Path
import subprocess,sys
p=Path(__file__).resolve().parent
if sys.platform!='linux': raise SystemExit('Run on Linux for actual POSIX semaphores')
def func(n,sig):
 s=(p/n).read_text();a=s.index(sig);b=s.index('{',a)+1;d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
s=(p/'v4l2_context.c').read_text();a=s.index('        if (av_codec_is_decoder(ctx_to_m2mctx(ctx)->avctx->codec) &&');b=s.index('\n        if (ctx_to_m2mctx(ctx)->draining',a);last=s[a:b]
pre=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#define AVERROR(e) (-(e))
#define AV_LOG_ERROR 0
#define VIDIOC_DQEVENT 1
#define VIDIOC_STREAMOFF 2
#define V4L2_EVENT_EOS 2
#define V4L2_EVENT_SOURCE_CHANGE 5
#define V4L2_EVENT_SRC_CH_RESOLUTION 1
#define V4L2_BUF_FLAG_LAST 16
#define V4L2_BUF_FLAG_ERROR 64
#define V4L2BUF_AVAILABLE 0
#define V4L2_TYPE_IS_OUTPUT(t) ((t)==1)
#define V4L2_TYPE_IS_MULTIPLANAR(t) ((t)==2)
#define av_log(...) ((void)0)
#define logger(c) NULL
#define ff_mutex_lock pthread_mutex_lock
#define ff_mutex_unlock pthread_mutex_unlock
struct V4L2m2mContext;
typedef struct { int status; } Buffer;
typedef struct {struct V4L2m2mContext*s;int done,streamon,type;Buffer*buffers;const char*name;} V4L2Context;
typedef struct {int codec;} AVCodecContext;
typedef struct V4L2m2mContext {V4L2Context capture;AVCodecContext*avctx;int fd,source_change_seen,drc_pending,drc_ready,drc_error,reinit,draining;pthread_mutex_t queue_lock;sem_t refsync;atomic_uint refcount;} V4L2m2mContext;
#define ctx_to_m2mctx(c) ((c)->s)
#define av_codec_is_decoder(c) (c)
struct v4l2_event {int type;union {struct {int changes;} src_change;} u;};
static struct v4l2_event next_event;
static int events_left=1,eos_first,interrupt_once,terminal_errno=ENOENT;
static int ioctl(int fd,int op,void*p){assert(op==VIDIOC_DQEVENT);if(interrupt_once){interrupt_once=0;errno=EINTR;return -1;}if(!events_left){errno=terminal_errno;return -1;}events_left--;*(struct v4l2_event*)p=next_event;if(eos_first){((struct v4l2_event*)p)->type=V4L2_EVENT_EOS;eos_first=0;}return 0;}
static int stop_fail;
static atomic_int released,finished;
static int ff_v4l2_context_set_status(V4L2Context*c,int cmd){assert(cmd==VIDIOC_STREAMOFF);if(stop_fail)return -EIO;c->streamon=0;return 0;}
static void ff_v4l2_context_release(V4L2Context*c){atomic_fetch_add(&released,1);}
static int ff_v4l2_context_get_format(V4L2Context*c,int n){return 0;}
static int ff_v4l2_context_set_format(V4L2Context*c){return 0;}
struct plane{int bytesused;};
struct v4l2_buffer {int type,flags,bytesused,index;union {struct plane*planes;} m;};
'''
code=pre+func('v4l2_context.c','static int v4l2_handle_event(')+'\n'+func('v4l2_m2m.c','int ff_v4l2_m2m_codec_reinit(')
# Extract the actual caller's POLLPRI error/ready ordering and public frame API.
event_start=s.index('    /* 1. handle resolution changes */')
event_end=s.index('    /* 2. dequeue the buffer */',event_start)
caller=s[event_start:event_end]
code+='\n#define POLLPRI 1\n#define AVERROR_EOF (-1234)\ntypedef Buffer V4L2Buffer;\ntypedef struct {int unused;} AVFrame;\n'
code+='static void *dispatch_event(V4L2Context *ctx) { int ret; struct {int revents;} pfd={POLLPRI};\n'+caller+'return ctx;\n}\n'
code+='static V4L2Buffer *v4l2_dequeue_v4l2buf(V4L2Context*c,int timeout){dispatch_event(c);return NULL;}\n'
code+='static int ff_v4l2_buffer_buf_to_avframe(AVFrame*f,V4L2Buffer*b){return 0;}\n'
code+=func('v4l2_context.c','int ff_v4l2_context_dequeue_frame(')
code+='\nstatic void *last_boundary(V4L2Context *ctx, struct v4l2_buffer buf) {\n'+last+'\nreturn ctx;\nstart: return (void*)1;\n}\n'
code+=r'''
static void*run_reinit(void*p){assert(!ff_v4l2_m2m_codec_reinit(p));atomic_store(&finished,1);return NULL;}
int main(void){
 V4L2m2mContext s={0};AVCodecContext a={1};Buffer bs[1]={{0}};s.avctx=&a;s.capture=(V4L2Context){&s,0,1,2,bs,"capture"};
 pthread_mutex_init(&s.queue_lock,NULL);assert(!sem_init(&s.refsync,0,0));atomic_init(&s.refcount,0);
 next_event=(struct v4l2_event){V4L2_EVENT_EOS};assert(!v4l2_handle_event(&s.capture));assert(!s.capture.done);
 next_event=(struct v4l2_event){V4L2_EVENT_SOURCE_CHANGE};next_event.u.src_change.changes=1;events_left=2;eos_first=1;s.source_change_seen=1;
 assert(!v4l2_handle_event(&s.capture));assert(s.drc_pending&&!s.drc_ready);assert(s.capture.streamon);
 struct plane pl={100};struct v4l2_buffer b={2,V4L2_BUF_FLAG_LAST,0,0,{&pl}};
 assert(last_boundary(&s.capture,b)==&s.capture);assert(s.drc_ready&&!s.capture.done&&s.reinit); /* nonempty LAST remains deliverable */
 s.drc_ready=s.reinit=0;pl.bytesused=0;
 b.flags=V4L2_BUF_FLAG_ERROR;bs[0].status=9;
 assert(last_boundary(&s.capture,b)==(void*)1);
 assert(bs[0].status==V4L2BUF_AVAILABLE&&!s.drc_ready&&!s.capture.done);
 b.flags=0;assert(last_boundary(&s.capture,b)==&s.capture); /* strict non-error path */
 b.flags=V4L2_BUF_FLAG_ERROR;s.drc_pending=0;assert(last_boundary(&s.capture,b)==&s.capture);
 s.drc_pending=1;b.flags=V4L2_BUF_FLAG_LAST|V4L2_BUF_FLAG_ERROR;
assert(!last_boundary(&s.capture,b));assert(s.drc_ready&&!s.capture.done);
 s.drc_pending=s.drc_ready=s.reinit=0;pl.bytesused=100;assert(last_boundary(&s.capture,b)==&s.capture);assert(s.capture.done&&!s.drc_ready);
 s.capture.done=0;s.source_change_seen=0;events_left=1;s.reinit=0;assert(!v4l2_handle_event(&s.capture));assert(s.drc_ready);s.capture.buffers=NULL;events_left=1;s.drc_ready=0;assert(!v4l2_handle_event(&s.capture));assert(s.drc_ready);s.capture.buffers=bs;
 stop_fail=1;assert(ff_v4l2_m2m_codec_reinit(&s)==-EIO);assert(!atomic_load(&released)&&s.capture.buffers==bs&&s.reinit);stop_fail=0;
 /* A stale post must not satisfy a nonzero outstanding-reference predicate. */
 atomic_store(&s.refcount,1);sem_post(&s.refsync);pthread_t t;pthread_create(&t,NULL,run_reinit,&s);
 struct timespec delay={0,30000000};nanosleep(&delay,NULL);assert(!atomic_load(&finished)&&!atomic_load(&released));
 pthread_mutex_lock(&s.queue_lock);atomic_store(&s.refcount,0);sem_post(&s.refsync);pthread_mutex_unlock(&s.queue_lock);
 pthread_join(t,NULL);assert(atomic_load(&finished)&&atomic_load(&released)==1&&!s.reinit);
 /* DRC doesn't discard input STOP/draining state. */
 s.draining=1;assert(!ff_v4l2_m2m_codec_reinit(&s));assert(s.draining);
 /* Linux v4l2-event empty queue is ENOENT; EAGAIN remains accepted too. */
 events_left=0;terminal_errno=ENOENT;assert(!v4l2_handle_event(&s.capture));
 terminal_errno=EAGAIN;assert(!v4l2_handle_event(&s.capture));
 terminal_errno=ENOENT;
 /* Actual caller must prioritize EIO over ready and public API must not EOF. */
 s.source_change_seen=0;s.drc_ready=s.drc_pending=0;s.capture.done=0;
 events_left=1;interrupt_once=1;terminal_errno=ENOENT;
 assert(dispatch_event(&s.capture)==NULL);assert(s.drc_ready&&!s.drc_error&&!interrupt_once);
 s.source_change_seen=0;s.drc_ready=0;events_left=1;terminal_errno=EIO;
 AVFrame frame={0};assert(ff_v4l2_context_dequeue_frame(&s.capture,&frame,0)==-EIO);
 assert(s.drc_ready&&s.drc_error==-EIO&&!s.capture.done);
 s.capture.done=1;assert(ff_v4l2_context_dequeue_frame(&s.capture,&frame,0)==-EIO);
 sem_destroy(&s.refsync);pthread_mutex_destroy(&s.queue_lock);
 puts("PASS extracted event/LAST/reinit: EOS informational, pending old-frame delivery, empty LAST, final LAST, initial no-buffer event, STREAMOFF failure retains mappings, stale-post predicate wait, draining preserved; EINTR retry, SOURCE then EIO priority, public error not EOF, empty ENOENT/EAGAIN, narrow DRC empty ERROR recycle without LAST/EOF");
}
'''
(p/'test-control.c').write_text(code)
subprocess.run(['cc','-std=c11','-pthread','-g','-O1','-fsanitize=address,undefined',str(p/'test-control.c'),'-o',str(p/'test-control')],check=True)
r=subprocess.run([str(p/'test-control')],capture_output=True,text=True,timeout=20)
(p/'test-control.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);r.check_returncode()
