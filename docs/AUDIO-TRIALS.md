# 音频采集适配试验（2026-10-17）

原厂匹配board-id=5的DTBO记录WCD938x家族、SoundWire TX/RX身份、GPIO32复位和供电。现有系统仅交付TFA9894扬声器后端；ALSA的capture前端并不证明麦克风后端完整。

主线WCD9380/9385共用同一驱动，实际variant在ASoC component probe读EFUSE决定。仅恢复SWR枚举而不挂WCD声卡link时，不能声称已确认具体variant。原厂广泛AMIC/DMIC路由也不代表每个通道实际装配。

## #57：依赖缺失

临时启用codec、RX/TX macro、两条SWR及内置驱动。DT仅五个status变化，保留TFA声卡、所有电压/复位/端口参数及#56显示/PON修复。未增加capture link、UCM或录音。

RX/TX macro等待LPASS pinctrl供应者，两条SWR继续等待macro。查明PINCTRL_LPASS_LPI/PINCTRL_SM8250_LPASS_LPI仍为未交付模块；此外已存在并启用的VA macro提供RX/TX必需fsgen时钟，其驱动也为模块。早期评估“VA节点关闭”已纠正。

此启动Wi-Fi板级数据读取失败，USB shell可用。原initramfs本身含有效board-2.bin.xz和精确匹配条目；不能把最终ENOENT简单归因于固件缺失。失败靠近switch_root窗口，竞态尚未证实。恢复#56后相同Wi-Fi芯片/board标识正常联网。

## #58：枚举成功，启动阻塞

仅将上述三项依赖改为内置，DT与#57相同。日志确认WCD938x codec已绑定SoundWire RX和TX。随后系统未进入真实rootfs，SSH和由systemd启动的USB shell不可用；只读USB日志仍持续输出。sdb至sdf完成识别，sda未记录完成分区扫描。不能据此断言整个UFS控制器失效、供电问题或IRQ冲突。

用户协助强制重启后已确认恢复已安装#56，SSH、Steam独立游戏模式与仅2GiB ZRAM正常。#57/#58均未写入启动分区，REC未修改。

尚无录音测试、实际麦克风路由或9380/9385型号验收。

## 供电边界

复位极性与原厂active-high/sleep-low行为一致；主线ACTIVE_LOW表示逻辑assert时拉低。S4A实测1800mV。BOB实测3032mV，与原厂codec请求3296mV不同；其为共享电源，本轮不改电压、不启用录音，后续采集前需单独核对影响。

## #59：早期 USB 诊断入口与一次完整启动

临时镜像保持 #58 的 DT、驱动配置和 #56 显示时钟修复，仅修改 initramfs 的两个启动脚本并加入早期 USB shell。原有 73 个 archive 条目保留，其余 71 个条目内容及元数据不变。离线 FIFO/PTY 测试覆盖无主机连接、断线重连和会话子进程清理；构建出现一次时钟偏差后重跑，最终构建无该警告。

实机一次启动通过：4.949 秒完成根分区挂载，6.039 秒开始退出早期 shell，9.417 秒确认会话成员清理完成，9.424 秒切换真实根目录。systemd USB 服务接管，事后未见早期 shell 残留。Wi-Fi/SSH、Steam 独立游戏模式、仅 2 GiB ZRAM 正常，两个 WCD SoundWire 端点均绑定。未增加音频采集后端或改变共享电源电压。

这次没有复现 #58 的启动阻塞，不能声称其根因已经修复。早期 shell 清理改变了切根时序，Wi-Fi 正常与此前固件读取竞态假设一致，但单次观察不能证实该假设，不能将清理延迟当作网络修复。#58 日志中的不完整 sda 初始化片段也不能单独证明块设备死锁。

#59 镜像 SHA256：`1037fbdf23597e6e90eb98fb43023da1d1cd93d07c17e3ee27f7ccab207bd164`。仅通过 fastboot 临时启动，未写入 boot 或 REC。测试后正常重启恢复已安装 #56，SSH、Steam 游戏模式和仅 2 GiB ZRAM 再次通过，systemd 无失败单元。后续应以早期任务栈定位复现的阻塞，并单独验证音频实际路由。

