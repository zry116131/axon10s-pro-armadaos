#!/usr/bin/env python3
"""Single-pipeline H.264 DRC comparison. Parent supplies an external timeout."""
import hashlib
import sys


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
    if len(sys.argv) != 2:
        print("usage: gst-compare.py INPUT.h264", file=sys.stderr)
        return 2
    try:
        import gi
        gi.require_version("Gst", "1.0")
        gi.require_version("GstVideo", "1.0")
        from gi.repository import Gst, GstVideo, GLib
        Gst.init(None)
        pipeline = Gst.parse_launch(
            "filesrc name=source ! h264parse ! v4l2h264dec ! videoconvert ! "
            "video/x-raw,format=I420 ! appsink name=sink emit-signals=true "
            "sync=false max-buffers=4 drop=false")
    except Exception as exc:
        print(f"ERROR setup: {exc}", file=sys.stderr, flush=True)
        return 1

    loop = GLib.MainLoop()
    state = {"frames": 0, "failed": False, "eos": False}

    def fail(reason):
        state["failed"] = True
        print(f"ERROR {reason}", file=sys.stderr, flush=True)
        GLib.idle_add(loop.quit)

    def sample_ready(sink):
        try:
            sample = sink.emit("pull-sample")
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

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", message_received)
    pipeline.get_by_name("source").set_property("location", sys.argv[1])
    pipeline.get_by_name("sink").connect("new-sample", sample_ready)
    try:
        print("PIPELINE decoder=v4l2h264dec instances=1 flushes=0 reopens=0 pts_unit=ns", flush=True)
        if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("PLAYING state change failed")
        loop.run()
    except BaseException as exc:
        state["failed"] = True
        print(f"ERROR run: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    finally:
        pipeline.set_state(Gst.State.NULL)
        bus.remove_signal_watch()
    success = state["eos"] and not state["failed"] and state["frames"] > 0
    print(f"DECODE_END frames={state['frames']} result={2 if success else -1} "
          "decoder_instances=1 flushes=0 reopens=0", flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
