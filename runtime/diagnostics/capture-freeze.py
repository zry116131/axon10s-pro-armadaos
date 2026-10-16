#!/usr/bin/env python3
"""Bounded, read-only freeze sampler. No CDP, page/log content, ptrace or signals."""
import argparse
import datetime
import json
import os
import pathlib
import re
import time

PROC = pathlib.Path('/proc')
NAMES = {'steamwebhelper', 'gamescope', 'gamescope-wl', 'Xwayland'}
MEM = {'MemAvailable', 'MemFree', 'SwapTotal', 'SwapFree', 'Shmem', 'Slab'}
VM = {'oom_kill', 'pswpin', 'pswpout', 'allocstall_normal', 'allocstall_dma32',
      'pgscan_direct', 'pgsteal_direct', 'compact_stall'}
EVENTS = {'oom': r'out of memory|oom-kill|killed process',
          'gpu_fault': r'gpu.*(?:fault|hang|reset|recover)|(?:adreno|msm|drm).*fault',
          'gpu_timeout': r'(?:gpu|adreno|msm|drm).*timeout',
          'blocked_task': r'blocked for more than',
          'segfault': r'segfault'}


def read(path, limit=4096):
    try:
        with open(path, 'r', errors='replace') as f:
            return f.read(limit)
    except (OSError, PermissionError):
        return None


def stat(path):
    s = read(path)
    if not s or ')' not in s:
        return None
    fields = s[s.rfind(')') + 2:].split()
    try:
        return dict(state=fields[0], ppid=int(fields[1]),
                    utime=int(fields[11]), stime=int(fields[12]),
                    starttime=int(fields[19]), rss_pages=int(fields[21]))
    except (IndexError, ValueError):
        return None


def counters(path, keys):
    out = {}
    for row in (read(path, 16384) or '').splitlines():
        parts = row.replace(':', '').split()
        if len(parts) >= 2 and parts[0] in keys:
            out[parts[0]] = int(parts[1])
    return out


def processes():
    out = []
    candidates = []
    for d in PROC.iterdir():
        if not d.name.isdigit():
            continue
        name = (read(d / 'comm', 64) or '').strip()
        if name not in NAMES:
            continue
        # Inspect only fixed role switches; never save command lines or URLs.
        cmd = (d / 'cmdline')
        raw = read(cmd, 16384) or ''
        role = 'gpu' if '--type=gpu-process' in raw.split('\0') else (
            'renderer' if '--type=renderer' in raw.split('\0') else 'main/other')
        # Forked CEF children can retain the zygote command line on this build.
        # GpuWatchdog is a role hint, not proof from the executable arguments.
        if name == 'steamwebhelper' and role == 'main/other':
            try:
                if any((read(t / 'comm', 64) or '').strip() == 'GpuWatchdog'
                       for t in (d / 'task').iterdir()):
                    role = 'gpu_thread_hint'
            except OSError:
                pass
        candidates.append((d, name, role))
    priority = {'gpu': 0, 'gpu_thread_hint': 0, 'main/other': 1, 'renderer': 2}
    candidates.sort(key=lambda item: (priority[item[2]], int(item[0].name)))
    for d, name, role in candidates[:32]:
        row = dict(pid=int(d.name), name=name, role=role, stat=stat(d / 'stat'))
        threads = []
        try:
            tasks = sorted((d / 'task').iterdir(), key=lambda x: int(x.name))
        except OSError:
            continue
        row['thread_count'] = len(tasks)
        named = [(t, (read(t / 'comm', 64) or '').strip()) for t in tasks]
        critical = {'GpuWatchdog', 'CrGpuMain', 'VizCompositorTh', 'Compositor', 'RenderThread'}
        named.sort(key=lambda pair: (0 if pair[1] == 'GpuWatchdog' else 1 if pair[0].name == d.name else
                                     2 if pair[1] in critical else 3,
                                     int(pair[0].name)))
        row['threads_omitted'] = max(0, len(named) - 32)
        for t, thread_name in named[:32]:
            item = dict(tid=int(t.name), name=thread_name, stat=stat(t / 'stat'),
                        wchan=(read(t / 'wchan', 128) or '').strip())
            if role in {'gpu', 'gpu_thread_hint'} or name in {'gamescope', 'gamescope-wl', 'Xwayland'}:
                stack = read(t / 'stack', 2048)
                # Function names only: discard addresses, offsets and arguments.
                item['kernel_stack'] = (re.findall(r'\]\s+([A-Za-z0-9_.]+)\+', stack)
                                        if stack is not None else None)
            threads.append(item)
        row['threads'] = threads
        out.append(row)
        if len(out) >= 32:
            break
    return out


