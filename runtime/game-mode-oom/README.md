# Game-mode OOM session policy

This is the exact user-service drop-in already deployed on the phone. The original `OOMPolicy=stop` stopped the whole game-mode service after the kernel killed a game child. `continue` allows the remaining service processes to continue. It neither prevents OOM nor keeps the session alive if Steam or Gamescope itself is killed.

Install as the Steam-session user at `~/.config/systemd/user/gamescope-session-plus@steam.service.d/50-axon-oom-policy.conf`, preserving any existing file before replacement. Run `systemctl --user daemon-reload`, then read back `systemctl --user show gamescope-session-plus@steam.service -p OOMPolicy -p MainPID -p InvocationID`. Expected policy is `continue`; the session identity should remain unchanged. A session restart is unnecessary. The real phone already has this configuration; no redeployment was needed for this handoff.

To roll back, restore the previous drop-in (or remove this file only if it was newly added), reload the user manager and inspect the effective policy. Do not assume removing one file overrides other drop-ins.

Validation: earlier bounded synthetic user services demonstrated that `stop` terminates the service after a child memcg OOM and `continue` leaves the parent active. Current installed87 readback confirms `continue`, active game mode, `Delegate=no`, `memory.oom.group=0`, and no game-mode cgroup OOM events in the inspected boot. A real Silksong launch and Steam-directed exit passed previously, but this is not a real game OOM recovery test.

The live service has20 direct processes and no children; memory controllers are available but not enabled for a subtree. Do not impose a low MemoryMax on this shared service or move arbitrary running game PIDs and assume their existing memory charges follow. A bounded actual-game OOM test needs launch-time isolation and a reviewed data/recovery plan. A sibling test scope can validate game-exit recovery but does not exercise this service's parent OOM policy. Global memory-exhaustion survival remains unverified.
