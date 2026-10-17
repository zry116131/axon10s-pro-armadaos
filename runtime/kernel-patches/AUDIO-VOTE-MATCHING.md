# Q6AFE vote transaction isolation (candidate #90)

`0008-q6afe-isolate-vote-transactions.patch` is an incremental patch **after public patch 0004**. It is not the private #89-to-#90 finalization patch. It touches only `sound/soc/qcom/qdsp6/q6afe.c` and reproduces the exact source used for temporary candidate #90.

## Exact inputs and application order

The checked Linux 7.2.6 source file has these SHA-256 values:

| Stage | SHA-256 of q6afe.c |
| --- | --- |
| Before public 0004 | `77ea51ffe6ed5dbc8f6f431e9a721ee00e598555aa5b2bd1f3d2828b743c0ff4` |
| After public 0004; required input to 0008 | `ee08247bdaffdfe169c7f701f4d9db1c08ff9f7247399c7f3ed4b535d2cd8ff8` |
| After public 0008; final #90 source | `54b9d5d4bc0863e6621e5a91ae739f3e7a97c905e7582de6a2fcc34f6bcce69b` |

Patch 0008 SHA-256: `ce927d9237e95a34cd2fccd6d8b84bb26612333ad55092ec4a1e0e142e02b8e5`.

From the kernel source root, using a local checkout of this repository:

```sh
# Set patches to this repository's runtime/kernel-patches directory.
sha256sum sound/soc/qcom/qdsp6/q6afe.c
git apply --check "$patches/0004-q6afe-preserve-vote-handle.patch"
git apply "$patches/0004-q6afe-preserve-vote-handle.patch"
sha256sum sound/soc/qcom/qdsp6/q6afe.c
git apply --check "$patches/0008-q6afe-isolate-vote-transactions.patch"
git apply "$patches/0008-q6afe-isolate-vote-transactions.patch"
sha256sum sound/soc/qcom/qdsp6/q6afe.c
```

Compare each hash with the table. If 0004 is already applied, begin at its expected output hash and apply only 0008. Do not force a mismatching base. Public patches 0005–0007 address Venus and do not change this file; the normal numbered series may be retained.

Validation performed in an isolated temporary source tree: `git apply --check` and actual application both succeeded for 0004 and then 0008, with no stderr. Each intermediate file was compared byte-for-byte with its expected source. The pre-0004 hash was independently checked against the kernel source tree. No shared kernel build or device was changed for this packaging step.

## Resulting behavior

Patch 0004 fixes vote handle parsing and synchronous delivery. Patch 0008 additionally isolates vote replies from ordinary AFE clock/port results using a separate waitqueue, pending/completion state and spinlock. A callback never retains the caller's output pointer. Normal request serialization remains under the existing request mutex; callbacks do not take that mutex.

Each vote receives a globally allocated header token from `0x10000` through `INT_MAX`. The callback accepts only a matching pending token, once. Tokens do not wrap: exhaustion returns `-EOVERFLOW` before sending or changing the caller's output. The sequence is global across AFE instances. Payload hardware-block identifiers, client data and unvote packets remain unchanged.

An uncertain send failure or timeout permanently poisons new vote transactions for that AFE instance. Subsequent votes fail without sending; successful existing handles can still be unvoted through the unchanged path. There is no automatic retry or fallback to hardware-block tokens. A timed-out firmware operation may have allocated an unknown resource; this patch does not guess a cleanup handle.

The final source always uses unique tokens. It contains neither the experimental `vote_transaction_tokens` switch nor the bounded `vote_observe` diagnostic logger from earlier candidates.

## Validation scope

Offline tests extracted actual functions from the final source identified above. Host Werror/ASan/UBSan tests covered unique allocation across instances, a successful A followed by B receiving A's duplicate, wrong-token rejection, correct completion, saturation with zero sends and unchanged output, payload/opcode preservation, timeout/send-failure poison, expired stack/freed output, invalid calls with zero sends, and an ordinary clock transaction receiving a late vote. An independent host process used four real threads to allocate 40,000 unique contiguous tokens without resetting the counter. These harnesses were used during development and are not included in this two-file patch handoff. Host mocks do not prove kernel IRQ behavior or ARM64 memory ordering. The final source also passed isolated AArch64 object compilation; this packaging step did not repeat a kernel build.

Temporary #89 exercised existing boot-probe vote requests: firmware echoed tokens 65536 and 65537 and both requests completed. That establishes those two observations on the tested firmware, not support for the whole token range or every firmware version. No artificial resource requests were sent for that check.

Temporary #90 booted with the final source. A corrected low-stimulus audio test completed playback and approximately 4.94 seconds of capture, with the expected 700 Hz then 1100 Hz windows above baseline. No endpoint clipping was found in the analyzed windows; this does not prove an unclipped analog ADC, physical sound quality, or two independent microphones. The first audio attempt failed because of the test harness's file-size restriction; the corrected attempt retained an unlocalized cleanup error, followed by independent cleanup verification. Neither is evidence of a Q6AFE transaction failure. Two RTC suspend/resume checks passed operationally, with UI and connectivity checks afterward. These do not establish SoC deep-state residency or power consumption.

SoundWire read-enable-valid mismatch remains observed at capture startup and is not fixed by this patch. The device was returned to the installed #87 baseline. **#90 was tested by temporary boot and was not installed persistently.** Reproducing the full audio image also requires the broader audio dependency/configuration/DT work.

## Lifetime and unresolved boundaries

Token uniqueness is limited to the lifetime of this **built-in driver image**. Recreating an AFE instance does not reset the global counter; reboot does. A module unload/reload would also reset module storage and is outside the validated assumptions. Driver/APR teardown synchronization, in-flight callback drainage, ADSP reset and firmware resource cleanup have not been validated. Do not use unbind/rebind or an ADSP restart as a claimed safe recovery procedure based on these tests. A new software instance alone does not prove that old firmware activity has drained.
