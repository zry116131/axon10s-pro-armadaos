#!/usr/bin/env python3
"""Bounded single-stream VPx diagnosis with throttled input. Parent supplies an external timeout."""
import hashlib
import sys
import time


def visible_md5(data, width, height, offsets, strides):
    """Hash visible I420 rows, rejecting unsupported/invalid layouts."""
    if width <= 0 or height <= 0 or len(offsets) < 3 or len(strides) < 3:
        raise ValueError("invalid I420 geometry")
    digest = hashlib.md5()
    for plane, (cols, rows) in enumerate(((width, height),
                                          ((width + 1) // 2, (height + 1) // 2),
                                          ((width + 1) // 2, (height + 1) // 2))):
        offset, stride = int(offsets[plane]), int(strides[plane])
        if offset < 0 or stride < cols:
            raise ValueError("unsupported negative/short stride or negative offset")
        if offset + (rows - 1) * stride + cols > len(data):
            raise ValueError("plane extends beyond mapped buffer")
        for row in range(rows):
            start = offset + row * stride
            digest.update(data[start:start + cols])
    return digest.hexdigest()


def main():
    if len(sys.argv) != 4 or sys.argv[2] not in ('vp8','vp9') or sys.argv[3] not in ('stop','drain'):
        print("usage: gst-vpx.py INPUT.webm vp8|vp9 stop|drain", file=sys.stderr)
        return 2
    codec, mode = sys.argv[2:4]
    decoder = 'v4l2' + codec + 'dec'
    try:
        import gi
        gi.require_version("Gst", "1.0")
        gi.require_version("GstVideo", "1.0")
        from gi.repository import Gst, GstVideo, GLib
        Gst.init(None)
        pipeline = Gst.parse_launch(
            f"filesrc name=source ! matroskademux ! identity sleep-time=33333 ! {decoder} name=decoder ! videoconvert ! "
            "video/x-raw,format=I420 ! appsink name=sink emit-signals=true "
            "sync=false max-buffers=4 drop=false")
    except Exception as exc:
        print(f"ERROR setup: {exc}", file=sys.stderr, flush=True)
        return 1

    loop = GLib.MainLoop()
    state = {"frames": 0, "failed": False, "eos": False, "stopped": False}

    def fail(reason):
        state["failed"] = True
        print(f"ERROR {reason}", file=sys.stderr, flush=True)
        GLib.idle_add(loop.quit)

    def sample_ready(sink):
        try:
            sample = sink.emit("pull-sample")
            if state['stopped']:
                return Gst.FlowReturn.OK
            if sample is None:
                raise RuntimeError("new-sample returned no sample")
            if state["frames"] >= 240:
                raise RuntimeError("frame limit 240 exceeded; no additional frame hashed")
            caps = sample.get_caps()
            info = GstVideo.VideoInfo.new_from_caps(caps)
            if info is None or info.finfo.format != GstVideo.VideoFormat.I420:
                raise RuntimeError("sample is not valid I420")
            structure = caps.get_structure(0)
            # Only ordinary single-view progressive frames are normalized here.
            if structure.has_field("interlace-mode") and structure.get_string("interlace-mode") != "progressive":
                raise RuntimeError("unsupported interlaced layout")
            if structure.has_field("multiview-mode") and structure.get_string("multiview-mode") != "mono":
                raise RuntimeError("unsupported multiview layout")
            if structure.has_field("views") and structure.get_value("views") != 1:
                raise RuntimeError("unsupported view count")
            buffer = sample.get_buffer()
            meta = GstVideo.buffer_get_video_meta(buffer)
            offsets, strides = info.offset, info.stride
            if meta is not None:
                if (meta.format != GstVideo.VideoFormat.I420 or
                        meta.width != info.width or meta.height != info.height or
                        meta.n_planes != 3 or meta.id != 0):
                    raise RuntimeError("unsupported video meta geometry/view")
                offsets, strides = meta.offset, meta.stride
            mapped, mapinfo = buffer.map(Gst.MapFlags.READ)
            if not mapped:
                raise RuntimeError("buffer map failed")
            try:
                checksum = visible_md5(mapinfo.data, info.width, info.height,
                                       offsets, strides)
            finally:
                buffer.unmap(mapinfo)
            pts = "NOPTS" if buffer.pts == Gst.CLOCK_TIME_NONE else str(buffer.pts)
            print(f"FRAME phase=1 index={state['frames']} pts={pts} "
                  f"width={info.width} height={info.height} source_fmt=I420 "
                  f"hash_fmt=yuv420p md5={checksum}", flush=True)
            state["frames"] += 1
            if mode == 'stop' and state['frames'] == 30:
                state['stopped'] = True
                print('STOP_REQUEST frames=30 source_throttled=true', flush=True)
                GLib.idle_add(loop.quit)
            return Gst.FlowReturn.OK
        except Exception as exc:
            fail(f"sample callback: {type(exc).__name__}: {exc}")
            return Gst.FlowReturn.ERROR

    def message_received(bus, message):
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            fail(f"bus: {error}; debug={debug}")
        elif message.type == Gst.MessageType.EOS:
            state["eos"] = True
            print(f"EOS frames={state['frames']}", flush=True)
            loop.quit()

    inputs = {'buffers': 0, 'eos': False}
    def trace_input(pad, info):
        if info.type & Gst.PadProbeType.BUFFER:
            inputs['buffers'] += 1
        elif info.type & Gst.PadProbeType.EVENT_DOWNSTREAM:
            event = info.get_event()
            if event.type == Gst.EventType.EOS:
                inputs['eos'] = True
                print(f"INPUT_EOS buffers={inputs['buffers']} monotonic={time.monotonic()}", flush=True)
        return Gst.PadProbeReturn.OK
    pipeline.get_by_name('decoder').get_static_pad('sink').add_probe(
        Gst.PadProbeType.BUFFER | Gst.PadProbeType.EVENT_DOWNSTREAM, trace_input)
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", message_received)
    pipeline.get_by_name("source").set_property("location", sys.argv[1])
    pipeline.get_by_name("sink").connect("new-sample", sample_ready)
    try:
        print(f"PIPELINE decoder={decoder} mode={mode} instances=1 pts_unit=ns", flush=True)
        if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("PLAYING state change failed")
        loop.run()
    except BaseException as exc:
        state["failed"] = True
        print(f"ERROR run: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    finally:
        shutdown = pipeline.set_state(Gst.State.NULL)
        if shutdown == Gst.StateChangeReturn.ASYNC:
            shutdown, current, pending = pipeline.get_state(2 * Gst.SECOND)
        if shutdown != Gst.StateChangeReturn.SUCCESS:
            state['failed'] = True
            print(f'ERROR shutdown result={shutdown}', flush=True)
        for _ in range(16):
            error_message = bus.pop_filtered(Gst.MessageType.ERROR)
            if error_message is None:
                break
            state['failed'] = True
            error, debug = error_message.parse_error()
            print(f'ERROR shutdown bus: {error}; debug={debug}', flush=True)
        bus.remove_signal_watch()
    print(f"INPUT_END buffers={inputs['buffers']} eos={inputs['eos']} monotonic={time.monotonic()}", flush=True)
    success = not state['failed'] and ((mode == 'drain' and state['eos'] and state['frames'] == 60) or
                                       (mode == 'stop' and state['stopped'] and not state['eos'] and state['frames'] == 30))
    print(f"DECODE_END frames={state['frames']} result={(2 if mode == 'drain' else 1) if success else -1} "
          "decoder_instances=1 flushes=0 reopens=0", flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
