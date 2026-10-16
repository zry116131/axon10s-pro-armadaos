from pathlib import Path
import subprocess,sys
p=Path(__file__).resolve().parent
if sys.platform!='linux':raise SystemExit('Linux required')
def func(sig):
 s=(p/'v4l2_m2m_dec.c').read_text();a=s.index(sig);b=s.index('{',a)+1;d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
pre=r'''
#include <time.h>
#include <linux/videodev2.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#define AVERROR(e) (-(e))
#define AVERROR_INVALIDDATA (-1234)
typedef struct {struct v4l2_format format;unsigned int width,height,type;int done;} V4L2Context;
typedef struct {V4L2Context capture;int fd,drc_ready,drc_pending;} V4L2m2mContext;
typedef struct {V4L2m2mContext*context;} V4L2m2mPriv;
typedef struct {void*priv_data;int width,height,coded_width,coded_height;} AVCodecContext;
static struct v4l2_rect crop;
static int query_errno,reconfigured;
static int ioctl(int fd,unsigned long request,void*p){
 if(request==VIDIOC_G_FMT){struct v4l2_format*f=p;f->fmt.pix_mp.width=640;f->fmt.pix_mp.height=384;return 0;}
 assert(request==VIDIOC_G_SELECTION);if(query_errno){errno=query_errno;return -1;}
 struct v4l2_selection*s=p;assert(s->type==V4L2_BUF_TYPE_VIDEO_CAPTURE);assert(s->target==V4L2_SEL_TGT_COMPOSE||s->target==V4L2_SEL_TGT_COMPOSE_DEFAULT);s->r=crop;return 0;
}
static int ff_set_dimensions(AVCodecContext*a,int w,int h){a->coded_width=a->width=w;a->coded_height=a->height=h;return 0;}
static int ff_v4l2_m2m_codec_reinit(V4L2m2mContext*s){
 reconfigured++; /* model Venus S_FMT resetting crop to aligned allocation */
 crop=(struct v4l2_rect){0,0,640,384};s->capture.format.fmt.pix_mp.width=640;s->capture.format.fmt.pix_mp.height=384;return 0;
}
static int v4l2_try_start(AVCodecContext*a){V4L2m2mContext*s=((V4L2m2mPriv*)a->priv_data)->context;s->capture.width=a->width=crop.width;s->capture.height=a->height=crop.height;return 0;}
'''
code=pre+func('static int v4l2_save_visible(')+'\n'+func('static int v4l2_finish_drc(')+r'''
int main(void){
 V4L2m2mContext s={0};V4L2m2mPriv p={&s};AVCodecContext a={&p};s.capture.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;s.capture.format.type=s.capture.type;
 crop=(struct v4l2_rect){0,0,640,360};s.drc_pending=s.drc_ready=1;
 assert(!v4l2_finish_drc(&a));assert(reconfigured==1);
 assert(a.width==640&&a.height==360&&s.capture.height==360);
 assert(a.coded_height==384&&s.capture.format.fmt.pix_mp.height==384&&crop.height==384);
 assert(!s.drc_pending&&!s.drc_ready);
 crop=(struct v4l2_rect){2,0,638,360};assert(v4l2_finish_drc(&a)==-ENOSYS);assert(reconfigured==1);
 crop=(struct v4l2_rect){0,0,640,400};assert(v4l2_finish_drc(&a)==AVERROR_INVALIDDATA);assert(reconfigured==1);
 query_errno=EIO;assert(v4l2_finish_drc(&a)==-EIO);assert(reconfigured==1);
 query_errno=EINVAL;assert(!v4l2_finish_drc(&a));assert(a.height==384);
 puts("PASS extracted visible/finish_drc: COMPOSE saved before S_FMT crop reset; visible360 vs allocated384 preserved; nonzero/invalid rejected; EIO propagated; unsupported fallback");
}
'''
(p/'test-visible.c').write_text(code)
subprocess.run(['cc','-std=c11','-g','-O1','-fsanitize=address,undefined',str(p/'test-visible.c'),'-o',str(p/'test-visible')],check=True)
r=subprocess.run([str(p/'test-visible')],capture_output=True,text=True,timeout=20);(p/'test-visible.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);r.check_returncode()
