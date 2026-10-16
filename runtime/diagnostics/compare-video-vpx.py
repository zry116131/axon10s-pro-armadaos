import json,re,sys
from pathlib import Path
if len(sys.argv)!=4 or sys.argv[3] not in ('stop','drain'):raise SystemExit('reference.framemd5 hardware.log stop|drain')
ref=[line.split(',')[-1].strip() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip() and not line.startswith('#')]
text=Path(sys.argv[2]).read_text();rows=[dict(re.findall(r'(\w+)=(\S+)',line)) for line in text.splitlines() if line.startswith('FRAME ')]
mode=sys.argv[3];n=30 if mode=='stop' else 60;result=1 if mode=='stop' else 2
ok=len(ref)==60 and len(rows)==n and all(row['md5']==ref[i] and row['width']=='320' and row['height']=='240' and row['index']==str(i) for i,row in enumerate(rows)) and f'DECODE_END frames={n} result={result} ' in text and not any(line.startswith('ERROR') for line in text.splitlines())
print(json.dumps({'pass':ok,'mode':mode,'software_frames':len(ref),'hardware_reported_frames':len(rows),'scope':'ordered visible pixel MD5 and dimensions; process exit code checked separately'}))
raise SystemExit(0 if ok else 1)
