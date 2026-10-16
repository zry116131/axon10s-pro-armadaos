#!/usr/bin/env python3
"""Bounded destructive test of an UNUSED zram0, never an existing swap device."""
import hashlib, json, os, pathlib, subprocess
base = pathlib.Path('/sys/block/zram0')
if not base.exists():
    raise SystemExit('zram0 missing')
if int((base/'disksize').read_text()) != 0:
    raise SystemExit('refusing initialized zram0')
if '/dev/zram0' in pathlib.Path('/proc/swaps').read_text():
    raise SystemExit('refusing active swap')
if subprocess.check_output(['lsblk','-n','-o','MOUNTPOINTS','/dev/zram0'], text=True).strip():
    raise SystemExit('refusing mounted zram0')
size=64*1024*1024
(base/'comp_algorithm').write_text('lz4')
(base/'disksize').write_text(str(size))
try:
    for pattern in ('same-filled', 'compressible', 'random'):
        digest=hashlib.sha256()
        with open('/dev/zram0','wb',buffering=0) as f:
            for i in range(64):
                chunk=(bytes([i])*1048576 if pattern=='same-filled' else bytes((j+i)%256 for j in range(256))*4096 if pattern=='compressible' else os.urandom(1048576))
                if f.write(chunk)!=len(chunk): raise RuntimeError('short write')
                digest.update(chunk)
            os.fsync(f.fileno())
        got=hashlib.sha256()
        with open('/dev/zram0','rb',buffering=0) as f:
            for i in range(64):
                chunk=f.read(1048576)
                if len(chunk)!=1048576: raise RuntimeError('short read')
                got.update(chunk)
        if digest.digest()!=got.digest(): raise RuntimeError('data mismatch')
        print(json.dumps({'pattern':pattern,'bytes':size,'sha256':got.hexdigest(),'verified':True,'mm_stat':(base/'mm_stat').read_text().strip()}),flush=True)
finally:
    (base/'reset').write_text('1')
