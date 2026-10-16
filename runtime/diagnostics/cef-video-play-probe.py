import base64,json,pathlib,urllib.request,websocket,time,sys
p=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/var/lib/axon-swap/venus-synthetic.mp4'); data=p.read_bytes()
assert len(data)<8*1024*1024
pages=json.load(urllib.request.urlopen('http://127.0.0.1:8080/json/list',timeout=5))
page=next(p for p in pages if p['title']=='Steam 大屏幕模式')
w=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=40,suppress_origin=True)
events=[]
allowed={'kVideoDecoderName','kIsPlatformVideoDecoder','kVideoTracks','kResolution','kFrameUrl','kRendererName','video_decoder','is_platform_video_decoder'}
def call(i,method,params):
 w.send(json.dumps({'id':i,'method':method,'params':params}))
 while True:
  r=json.loads(w.recv())
  if r.get('method')=='Media.playerPropertiesChanged':
   props=[x for x in r['params']['properties'] if x['name'] in allowed and x['name']!='kFrameUrl']
   if props:events.append({'playerId':r['params']['playerId'],'properties':props})
  if r.get('id')==i:return r
try:
 call(1,'Media.enable',{})
 expr='''(async()=>{const v=document.createElement('video');v.muted=true;v.playsInline=true;v.style.cssText='position:fixed;width:1px;height:1px;opacity:0;pointer-events:none';document.body.appendChild(v);let result;const jumps=[];let stage=0;v.ontimeupdate=()=>{if(SEEK&&stage===0&&v.currentTime>=1){stage=1;jumps.push({from:v.currentTime,to:10});v.currentTime=10}else if(SEEK&&stage===1&&v.currentTime>=11){stage=2;jumps.push({from:v.currentTime,to:3});v.currentTime=3}};try {result=await new Promise(resolve=>{const timer=setTimeout(()=>resolve({outcome:'timeout'}),35000);v.onended=()=>{clearTimeout(timer);resolve({outcome:'ended'})};v.onerror=()=>{clearTimeout(timer);resolve({outcome:'error',code:v.error?.code,message:v.error?.message})};v.src=SOURCE;v.play().catch(e=>{clearTimeout(timer);resolve({outcome:'play-rejected',message:String(e)})})});let q=v.getVideoPlaybackQuality();return {...result,width:v.videoWidth,height:v.videoHeight,time:v.currentTime,total:q.totalVideoFrames,dropped:q.droppedVideoFrames,jumps}}finally{v.pause();v.removeAttribute('src');v.load();v.remove()}})()'''.replace('SEEK','true' if len(sys.argv)>2 and sys.argv[2]=='seek' else 'false').replace('SOURCE',json.dumps('data:video/mp4;base64,'+base64.b64encode(data).decode()))
 r=call(2,'Runtime.evaluate',{'expression':expr,'awaitPromise':True,'returnByValue':True})
 print(json.dumps({'playback':r,'decoder_properties':events},indent=2))
finally:w.close()