class CefEvents:
    """Read at most 32 KiB per tick; retain no original log lines in output."""
    patterns = {
        'gpu_process_exit': re.compile(r'GPU process exited', re.I),
        'shared_image': re.compile(r'SharedImage', re.I),
        'buffer_handle_null': re.compile(r'Buffer handle is null', re.I),
        'watchdog': re.compile(r'watchdog', re.I),
    }
    timestamp = re.compile(
        r'(?<!\d)(?:\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}'
        r'(?:\.\d{1,9})?|\d{4}/\d{6}(?:\.\d{1,9})?)(?!\d)')

    def __init__(self, path):
        self.path = path
        self.identity = None
        self.offset = 0
        self.pending = b''
        self.dropping = False
        # Existing bytes at arming are excluded. Files created later start at 0.
        if path:
            try:
                st = os.stat(path)
                self.identity = (st.st_dev, st.st_ino)
                self.offset = st.st_size
            except OSError:
                pass

    def sample(self):
        if not self.path:
            return None
        result = {'events': []}
        try:
            with open(self.path, 'rb') as f:
                st = os.fstat(f.fileno())
                identity = (st.st_dev, st.st_ino)
                if identity != self.identity or st.st_size < self.offset:
                    result['reset'] = 'rotation' if identity != self.identity else 'truncation'
                    self.identity = identity
                    self.offset = 0
                    self.pending = b''
                    self.dropping = False
                f.seek(self.offset)
                chunk = f.read(32768)
                self.offset = f.tell()
                result['backlog_bytes'] = max(0, st.st_size - self.offset)
        except OSError as exc:
            result['read_errno'] = exc.errno
            return result
        result['read_bytes'] = len(chunk)
        for fragment in chunk.splitlines(keepends=True):
            complete = fragment.endswith(b'\n')
            if not self.dropping:
                self.pending += fragment
                if len(self.pending) > 4096:
                    self.pending = b''
                    self.dropping = True
                    result['oversize_lines_dropped'] = result.get('oversize_lines_dropped', 0) + 1
            if complete:
                if not self.dropping:
                    line = self.pending.decode(errors='replace')
                    categories = [key for key, pat in self.patterns.items() if pat.search(line)]
                    if categories:
                        stamp = self.timestamp.search(line)
                        if len(result['events']) < 64:
                            result['events'].append({'timestamp': stamp.group(0) if stamp else None,
                                                     'categories': categories})
                        else:
                            result['events_overflow'] = True
                self.pending = b''
                self.dropping = False
        return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True)
    ap.add_argument('--seconds', type=int, default=180)
    ap.add_argument('--cef-log', help='Optional CEF log; only new whitelisted event metadata is saved')
    args = ap.parse_args()
    if not 1 <= args.seconds <= 600:
        ap.error('--seconds must be 1..600')
    os.umask(0o077)
    # Exclusive create: never truncate or follow an existing output symlink.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    kfd, kerror = None, None
    try:
        kfd = os.open('/dev/kmsg', os.O_RDONLY | os.O_NONBLOCK)
        os.lseek(kfd, 0, os.SEEK_END)  # Only new events after arming.
    except OSError as exc:
        kerror = exc.errno
        if kfd is not None:
            os.close(kfd)
            kfd = None
    cef = CefEvents(args.cef_log)
    start = time.monotonic()
    written = 0
    with os.fdopen(fd, 'w', buffering=1) as output:
        def emit(row):
            nonlocal written
            text = json.dumps(row, separators=(',', ':')) + '\n'
            if written + len(text) > 8 * 1024 * 1024:
                return False
            output.write(text)
            written += len(text)
            return True
        emit(dict(event='armed', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  euid=os.geteuid(), kmsg_errno=kerror, clock_ticks=os.sysconf('SC_CLK_TCK'),
                  max_processes=32, max_threads_each=32, limit_bytes=8*1024*1024))
        for index in range(args.seconds):
            events = []
            if kfd is not None:
                for _ in range(32):
                    try:
                        msg = os.read(kfd, 8192).decode(errors='replace')
                    except BlockingIOError:
                        break
                    except OSError as exc:
                        events.append(dict(read_errno=exc.errno))
                        break
                    header, _, body = msg.partition(';')
                    categories = [key for key, pattern in EVENTS.items()
                                  if re.search(pattern, body, re.I)]
                    if categories:
                        events.append(dict(header=header[:100], categories=categories))
            try:
                shm = os.statvfs('/dev/shm')
                shm_free = shm.f_bavail * shm.f_frsize
            except OSError:
                shm_free = None
            row = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       monotonic=time.monotonic(), mem_kib=counters(PROC/'meminfo', MEM),
                       vmstat=counters(PROC/'vmstat', VM), shm_free_bytes=shm_free,
                       pressure={key: read(PROC/'pressure'/key, 1024)
                                 for key in ('memory', 'io', 'cpu')},
                       processes=processes(), kernel_events=events, cef=cef.sample())
            if not emit(row):
                break
            delay = start + index + 1 - time.monotonic()
            if delay > 0:
                time.sleep(delay)
        emit(dict(event='finished', elapsed=time.monotonic()-start))
    if kfd is not None:
        os.close(kfd)


if __name__ == '__main__':
    main()
