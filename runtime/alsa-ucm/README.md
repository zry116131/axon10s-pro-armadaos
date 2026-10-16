# Axon speaker and AMIC1 UCM candidate

Target: `/usr/share/alsa/ucm2/Qualcomm/sm8250/ZTE-Axon10s-HiFi.conf`, referenced by the existing Syntax 4 TFA card config. Requires the validated #64 capture DT and multi-DEC fix for microphone operation. This is a tested candidate, not installed by the repository or approved for kernels #57–63.

`ADC1 Switch` presence chooses the microphone-capable branch. The fallback branch retains the original speaker verb. MM2 backend must connect during HiFi verb activation, before ACP probes capture PCM; connecting only in Mic.EnableSequence causes -EINVAL and rejection of the entire HiFi profile. Mic enable/disable manages the remaining nine controls. Only enabling the backend does not power ADC/micbias; bounded live verification confirmed all four inspected DAPM widgets Off.

Application close may leave routing controls enabled. Verify PCM closed, PipeWire source suspended, and microphone DAPM Off after idle timeout. Disabling the HiFi profile additionally resets all ten controls. No gain, voltage, thermal policy or MBHC change is included.

Fallback #56 was also verified with real libasound and WirePlumber: Speaker only, no microphone source.

Real PipeWire tests on #64: repeated start/stop, 5-second known 700/1100 Hz response through simultaneous TFA playback, volume restoration, idle power-down and profile-off cleanup. This does not validate speech quality, other microphones, suspend, long-term stability or unexpected power-loss recovery. #64 still has startup-time AFE vote timeout and a first-stream SoundWire warning under investigation; do not install that kernel solely because UCM passes.
