#!/usr/bin/python3
"""One bounded reprobe for the observed Axon VA macro startup timeout."""
import os
import re
from pathlib import Path
import subprocess
import sys
import time

SYS = Path('/sys')
MARKER = Path('/run/axon-audio-startup-recover.attempted')
VA_NAME = '3370000.codec'
VA = SYS / 'bus/platform/devices' / VA_NAME


def log(message):
    print('axon-audio-startup: ' + message, flush=True)


def strings(path):
    return path.read_bytes().rstrip(b'\0').split(b'\0')


def driver(path):
    link = path / 'driver'
    return link.resolve().name if link.is_symlink() else None


def identity():
    if b'zte,axon10s-pro' not in strings(SYS / 'firmware/devicetree/base/compatible'):
        raise RuntimeError('not the supported Axon board')
    node = (VA / 'of_node').resolve(strict=True)
    if node.name != 'codec@3370000':
        raise RuntimeError('VA DT node name mismatch')
    if b'qcom,sm8250-lpass-va-macro' not in strings(node / 'compatible'):
        raise RuntimeError('VA compatible mismatch')
    if (node / 'reg').read_bytes() != bytes.fromhex('00000000033700000000000000001000'):
        raise RuntimeError('VA register identity mismatch')
    if not (SYS / 'bus/platform/drivers/va_macro').is_dir():
        raise RuntimeError('expected VA driver is not registered')
    override = VA / 'driver_override'
    if override.exists() and override.read_text().strip() not in ('', '(null)'):
        raise RuntimeError('VA driver_override is set')
    bound = driver(VA)
    if bound not in (None, 'va_macro'):
        raise RuntimeError('VA bound to an unexpected driver')
    return bound


def afe_ready():
    for dev in (SYS / 'bus/aprbus/devices').glob('*'):
        if driver(dev) == 'qcom-q6afe':
            try:
                if b'qcom,q6afe' in strings(dev / 'of_node/compatible'):
                    return True
            except OSError:
                pass
    return False


def known_failure(deferred, kernel_log):
    for name in ('3200000.rxmacro', '3220000.txmacro'):
        if not any(line.startswith(name + '\t') and 'supplier 3370000.codec not ready' in line
                   for line in deferred.splitlines()):
            return False
    # Match the nearest preceding AFE vote failure to the latest VA failure.
    # The observed pair is ~6 ms apart; reject old/unrelated log entries.
    events = []
    for line in kernel_log.splitlines():
        match = re.match(r"\[\s*(\d+\.\d+)\]\s+(.*)", line)
        if match:
            events.append((float(match.group(1)), match.group(2)))
    failures = [i for i, (_, line) in enumerate(events)
                if 'va_macro 3370000.codec: probe with driver va_macro failed with error ' in line]
    if not failures:
        return False
    index = failures[-1]
    stamp, failure = events[index]
    if not failure.rstrip().endswith('error -110'):
        return False
    votes = [(t, line) for t, line in events[:index] if 'AFE failed to vote (' in line]
    if not votes:
        return False
    vote_stamp, vote = votes[-1]
    return (0 <= stamp - vote_stamp <= 1.0 and
            'qcom-q6afe ' in vote and vote.rstrip().endswith('AFE failed to vote (3)'))



def main():
    if identity() == 'va_macro':
        log('VA already bound; no action')
        return 0
    deadline = time.monotonic() + 20
    while not afe_ready():
        if identity() == 'va_macro':
            log('VA became bound while waiting; no action')
            return 0
        if time.monotonic() >= deadline:
            raise RuntimeError('Q6AFE not ready within 20 seconds; no reprobe')
        time.sleep(0.5)
    deferred = (SYS / 'kernel/debug/devices_deferred').read_text()
    result = subprocess.run(['/usr/bin/dmesg', '--color=never'], capture_output=True,
                            text=True, timeout=3, check=True)
    if not known_failure(deferred, result.stdout):
        raise RuntimeError('observed timeout/dependency signature absent; no reprobe')
    if identity() == 'va_macro':
        log('VA became bound before attempt; no action')
        return 0
    try:
        fd = os.open(MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        log('this boot already consumed its one attempt; no action')
        return 0
    with os.fdopen(fd, 'w') as f:
        f.write('One VA reprobe attempted; original APR timeout cause remains unknown.\n')
    log('confirmed VA vote timeout; attempting one platform reprobe')
    # A child bounds the userspace wait around a potentially blocking sysfs store.
    child = subprocess.Popen([sys.executable, '-c',
        "from pathlib import Path; Path('/sys/bus/platform/drivers_probe').write_text('3370000.codec\\n')"])
    try:
        code = child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        child.kill()
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            log('probe child remains in kernel after SIGKILL; recovery required, no retry')
        raise RuntimeError('reprobe exceeded eight seconds; no retry')
    if code:
        raise RuntimeError('reprobe writer failed with status ' + str(code))
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if identity() == 'va_macro' and (Path('/proc/asound/cards').read_text().find('ZTE-Axon10s-TFA9894') >= 0):
            log('VA bound and expected sound card present; one-shot recovery complete')
            return 0
        time.sleep(0.5)
    raise RuntimeError('reprobe did not restore expected VA/card within eight seconds; no retry')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        log(str(exc))
        sys.exit(1)
