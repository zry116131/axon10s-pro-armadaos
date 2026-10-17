# Axon H264 compatibility profile (#91)

This optional profile exposes H264 hardware decoding while excluding the other compressed codecs from this Venus decoder. It is a temporary, tested compatibility profile; VP8/VP9 firmware decoding remains unresolved. VP8/VP9 playback in the tested CEF session used software fallback. The profile affects every client of the decoder device, not only CEF.

## Reproducible patch chain

Use this project's Linux 7.2.6 source and apply these patches in order:

1. `0005-axon-h264-input-dimensions.patch`
2. `0006-axon-stock-h264-null-eos.patch`
3. `0007-axon-stock-h264-real-eos-buffer.patch`
4. `0009-axon-h264-compat-profile.patch`

`0008-q6afe-isolate-vote-transactions.patch` concerns audio and is independent of this video chain. Patch 0009 modifies only `drivers/media/platform/qcom/venus/vdec.c`; retain the `core.h` change from 0007 and rebuild all Venus objects together.

SHA256 verification:

| File/stage | SHA256 |
| --- | --- |
| Initial vdec.c | `6e402d6a3d6462c44291ca1839ae5bb314beefa01f731f551f0d889a23255b4f` |
| Initial core.h | `c21601585dca86dd4078ac212a0b9df94fb24f62fc76b94e424f1eff512a8ad9` |
| vdec.c after 0005 | `178163189292cf5aa65e1e7cfde0b1600c57bf4e1d61e7fc6d361ff5425e9def` |
| vdec.c after 0006 | `81e171354a9c0bfd840deebf66c6653d06a5e6e40e879ccaedfd763a20cf22a5` |
| vdec.c after 0007 / input to 0009 | `f60cb0f2c824ea1eb4b5a45939f99725cf65f46cbf866f90d8298697ff92b804` |
| vdec.c after 0009 / tested #91 source | `915e26bcf532e2218fbe106dcd406c9acf374e1c002f6873bf7af850e6476ccf` |
| core.h after 0007 | `7066a254d4567966c2f5147948af83b53ca2dec336e592187a937df512ed734f` |
| 0009 patch | `598d69532ddf4ee3a6edf7222d1f4bfc1b8c001ed56658c7c35f2d2f00b971d1` |

In a disposable source tree, `git apply --check` followed by `git apply` succeeded for every step. The final vdec.c and core.h were compared byte-for-byte with the #91 candidate and #71 core header, respectively.

## Configuration and behavior

The default-false boolean `axon_h264_compat` has mode 0400. For the tested built-in driver, explicitly add `venus_dec.axon_h264_compat=1` to the boot command line. It is readable but cannot be changed through sysfs at runtime. A modular build would set it at module load; that configuration has not been validated here.

The profile requires all of: `zte,axon10s-pro` machine compatibility, `qcom,sm8250-venus` core DT compatibility, decoder session type, and HFI6. It does not wait for asynchronous firmware-version reporting, so an unknown version cannot bypass an explicitly enabled profile. It still requires the original H264 capability check.

With the profile active, compressed OUTPUT_MPLANE enumeration and lookup retain only H264. S_FMT rejects the original non-H264 OUTPUT_MPLANE fourcc with EINVAL before queue access or TRY_FMT substitution; this includes unknown formats. Rejected requests leave the instance and format unchanged. EINVAL intentionally takes precedence over EBUSY for these requests. TRY_FMT retains its normal H264 suggestion for unsupported compressed formats; callers must honor its returned fourcc. Raw capture checks/fallback, encoder code, and default-off behavior remain unchanged. Invalid buffer types continue through the original ioctl validation path.

The patch does not enable Venus by itself. The tested configuration uses Venus built in, Iris disabled, matching device tree, and legitimate stock firmware; firmware is not distributed here. Enabling Steam hardware video decoding is a separate policy change.

## Validation and limits

Offline tests extracted the actual candidate gate, format array, lookup/enumeration, TRY_FMT and full S_FMT functions. Clang Werror with ASan/UBSan passed unknown-firmware, gate mismatch/default-off, H264 capability failure, all rejected codecs, unknown format, all raw capture formats, invalid-type path, and rejection-without-mutation/helper-call cases. Host stubs do not establish kernel ABI or concurrency correctness.

On the temporary #91 boot, the enabled parameter was confirmed. A bounded ioctl probe verified the decoder advertised only H264 and separately rejected VP8, VP9, HEVC and an unknown fourcc with EINVAL; G_FMT remained H264 after each rejection. An initial attempt on an encoder node was correctly rejected by QUERYCAP identity checks before S_FMT; validation used the confirmed decoder node.

During a temporary Steam hardware-video setting of true, exact Blob-associated CEF player metadata showed:

| Fixture | Frames | Decoder / platform | Playback |
| --- | ---: | --- | --- |
| H264 | 90 | V4L2 / true | ended, zero dropped |
| H264 720p | 90 | V4L2 / true | ended, zero dropped |
| H264 720p | 600 | V4L2 / true | ended, zero dropped |
| VP8 | 60 | VpxVideoDecoder / false | ended, zero dropped |
| VP9 | 60 | VpxVideoDecoder / false | ended, zero dropped |

Player video-track codec properties matched each requested codec. Startup and post-test kernel captures showed no matching SFR/Err_Fatal messages. The Steam setting was restored to false afterward. These bounded tests establish the observed routes and playback completion for these fixtures; they do not establish every stream/profile, visual correctness, audio synchronization, seeking, long-run reliability, or absence of every possible firmware error.

#91 was booted temporarily and has not been persistently installed. After video testing, native s2idle completed a 28.022-second RTC-woken cycle (suspend success count 0→1, failure count 0), with the Steam page responsive and probe elements removed. A further 90-frame H264 fixture after resume completed through V4L2VideoDecoder/platform=true with zero dropped frames. The hardware-video setting was false at this latter check: the existing CEF process retained its decoder path, so persistent-setting changes must not be treated as immediate process reconfiguration. The setting was verified false again before returning to the installed kernel. These tests do not establish deep-sleep residency or standby power consumption.

Normal reboot returned installed #87 (boot44909f32-01ab-49c7-91e3-23a82b33e25f). USB and SSH confirmed system running, independent game mode active, taint0, boot disk read-only, no failed system units and only2GiB ZRAM. Steam readback confirmed hardwarevideo=false/webviews=true. No #91 boot-partition or REC writes occurred.
