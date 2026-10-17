#!/usr/bin/python3
import hashlib, os, pathlib, subprocess, time
P=pathlib.Path
if os.geteuid()!=0: raise SystemExit('root required')
u=os.uname()
if u.release!='7.2.6-axon10s-avcompat2' or not u.version.startswith('#93 '): raise SystemExit('unsupported kernel; no changes')
d=P('/sys/bus/i2c/devices/13-0022')
for _ in range(40):
 if d.exists(): break
 time.sleep(.25)
if not d.exists() or 'Csyna,s3908' not in (d/'modalias').read_text(): raise SystemExit('unexpected touch device')
if (d/'driver').exists():
 print('touch already bound; no change'); raise SystemExit(0)
m=P('/usr/local/lib/axon/axon_tcm_repair93.ko')
if hashlib.sha256(m.read_bytes()).hexdigest()!='fe8ef799e439888d78799fe3dc6533cc7f69e00396241b620c8e455749cf356d': raise SystemExit('module hash mismatch')
subprocess.run(['/usr/bin/insmod',str(m)],check=True,timeout=10)
if not (d/'driver').exists() or (d/'driver').resolve().name!='axon-tcm-repair93' or not list((d/'input').glob('input*')):
 subprocess.run(['/usr/bin/rmmod','axon_tcm_repair93'],check=False,timeout=10)
 raise SystemExit('touch registration failed; module removed')
print('touch recovery registered')
