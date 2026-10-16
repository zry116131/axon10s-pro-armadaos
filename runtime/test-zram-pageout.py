#!/usr/bin/env python3
import ctypes,hashlib,json,mmap,pathlib,time
n=128*1024*1024
m=mmap.mmap(-1,n,flags=mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS,prot=mmap.PROT_READ|mmap.PROT_WRITE)
chunk=bytes(range(256))*4096
for off in range(0,n,len(chunk)):m[off:off+len(chunk)]=chunk
before=hashlib.sha256(m).hexdigest()
a=ctypes.addressof(ctypes.c_char.from_buffer(m));libc=ctypes.CDLL(None,use_errno=True)
libc.madvise.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
if libc.madvise(a,n,21)!=0:raise OSError(ctypes.get_errno(),'MADV_PAGEOUT')
time.sleep(2)
smaps=pathlib.Path('/proc/self/smaps_rollup').read_text()
swap_kb=int(next(s.split()[1] for s in smaps.splitlines() if s.startswith('Swap:')))
stat=pathlib.Path('/sys/block/zram0/mm_stat').read_text().strip()
after=hashlib.sha256(m).hexdigest()
result={'bytes':n,'swap_kib_before_readback':swap_kb,'zram_mm_stat_before_readback':stat,'data_matches':before==after,'sha256':after}
print(json.dumps(result),flush=True)
assert before==after and swap_kb>0
m.close()
