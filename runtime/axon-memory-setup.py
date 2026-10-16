#!/usr/bin/python3
"""Enable only 2 GiB LZ4 zram; retire the previous disk swap safely."""
import pathlib,subprocess

def active():
    return {line.split()[0] for line in pathlib.Path('/proc/swaps').read_text().splitlines()[1:]}
def run(*args):subprocess.run(args,check=True)
disk='/var/lib/axon-swap/swapfile'
z=pathlib.Path('/sys/block/zram0')
if not z.exists():
    raise SystemExit('kernel has no zram0; refusing to enable the retired disk swap')
elif '/dev/zram0' in active():
    print('zram already active; left unchanged')
else:
    size=int((z/'disksize').read_text())
    if size:
        raise SystemExit('zram0 initialized but not active; refusing to reset it')
    (z/'comp_algorithm').write_text('lz4')
    (z/'disksize').write_text(str(2*1024**3))
    run('/usr/sbin/mkswap','/dev/zram0')
    run('/usr/sbin/swapon','-p','100','/dev/zram0')
if disk in active():
    rows=pathlib.Path('/proc/swaps').read_text().splitlines()[1:]
    used_kib=next(int(row.split()[3]) for row in rows if row.split()[0]==disk)
    info=dict(line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
    available_kib=int(info['MemAvailable'].split()[0])
    if available_kib < used_kib + 512*1024:
        raise SystemExit('insufficient memory to retire disk swap safely; retry after closing games')
    run('/usr/sbin/swapoff',disk)
if '/dev/zram0' not in active() or disk in active():
    raise SystemExit('exclusive zram configuration not reached')
print(pathlib.Path('/proc/swaps').read_text())
