# 视频候选补丁：未安装、未通过完整验收

在本项目7.2.6源码上依次应用：

1. `0005-axon-h264-input-dimensions.patch`：本机H264在bootstrap前提交已配置的输入尺寸。
2. `0006-axon-stock-h264-null-eos.patch`：历史#68阶段，为本机固件1.0.90/H264提交NULL EOS；必须继续应用下一项，NULL会留下结束阻塞。
3. `0007-axon-stock-h264-real-eos-buffer.patch`：#71将同一精确guard内NULL替换为4KiB真实DMA EOS缓冲，会话关闭后释放；其他机型和旧固件分支保持原状。

已验证补丁顺序逐字节重建#68实际编译的vdec.c。它们不单独启用视频：仍依赖Venus内置、Iris禁用、设备树及合法原厂固件配置；固件不随本仓库分发。这三个补丁均不带诊断日志。

#67的EOS地址双向对照及重新启动后首次解码支持第二项兼容修改。但#68更长测试仍有早期丢帧/腐坏和快速输入结束停滞，所以不能当作稳定视频支持安装或开启Steam硬件视频解码。当前安装系统仍为#56，详情见[试验记录](../../docs/VIDEO-DECODE-TRIALS.md)。

#71采用真实DMA缓冲后，600帧自然EOF快速解码逐帧一致并约2.3秒正常退出，日志确认EOS/空LAST；无诊断版也通过。测试同时使用独立FFmpeg v2 pending重试候选。中段起播仍有时间戳/帧数异常，故维持未验收状态。

DMA方案来源：David Heidelberg, [signal EOS with a real buffer](https://lists.openwall.net/linux-kernel/2026/09/28/2956)，2026-09-28。本项目将原提案范围收窄到Axon/IRIS2/固件1.0.90/H264。`core.h`布局变化要求重编所有Venus对象。
