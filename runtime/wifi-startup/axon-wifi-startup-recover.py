#!/usr/bin/python3
"""One narrowly gated PCI Wi-Fi rebind; not a firmware/root-cause fix."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time

SYS = Path('/sys')
BDF = '0000:01:00.0'
DEVICE = SYS / 'bus/pci/devices' / BDF
DRIVER = SYS / 'bus/pci/drivers/ath11k_pci'
FIRMWARE = Path('/lib/firmware/ath11k/QCA6390/hw2.0/board-2.bin.xz')
SHA256 = 'd7ad84920359fdce4d05d5a1b318a1e2749782dd51501ead9f6a3e1f9af7615d'
MARKER = Path('/run/axon-wifi-startup-recover.attempted')


def log(message):
    print('axon-wifi-startup: ' + message, flush=True)


def interface_present():
    # Only this PCI function. Any net interface is sufficient to prevent rebind.
    net = DEVICE / 'net'
    if not net.exists():
        return False
    return any(net.iterdir())


def identity():
    board = (SYS / 'firmware/devicetree/base/compatible').read_bytes().split(b'\0')
    if b'zte,axon10s-pro' not in board:
        raise RuntimeError('board mismatch')
    if DEVICE.resolve(strict=True).name != BDF:
        raise RuntimeError('PCI identity mismatch')
    if (DEVICE / 'vendor').read_text().strip() != '0x17cb' or (DEVICE / 'device').read_text().strip() != '0x1101':
        raise RuntimeError('PCI vendor/device mismatch')
    if not (DEVICE / 'driver').is_symlink() or (DEVICE / 'driver').resolve(strict=True) != DRIVER.resolve(strict=True):
        raise RuntimeError('ath11k_pci binding absent or different')
    override = (DEVICE / 'driver_override').read_text().strip()
    if override not in ('', '(null)'):
        raise RuntimeError('driver_override set')


def known_failure(kernel_log):
    return any(re.search(r'ath11k_pci 0000:01:00\.0: failed to load board data file: -2\s*$', line)
               for line in kernel_log.splitlines())


def firmware_matches():
    # No directory scan and no firmware content is emitted.
    with FIRMWARE.open('rb') as f:
        data = f.read(1048577)
    return len(data) <= 1048576 and hashlib.sha256(data).hexdigest() == SHA256


def main():
    if os.geteuid() != 0:
        raise RuntimeError('root required')
    identity()
    if interface_present():
        log('target PCI net interface already exists; no action')
        return 0
    if MARKER.exists():
        log('this boot already consumed its attempt; no action')
        return 0
    if not firmware_matches():
        raise RuntimeError('root board-2 compressed firmware hash mismatch')
    output = subprocess.run(['/usr/bin/dmesg', '--color=never'], capture_output=True,
                            text=True, check=True, timeout=3).stdout
    if not known_failure(output):
        log('exact target board-data -2 signature absent; no action')
        return 0
    identity()
    if interface_present():
        log('target interface appeared before attempt; no action')
        return 0
    try:
        fd = os.open(MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        log('another invocation reserved this boot attempt; no action')
        return 0
    with os.fdopen(fd, 'w') as f:
        f.write('One target PCI rebind reserved; root cause remains unconfirmed.\n')
    log('confirmed target board-data failure and firmware hash; one rebind')
    # The child has only two fixed sysfs stores. Timeout never launches another.
    child = subprocess.Popen([sys.executable, '-c', """
from pathlib import Path
import sys
d = Path('/sys/bus/pci/devices/0000:01:00.0')
p = Path('/sys/bus/pci/drivers/ath11k_pci')
if (d / 'vendor').read_text().strip() != '0x17cb' or (d / 'device').read_text().strip() != '0x1101':
    sys.exit('PCI identity changed before unbind')
if not (d / 'driver').is_symlink() or (d / 'driver').resolve(strict=True) != p.resolve(strict=True):
    sys.exit('PCI binding changed before unbind')
if (d / 'driver_override').read_text().strip() not in ('', '(null)'):
    sys.exit('PCI override changed before unbind')
net = d / 'net'
if net.exists() and any(net.iterdir()):
    print('axon-wifi-startup: interface appeared in child; no rebind', flush=True)
    sys.exit(0)
p.joinpath('unbind').write_text('0000:01:00.0\\n')
p.joinpath('bind').write_text('0000:01:00.0\\n')
"""])
    try:
        status = child.wait(timeout=12)
    except subprocess.TimeoutExpired:
        child.kill()
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            log('child remains in kernel after SIGKILL; no retry, recovery required')
        raise RuntimeError('rebind exceeded 12 seconds; binding state must be checked')
    if status:
        raise RuntimeError('rebind child failed; binding state must be checked; no retry')
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        identity()
        if interface_present():
            log('target interface restored; association/connectivity not tested')
            return 0
        time.sleep(0.5)
    raise RuntimeError('no target interface within 15 seconds; no retry')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        log('skip/failure: ' + str(exc))
        sys.exit(1)