## 后续 component 绑定准备

源码审查发现 `sm8250_snd_init` 会经通用 jack helper 对 WCD capture link 调用 `set_jack`，从而启动 MBHC 耳机检测；不打开录音流并不能排除这个自动行为。现有 jack-type 属性只描述触点极性，没有可直接关闭此路径的 DT 属性。下一候选将仅在本机 `TX_CODEC_DMA_TX_3` 链路跳过 jack setup，保留其他板型、TFA、USB 和 DP 行为；component 自身的寄存器初始化与 IRQ 注册仍执行。

标准后端为 `TX_CODEC_DMA_TX_3 → WCD DAI1 + swr2 DAI0 + txmacro DAI0`。先验证 component 绑定，不添加模拟麦克风路由或录音流。现有主线机器驱动将后端固定为 48 kHz / S16_LE / 双声道，后续单模拟源测试须与 PCM 声道配置区分。

WCD 驱动不主动设置或校验 BOB 输入电压；1–2.85 V 的校验针对 MICBIAS 输出，不能用于证明 3.032 V 输入符合模拟规格。共享 BOB 还连接多组 PMIC 电源输入，本阶段保持其电压。厂商 mixer 配置未在已提取文件中找到，不能据此断言原厂镜像内不存在。

## #60：采集 component 绑定失败，未安装

临时候选在 #59 基础上加入上述标准 capture link 和本机 TX3 jack-setup 限制；原设备树属性不变，仅增加四个 link 节点及所需引用属性。配置仅改版本名，保留 #59 的早期 USB 入口。两次源码审查通过，编译无警告，镜像 SHA256 为 `cbfb64e1d9004f1ba7cc04f0eaec02f6ea2b56f7a5df8f5d728e9e45dd930fd5`。

实机进入真实根目录，USB/SSH/Wi-Fi 可用，但声卡以 `-ENODEV (-19)` 注册失败，ALSA 无声卡，原 TFA 播放亦不能使用。系统启动后对未绑定的 sound 设备做一次重新探测，仍失败；因此不能仅归因于首次启动时序。已保存组件/DAI 清单和完整可用日志，后续需要给 card/component probe 加精确诊断。大量 q6routing 缺路由消息不能单独确定第一失败点。本轮没有打开录音流，也没有调整电压。

另外确认 WCD variant 读取缺少独立错误检查：掩码操作可能将负错误码转换成合法型号。因此变体控件只能说明驱动选了哪个分支。已准备单独的 EFUSE 读取错误处理补丁，尚未编译或实机验证，不将其记为已安装修复。

后续源码审查找到高度匹配的原因：#60 的生成工具把 capture 子树放在 `/sound` 最前面，而 common/ASoC 按此顺序建立并探测组件。q6routing 因而先于 q6asm 的 MM_DL/MM_UL widgets 加载，缺失 widget 的返回值正是 `-ENODEV`。属性值相同的检查没有覆盖这个结构顺序约束。下一候选仅将 capture 子树追加到原 TFA 之后，并增加顺序验证；在实机复测前仍保留“疑似根因”结论。

#60 测试后已正常重启回 #56：TFA 声卡恢复，Steam 独立游戏模式 active，仅 2 GiB ZRAM，systemd 无失败单元。未将 #60 写入启动分区。

## #61：修正顺序后声卡绑定通过

对 #60 只移动 capture 子树至原 TFA 子树之后，并改变版本标识；DT 属性字节、其他节点相对顺序、capture 内部顺序和 initramfs 均不变。原始 token 子树移动可逆，逆向操作逐字节恢复 #60 DT。编译、打包和顺序敏感检查通过。临时镜像 SHA256：`772274e8322d845306c67416bb010eaa6cb98f432bb098f842566cad94f293f2`。

实机声卡成功注册，WCD 采集控件出现，#60 的缺路由错误与 instantiate -19 消失，支持其由生成工具改变节点顺序导致。保留 TFA 声卡，Steam 独立游戏模式 active，USB/SSH/Wi-Fi 可用，systemd 无失败单元。此次未做扬声器实听或录音验收。

