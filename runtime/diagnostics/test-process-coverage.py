"""Verify real sampler selection under thread pressure and gamescope comm rename."""
import importlib.util
import tempfile
from pathlib import Path
spec = importlib.util.spec_from_file_location('sampler', Path(__file__).with_name('capture-freeze.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    m.PROC = Path(td)
    for pid, name in [(100, 'steamwebhelper'), (200, 'gamescope-wl')]:
        p = m.PROC / str(pid)
        p.mkdir()
        (p / 'comm').write_text(name)
        (p / 'cmdline').write_bytes((name + ('\0--type=gpu-process' if pid == 100 else '') + '\0').encode())
        for tid in range(pid, pid + (50 if pid == 100 else 1)):
            t = p / 'task' / str(tid)
            t.mkdir(parents=True)
            (t / 'comm').write_text('GpuWatchdog' if tid == 149 else 'RenderThread')
            (t / 'stack').write_text('[<00000000>] test_wait+0x0/0x10\n')
    rows = {r['pid']: r for r in m.processes()}
    gpu = rows[100]
    assert len(gpu['threads']) == 32 and gpu['threads_omitted'] == 18
    assert [t['tid'] for t in gpu['threads'][:2]] == [149, 100]
    assert rows[200]['name'] == 'gamescope-wl'
    assert rows[200]['threads'][0]['kernel_stack'] == ['test_wait']
print('PASS: watchdog + main retained among 50 critical-name threads; gamescope-wl stack sampled')
