#!/usr/bin/env python3
"""Compare the planned 60x128x128 + 60x640x360 sequence without relying on PTS."""
import json,re,sys
from pathlib import Path
if len(sys.argv)!=3: raise SystemExit('usage: compare-reconfig.py software.log hardware.log')
def read(path):
 text=Path(path).read_text()
 rows=[]
 for line in text.splitlines():
  if not line.startswith('FRAME '):continue
  fields=dict(re.findall(r'(\w+)=(\S+)',line))
  rows.append((int(fields['index']),int(fields['width']),int(fields['height']),fields['md5']))
 expected=[(i,128,128) if i<60 else (i,640,360) for i in range(120)]
 return {'rows':rows,'shape_order_valid':[r[:3] for r in rows]==expected,
         'clean_eof':'DECODE_END frames=120 result=2 decoder_instances=1 flushes=0 reopens=0' in text}
a,b=map(read,sys.argv[1:]);same=a['rows']==b['rows'];mismatch=[i for i,(x,y) in enumerate(zip(a['rows'],b['rows'])) if x!=y]
ok=same and a['shape_order_valid'] and b['shape_order_valid'] and a['clean_eof'] and b['clean_eof']
print(json.dumps({'pass':ok,'software_frames':len(a['rows']),'hardware_frames':len(b['rows']),
 'software_shape_order_valid':a['shape_order_valid'],'hardware_shape_order_valid':b['shape_order_valid'],
 'software_clean_eof':a['clean_eof'],'hardware_clean_eof':b['clean_eof'],
 'identical_index_size_hash':same,'mismatch_indices':mismatch},indent=2))
raise SystemExit(0 if ok else 1)