`TX0 MODE` 显示 ADC_ULP1/2，`RX HPH Mode` 显示 CLS_H_HIFI，证明驱动选择了 9385 分支；鉴于现有 EFUSE 错误处理缺陷，不把这当作无条件型号确认。独立修复已完成 ARM64 单对象编译，无警告，尚未纳入 #61。

BOB 仍为 3032 mV，S4A 1800 mV；ADC1、ADC1_MIXER 均 off，TX DEC0 MUX 为默认值。未增加模拟路由或打开录音流，实际麦克风通路尚未验证。#61 仅临时启动，未写入 boot/REC。

#61 测试后已正常重启回已安装 #56，复核 TFA 声卡、Steam 游戏模式与仅 2 GiB ZRAM 正常，systemd 无失败单元。

## #62：EFUSE 读取错误处理与型号确认

加入返回码检查及成功读取日志；PM 引用在错误出口配对释放，其余 component 路径不变。EFUSE 寄存器本身为 volatile，不需要绕过 regcache。临时镜像 SHA256 `1d648c3ff9766fa519bb669ddd00d17107d3bda0502d43edeb3fd21a58d1d869`。

实机确认总线读取成功，EFUSE raw=`0x0a`、variant=`5`，对应 WCD9385；声卡仍正常注册，Steam 游戏模式、SSH 和 ZRAM 正常。最小修复保存在 `runtime/kernel-patches/0002-wcd938x-check-efuse-read.patch`，诊断日志未混入该最小补丁。尚未安装至 boot。

## #63：首次限时采集与多通道状态缺陷

仅新增 AMIC1→MIC BIAS1、ADC1_OUTPUT→TX SWR_ADC0 两条路由，保持 #62 源码与所有供电参数。候选 SHA256 `8c3153eade9955500c722474f2d86a039205b4057cd02e9d3eef69c7a33f589c`。

受控测试先验证声卡/PCM 身份与其余输入关闭，使用 MM2、48 kHz/S16_LE/双声道；ADC1 为 0 dB，TX0 ADC_NORMAL，DEC0/DEC1 同选 ADC0。3 秒采集正常退出，取得 288000 个交错 s16 样本（每声道144000）。录音期间 MIC BIAS1/ADC1 的 DAPM 为 On，结束后 Off，临时原始 PCM 已删除，只保留统计。两声道 RMS 约3.27与25.06、峰值15与786，不一致；未施加已知声音，不能认定实体麦克风或音质验收通过。期间记录一次 SoundWire read-enable-valid mismatch，另有稍后的 DPU event overflow，因果关系未确定。

恢复检查发现 `TX_AIF1_CAP Mixer DEC0` 无法关闭，重试仍回读 on，其余已改控件恢复，模拟偏置已关闭。源码复现原因：TX mixer 使用单个 `active_decimator` 管理多个 mask 位；关闭最后选择的 DEC1 后将其设为 -1，导致关闭仍启用的 DEC0 时提前返回。重复启用非最后选择的 DEC 还可能错误累加计数；mute 路径也只处理一个 DEC。下一步修复以位掩码管理的幂等状态及多 DEC mute，再做同配置复测。此处与双声道幅度差异可能相关，尚未验证。

#63 测试后正常重启回已安装 #56，TFA 声卡、Steam 游戏模式、仅 2 GiB ZRAM 正常，systemd 无失败单元；未写入 boot 或 REC。

## #64：多 DEC 修复与 AMIC1 已知声音响应

新增 LPASS TX 修复：mixer put 按目标 mask 位幂等更新，mute 遍历该 AIF 的所有活动 DEC，移除单一 active_decimator 状态。实际修改函数抽取后经过 ASan/UBSan：真实 AIF 索引0–2、12288组状态变化/重复操作、两种关闭顺序、AIF隔离和mute位集合均通过。另通过真实内核单对象编译及完整镜像验证。该补丁不声称解决活动流期间任意并发重路由的原子性。

镜像 SHA256 `931f2afdac46420126834aa9fdcc56c362505c53fa6f98d46d71d16ba16fa5ea`；DT、供电、路由与 #63 一致。相同3秒采集配置实机复测通过，10项控件全部恢复；两个通道RMS约23.9075/23.9103，均峰值753，较 #63 明显接近，样本并非逐位完全一致。MIC BIAS1/ADC1结束后均Off。

