#!/usr/bin/env python3
"""Bounded single-file H264 decode comparison; hardware requires an exact kernel.

No looping, power changes, service changes, or firmware writes. Outputs are flushed
per frame so an abort does not erase the last successful output-frame boundary.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import resource
import re
import signal
import subprocess
import time


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))


def run(argv, output, seconds):
    start = time.monotonic()
    with output.open('xb') as log:
        proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True, preexec_fn=limits)
        timed_out = False
        try:
            proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if proc.poll() is None:
                for sig, grace in ((signal.SIGTERM, 2), (signal.SIGKILL, 1)):
                    try:
                        os.killpg(proc.pid, sig)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.wait(timeout=grace)
                        break
                    except subprocess.TimeoutExpired:
                        pass  # A blocked kernel task cannot be promised killable.
    return dict(returncode=proc.poll(), timed_out=timed_out,
                elapsed=round(time.monotonic() - start, 3), pid=proc.pid)


def rows(path):
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines(keepends=True)
            if line.endswith('\n') and re.fullmatch(
                r'\s*\d+,\s*-?\d+,\s*-?\d+,\s*\d+,\s*\d+,\s*[0-9a-f]{32}\s*', line)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, help='new evidence directory')
    parser.add_argument('--frames', type=int, default=300)
    parser.add_argument('--hardware-kernel', help='exact expected uname -r; omit for software only')
    parser.add_argument('--realtime', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.frames <= 600 or not args.input.is_file():
        parser.error('require a regular input file and 1..600 frames')
    if args.hardware_kernel:
        if platform.release() != args.hardware_kernel or not Path('/dev/video1').exists():
            parser.error('hardware kernel or video node does not match')
    args.output.mkdir(parents=False, exist_ok=False)
    source = str(args.input.resolve())
    probe = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_packets', '-show_entries', 'packet=pts_time,dts_time,pos,size,flags',
                 '-of', 'json', source], args.output / 'packets.json', 15)
    report = dict(kernel=platform.release(), requested_frames=args.frames,
                  realtime=args.realtime, probe=probe, trials={})
    modes = ['software', 'hardware'] if args.hardware_kernel else ['software']
    if probe['returncode'] != 0 or probe['timed_out']:
        modes = []
    for mode in modes:
        md5 = args.output / (mode + '.framemd5')
        command = ['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-loglevel', 'warning']
        if args.realtime:
            command += ['-re']
        command += ['-c:v', 'h264_v4l2m2m' if mode == 'hardware' else 'h264',
                    '-i', source, '-map', '0:v:0', '-an', '-frames:v', str(args.frames),
                    '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough',
                    '-stats_period', '0.25', '-progress', str(args.output / (mode + '.progress')),
                    '-f', 'framemd5', '-flush_packets', '1', '-n', str(md5)]
        trial = run(command, args.output / (mode + '.log'), 45)
        decoded = rows(md5)
        trial.update(frames=len(decoded), last_frame=decoded[-1] if decoded else None)
        content = md5.read_text() if md5.exists() else ''
        trial['incomplete_tail_ignored'] = bool(content and not content.endswith('\n'))
        report['trials'][mode] = trial
        if trial['returncode'] is None or (mode == 'software' and
                (trial['returncode'] != 0 or trial['timed_out'] or len(decoded) != args.frames)):
            break
    if 'hardware' in report['trials']:
        sw, hw = rows(args.output / 'software.framemd5'), rows(args.output / 'hardware.framemd5')
        report['matching_output_prefix'] = bool(hw) and hw == sw[:len(hw)]
        report['complete_match'] = (len(sw) == args.frames and sw == hw and
                                    all(t['returncode'] == 0 and not t['timed_out']
                                        for t in report['trials'].values()))
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    success = (report.get('complete_match', False) if args.hardware_kernel else
               'software' in report['trials'] and
               report['trials']['software']['returncode'] == 0 and
               not report['trials']['software']['timed_out'] and
               report['trials']['software']['frames'] == args.frames)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
