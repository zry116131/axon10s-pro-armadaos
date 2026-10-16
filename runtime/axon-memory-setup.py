#!/usr/bin/python3
"""Enable the verified fallback swap and 2 GiB LZ4 zram without resetting live data."""
import pathlib,subprocess

def active():
    return {line.split()[0] for line in pathlib.Path('/proc/swaps').read_text().splitlines()[1:]}
def run(*args):subprocess.run(args,check=True)
disk='/var/lib/axon-swap/swapfile'
if disk not in active():
    p=pathlib.Path(disk)
    if not p.is_file() or p.is_symlink() or p.stat().st_uid!=0 or p.stat().st_mode & 0o077:
        raise SystemExit('fallback swap missing or unsafe permissions')
    run('/usr/sbin/swapon','-p','10',disk)
z=pathlib.Path('/sys/block/zram0')
if not z.exists():
    print('kernel has no zram0; disk fallback enabled')
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
print(pathlib.Path('/proc/swaps').read_text())