已知声音试验：初次在用户约1%的系统音量下响应不明确，不作为通过依据。随后临时将系统音量设50%，播放数字峰值0.04FS的700Hz/1100Hz各1秒测试音，以MM2采集5秒。对应频率能量相对前置窗口分别约上升39dB/52dB，结束后下降，两通道趋势一致；播放与采集均正常退出。这验证了 AMIC1 基本声音采集通路，尚未验证其他麦克风、语音质量、长时录音或休眠恢复。

测试使用系统现有 paplay 经 PipeWire 的兼容服务输出，确认默认输出是手机 TFA 扬声器。精确音量值945/945恢复成功，全部10项控件恢复，模拟偏置关闭；原始PCM及生成的测试音均已删除，只保留统计。最小内核修复保存在 `runtime/kernel-patches/0003-lpass-tx-track-all-active-decimators.patch`。

#64 仍为临时启动，未写入 boot/REC。下一步添加应用可用的 UCM 采集启停序列，保留已有扬声器配置后再决定持久化。

测试后已正常重启回 #56，TFA 声卡、Steam 游戏模式和仅2GiB ZRAM正常，systemd无失败单元。

## #64 复测：启动依赖与 UCM 应用层验证

重复临时启动发现 VA macro 首次 LPASS_HW_MACRO_VOTE（block 3）超时 `-110`，使 RX/TX macro、SoundWire 和整张声卡等待。系统启动完成后仅重新探测未绑定的 `3370000.codec`，声卡恢复。下一次临时启动直接成功。确认启动存在时序敏感性；首次 APR 响应超时根因未定，手动 reprobe 仅为恢复手段，不能据此批准固化。

初版 UCM 仅在 Mic.EnableSequence 连接 MM2 backend，导致 ACP 在设置 HiFi verb 后探测采集 PCM 时返回 `EINVAL`，拒绝整个 HiFi profile。单变量实机对照：backend off→PCM open -22，backend on→0，恢复 off→-22；四个麦克风 DAPM 检查点始终 Off。修正版将 backend 连接提升至条件化 verb，Mic 启停负责其余九控件；无 ADC1 控件时保持原扬声器行为。

修正版通过真实 libasound 解析与 PipeWire 枚举。两次限时应用录音均进入 RUNNING，停止并等待后 PCM closed、source SUSPENDED，MIC BIAS1/ADC1/ADC1_MIXER/ADC1_OUTPUT 全 Off。另一次通过 parec/paplay 完成完整5秒、48kHz双声道应用采集，底层选择 S24_LE，交付 s16；700/1100Hz 对应时间窗能量明确上升并在结束后下降，两通道一致，播放/采集均返回0。系统音量精确恢复945/945，原始PCM与测试音删除。关闭HiFi profile后十控件全部回到关闭/零值。

首次应用录音时记录一次 SoundWire read-enable-valid mismatch；功能测试成功不能排除该警告的稳定性风险。UCM 候选见 `runtime/alsa-ucm/`。测试通过临时 `/run` 配置和用户服务环境覆盖完成，未修改系统 UCM 文件，覆盖已撤销；未写 boot/REC。语音质量、其他麦克风、长期运行、休眠和非正常断电恢复仍待验证。

随后恢复 #56，修正版 UCM 再经真实 libasound 和 WirePlumber 回退分支验证：仅 Speaker/sink 与其 monitor，无 Mic/source。测试覆盖已撤销，原系统 UCM 保持不变。#56 TFA 声卡恢复，systemd 无失败单元。

完成上述双版本验证后，UCM 修复已持久化至系统配置，SHA256 `1e6d8b8dccabecc385c41cc362b9780833741550e791833b21a24663b005922a`。替换前逐字节核对原文件并备份到 `/var/lib/axon-audio-backup/ZTE-Axon10s-HiFi-speaker-only.conf`，原子替换后校验新文件与备份。无环境覆盖的真实 UCM 加载通过；#56 仍仅有扬声器通道，Steam 独立游戏模式 active、仅2GiB ZRAM、无失败系统服务。采集内核仍未安装，boot/REC未改动。
