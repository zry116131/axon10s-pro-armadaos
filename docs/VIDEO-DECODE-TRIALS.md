# 视频硬解试验记录（2026-10-16）

当前安装版本为保留 #45 视频配置的 PON 与显示时钟修复版 #56，仅启用2 GiB ZRAM，旧磁盘swap已停用。#46至#53均只通过fastboot临时启动，未固化，REC未修改。视频硬解尚未验收，Steam硬件视频解码仍关闭。

## 已定位

- #44/#45设备树禁用Venus，媒体驱动配置为模块却未交付模块，因此没有视频节点。
- 新候选需将Venus及依赖内置，并禁用Iris；同时启用Iris会使Venus源码排除SM8250匹配项。
- 通用固件在PAS初始化返回-22；原厂modem分区只读取得的本机MDT和分片可使驱动绑定。所有必需分片长度及5MiB内存跨度已校验，未修改安全认证流程或保留区。
- #47直接从initramfs加载原厂固件后，启动即可出现视频编码/解码节点，未出现#46失败后手动重新探测时的IOVA0错误。但节点存在不等于解码通过。
- #47真实H264测试触发Venus固件内部异常（SFR Exception）；输出帧校验文件为空，测试失败。此前#46测试还出现FFmpeg断言退出。
- 固件故障恢复还暴露了启动文件与真实根文件系统固件不一致：切根后重载通用固件会再次失败。#48已使用本机专用firmware-name，并在两处部署相同原厂文件。

HFI通知0x21001属于EVENT_NOTIFY，系统故障允许没有关联session；不能从session_id ff或广播的session error 0直接推断协议根因。后续只增加默认关闭的收发包诊断，定位首次异常前的命令，不盲改协议。

#46之后曾出现一次原因未确定的重启；#47结束后主动返回#45时连接恢复延迟。最终已通过SSH确认返回#45，USB和两级swap正常。本阶段没有证明视频固件异常与此前Steam CEF GPU冻结是同一个问题。

## #48 诊断与恢复

#48临时启动和视频节点创建通过；30帧合成H264测试未通过，限时终止返回137。原厂固件为VIDEO.VPU.1.0-00090-PROD-1。日志显示内部SCRATCH_2需求32768字节、实际提供0；当前host计算遗漏该类型，零大小被分配路径跳过。当时提出缺少HFI SCRATCH_2的假设；#49查询结果不支持该对应关系，已撤回，不能将私有变量名等同协议缓冲区类型。

本轮完整包日志经低速串口输出，导致LOAD_RESOURCES超过驱动1秒等待窗口；后续0x1006代表错误状态下操作，不能直接认定为原始崩溃根因。#49已只查询固件需求并在LOAD_RESOURCES前退出。

测试后ext4 journal写入阻塞，SSH登录及普通重启受影响，USB调试shell仍可用。紧急同步/只读重挂载未报告完成，最终通过USB触发强制重启。随后确认恢复#45，ext4报告recovery complete，实际文件写入和sync成功，两级swap正常。这不等于完整离线文件系统检查通过。#48未安装，故障与视频测试的因果关系尚未确定。

## #49 查询结果

固件需求查询成功，返回类型1、2、3、6、7、5，没有8。解析器不筛掉8，不能通过硬编码新增SCRATCH_2来修复。#48提交的内部6/7/5缓冲区大小分别等于或大于#49查询值，但跨启动对比不能替代同会话验证。下一步核对初始128×128输入与320×256输出配置、双输出格式/尺寸的关系。

查询主动停止解码启动，FFmpeg虽返回0但没有输出帧，不能视为硬解成功。测试后真实文件写入和同步成功，并正常重启回#45。

## #50/#51 输入尺寸对照

同会话对照确认host按实际capture尺寸计算，固件仍处于128×128初始解析状态。上游有意采用这一bootstrap，差异本身不证明错误；最低数量18与已声明数量32也有正常协议解释。

#51临时开关在初次配置前发送实际压缩流尺寸，固件接受并更新需求。随后H.264三组短测全部逐帧匹配软件解码：320×240的30帧、含B帧640×360的60帧、含B帧1280×720的60帧。

较长测试仍失败：300帧循环片段的实时/快速输入、以及360帧单段视频在结尾前停止的实时测试，均再次触发原SFR异常和FFmpeg断言134。主机decoder与parent强制保持active、暂停计数不变时仍失败，之后恢复auto。因此这只是部分改善，尚非完整修复；不能排除固件内部功耗路径等问题。异常退出后空校验文件可能是缓冲尚未落盘，不代表解码器必定未输出任何帧。

## #52/#53 收窄验证

#52移除诊断查询并将尺寸修正限定为本机H.264；320×240的30帧正常退出并逐帧匹配软件解码。1280×720 High+B单段长视频仍出现capture POLLERR及FFmpeg断言，最终超时强杀137，未通过。

#53请求固件关闭power-plane-control，成功入队不等于固件确认。长测无完成帧并超时；重新启动后同时保持host parent/decoder active的对照仍失败，暂停计数不变。首次host-PM对照已有runtime错误，已排除其证据。原SFR未出现，但出现idle等待超时，不能认定修复。

两者均未安装，已正常重启返回#45。Steam硬件视频解码保持关闭。后续需核对原厂固件与主线HFI生命周期的差异，不能将短片通过作为稳定硬解交付。

## 菜单冻结对照

同一#45上进行了glthread开/关两组约30秒菜单左右浏览测试。两组均无新增GPU退出，rAF回调常见间隔接近；未复现原冻结，已撤销试验设置。该短测不能宣称修复，也不能将rAF回调等同屏幕帧率。

原始日志、设备固件和分区备份只保留在私有维护环境，本记录不发布固件或个人数据。

## 长测输出边界取证准备（2026-10-17）

新增 `runtime/diagnostics/check-video-boundary.py`。同一文件先软件解码，再在明确匹配的候选内核上运行硬解；默认仅软件，不循环输入。每帧立即刷新framemd5，保留包PTS/DTS、文件位置和进度；过滤强杀时可能留下的半行。探测失败、软件超时或帧数不足时不进入硬件步骤。每个解码进程限45秒，随后有界TERM/KILL；无法退出的内核阻塞任务会记录returncode为空，不能宣称强杀保证成功。禁用核心转储并限制单个输出文件大小。

当前#56上的验证：现有12秒360帧H264素材，软件输出前300帧成功，最后PTS=299；另一次实时软件解码在2秒强制终止后仍保留57条完整帧记录。该结果只证明取证方式有效，没有执行硬解或证明固件修复。

素材检查：3秒90帧样本仅开始有I帧，12秒360帧样本在0和8.333333秒有I帧。#51后者两次实时失败距测试开始约9.82、9.81秒。时间接近不足以证明IDR导致故障；B帧重排、输入预取和初始化耗时都会影响对应关系。下一步应以此工具获得硬解最后成功输出PTS，再核对输入包；必要时才加入DPB所有权转换的窄诊断。

源码审查另发现需核对的计数关系：主机声明OUTPUT/OUTPUT2为VB2_MAX_FRAME，DPB按主机最小数分配；旧日志主机18、固件查询32可能受主机声明影响，尚不能认定为少分配。不得据此直接扩大缓冲数量。

## #66 精确帧边界实测

临时内核 `7.2.6-axon10s-video-boundary1`，镜像SHA256 `d1925cf39d4121106eb1c4739621c5bb34ee10f60f0b547a36cedb46342f21ca`。以#56配置、设备树和DSI修复为基底，恢复#52的H264输入尺寸修改和Venus依赖，使用#48本机固件initramfs；没有#53功耗修改或#65音频修改。最终Image中设备树和initramfs逐字节验证通过，节点顺序保持，USB与PON属性保持。#48 initramfs原USB程序与#44一致，不包含#59 early shell。未写入boot/REC。

同一12秒360帧720p H264文件，两组均实时输入、立即刷新逐帧输出：

| 测试 | 软件参考 | 硬件结果 |
| --- | --- | --- |
| 截取前300帧 | 300帧正常退出 | 300条输出，PTS 0..301，缺16和18；PTS17、19..249共232帧内容错误；250..301与完整软件参考一致；约10.05秒后SIGABRT |
| 读到360帧/文件结尾 | 360帧正常退出 | PTS0..353连续354帧全部逐帧一致；约11.84秒后SIGABRT，未输出末6帧 |

两次仍有原SFR `IP=0x3bc8c FA=0 cause=6`，之后固件恢复。第一组有driver decode error/corrupt decoded frame，第二组无该提示但仍capture POLLERR及FFmpeg断言。第二组是在第一组固件恢复后的同一次启动，不等价于独立冷启动复测。

证据改变了后续方向：原“长测失败”至少包含结束附近的异常；完整组证明跨过第二IDR后仍能持续正确输出，不能把IDR本身认定为SFR原因。第一组参考链损坏在PTS250的IDR恢复，与最终结束异常可能是不同阶段的问题。下一步需核对EOS/STOP/drain及DPB归还的事件先后；仍未证明具体驱动根因，也不能交付稳定硬解。

测试后正常重启，SSH和USB shell均确认返回#56，2GiB ZRAM启用。未安装#66。

## #67 EOS 单变量对照：定位结束解码崩溃

临时内核 `7.2.6-axon10s-video-eos1`，镜像SHA256 `e90b96e83402a022e0d1125fa30f3969f18e5a0b22a5c91b9479246034e578d8`。在#66基础上只添加默认关闭的EOS空地址诊断开关及一条EOS日志；开关仅本机IRIS2、实际解析版本1.0.90生效。每次仅在前一解码进程退出后切换，未改缓冲区分配、尺寸或电源行为。

| 顺序 | EOS地址 | 同一360帧素材测试 | 结果 |
| --- | --- | --- | --- |
| 首次启动A | 0xdeadb000 | 实时完整文件 | 354帧正确，SIGABRT；EOS后约9ms原SFR |
| 同启动B，固件恢复后 | 0 | 实时完整文件 | 360帧逐帧一致，退出0，无新增SFR |
| 同启动反向A | 0xdeadb000 | 快速完整文件 | 341帧正确，SIGABRT及原SFR |
| 重新临时启动，首次解码B | 0 | 实时完整文件 | 360帧逐帧一致，退出0，无SFR |
| 同次新启动B | 0 | 快速截取前300帧 | 300帧逐帧一致，退出0，无SFR |

实机EOS日志确认版本为1.0.90，默认确实提交dummy地址，开关开启确实提交0。两方向结果与新启动首会话验证支持本机H264 EOS地址兼容问题，不能再将这些结束异常归为持续解码算力不足。快速与实时输入的返回帧数不同，也说明不能把最后输出PTS直接当作固件收到EOS时的全部处理进度。

上游历史已有[旧SM8250固件NULL EOS处理](https://lkml.iu.edu/hypermail/linux/kernel/2511.3/00452.html)，但版本门槛为1.0.87，本机1.0.90不进入该分支。另一个针对SDM845的real-DMA-buffer提案仍[要求SM8250回归验证](https://lkml.iu.edu/2610.1/02829.html)；本轮没有套用该更大修改。

下一正式候选将去掉诊断开关，仅追加本机、IRIS2、精确1.0.90、H264会话的NULL分支，原旧版本行为不变。该正式候选尚未构建/启动/安装。#66首GOP偶发缺帧和腐坏没有完成根因定位；这些通过结果也不证明其他编码、分辨率、seek、长时间循环或Steam内硬件视频功能通过。Steam硬件视频解码继续关闭。

#67测试后已正常返回#56；SSH确认游戏模式active、仅2GiB ZRAM、无失败系统服务，USB串口重新枚举。

## #68 无诊断开关候选与600帧测试

`7.2.6-axon10s-video-eosfix1`，镜像SHA256 `1fc6b09fa618291ccd7cda87cdf809c758d9f58850286def71ec0b6e29ec7895`。已编译并临时启动，设备树、#48固件initramfs、#56显示/PON/USB保留检查通过；诊断开关与日志已移除。只对本机IRIS2、固件精确1.0.90、H264会话扩展NULL EOS，其他分支保持原样。公开候选补丁0005、0006可逐字节重建实际vdec.c，但完整视频功能未验收。

新素材为20秒600帧720p High H264（libx264 veryfast、3个B帧、每60帧关键帧，SHA256 `9f14ce94a39d86b5f0ed62d34a7c2abdcc42785f1a1c90b9e5c53bbe40f53de1`）：

- 首次会话实时输入：软件600帧通过；硬件退出0但仅598帧。缺PTS16、18；PTS17及19..59内容错误；下一IDR（60）开始恢复，后续到599正确。无SFR，有driver decode error/corrupt decoded frame。正常退出不等于视频正确。
- 同启动快速输入：软件600帧通过；硬件最终600帧逐帧一致，但进程45秒未退出，TERM后仍未退出，随后KILL，约47.12秒返回-9。中途进度曾停在531；最终600帧可能在超时处理期间才完成，不能宣称实时完成，也不能视为drain通过。无新增SFR。

结果支持EOS dummy地址引起的SFR已得到定向缓解，但仍存在独立的初始帧损坏和结束停滞，#68不安装。未进行seek测试。

源码审查没有发现tag重叠：用户capture范围0..31，DPB从32起分配；V6动态模式按FTB提交，跳过静态注册是既有设计。下一诊断应记录首约80个原始FBD的stream/tag/error/flags/PTS/长度，以及DPB首次提交和owner归还，区分固件丢帧与主机匹配异常。不能未经证据直接修改18个DPB或32个声明计数。

#68测试后已正常返回#56，SSH确认游戏模式active、仅2GiB ZRAM、无失败系统服务，USB串口重新枚举。

## #69 有界帧与DPB记录：健康参考，未复现

临时内核 `7.2.6-axon10s-video-frame1`，镜像SHA256 `bc825272125769d176a68922fd31d13959dd2e5abf7a3c34207bf0cdbed234c7`。保留#68全部功能，仅加入本机IRIS2诊断：每启动最多EBD80、FBD128、DPB分配32、提交128、归还128条；用饱和原子计数控制上限，不修改数量、标签、原状态赋值或返回路径。解码前关闭ignore_loglevel并将console level设4，避免信息日志经低速串口输出；printk/journal仍有开销。

同一600帧素材、同一实时输入、首次解码：600帧全部逐帧一致，软件/硬件正常退出，未复现#68缺帧。本次仅是诊断环境中的健康参考，不能宣布画面损坏修复。

实际取得FBD128、EBD80、DPB分配18、提交18、归还18条。无非零固件error、无DPB未匹配归还。PTS16和18对应固件返回的用户tag分别17和16，长度1413120、flags=0、error=0；PTS不能当成缓冲编号。18个DPB约99微秒内提交成功，首EBD在约2.6毫秒后；DPB归还全部发生在结束阶段，未观察到开头归还与重新提交竞争。

由于加入日志后此次通过，下一步需降低诊断开销，保留同一取样范围再取失败样本。当前配置只有TRACING_SUPPORT，未开启FTRACE/TRACING；不能直接将dev_info改成trace_printk而假定有记录。若使用延迟格式化记录，必须保存DMA地址数值，不保存可能失效的对象地址指针。此阶段不改DPB数量、不安装视频候选。

#69测试后已正常返回#56，USB shell与SSH确认内核；游戏模式active、仅2GiB ZRAM、无失败系统服务。

## #70 缓存式记录：复现初始缺帧，继续核对输入路径

临时内核 `7.2.6-axon10s-video-buffered1`，镜像SHA256 `ec5ad4fd87c2f77a612b64228eace39c26a3cde91682825ed60b9a8ea9bd37a9`。在#69基础上改用有界内存缓存保存诊断事件，事件发生时格式化到缓存，冻结后集中输出，降低逐事件日志对时序的影响；未据此修改DPB数量或所有权规则。

同一600帧素材、实时输入、首次解码再次复现#68现象：软件600帧、硬件598帧，均正常退出0。硬件缺PTS16、18；PTS17及19..59内容不符，PTS60起恢复到末帧599。无SFR。降低日志开销后能够重现，说明#69的单次健康结果不足以证明修复。

缓存记录共244条，overflow=0、truncated=0：EBD80、FBD128、DPB分配18、提交18。本次未记录owner归还，因为取样冻结早于结束阶段；不能解释为DPB没有归还。

将EBD消费偏移与源包顺序对照，记录与跳过源包索引16、17（从0计数）后的序列对应；这两个源包的PTS分别为18、16。两处IDR的消费长度比容器包长度多37字节，其余长度按该顺序完全对齐，因此不能把EBD偏移直接等同原容器包大小。该结果把排查重点移到提交输入之前及输入归还链路，尚不能断言固件丢包，也不能仅凭长度建立每包的唯一身份。

当前待验证的具体候选是FFmpeg 8.1.3的V4L2 M2M路径：遇到EAGAIN后应保留的输入包，可能在后续 `try_start` 失败返回路径被 `unref`。修正候选正在准备A/B，尚无实机对照结果；不能将此假设写成已定位根因。EOS正常退出与逐帧正确性仍须分别验证，Steam硬件视频解码继续关闭，#70不安装。

本轮测试后已恢复已安装#56，SSH确认系统状态为running。原始缓存日志和帧数据仍只保留于私有维护目录。

## FFmpeg 8.1.3 待重试包候选：源码回归及独立程序对照

手机报告 negativo17.org `ffmpeg-8.1.3-1.fc44`。上游n8.1.3确有EAGAIN保包被后续start失败清理的路径；尚未审计该发行包的精确source-RPM补丁。候选 `runtime/ffmpeg-patches/0001-v4l2-preserve-pending-packet.patch` 将非ENOMEM分支直接返回0，保留待重试包，其余硬错误和EOS路径不变。

提取实际receive函数的C桩测试中，原版连续3次EAGAIN/start暂时失败会丢包，修版最终只提交原包一次；ENOMEM、入队硬错误、正常成功、成功入队后start失败、EAGAIN/start成功、EOF/draining及取包EAGAIN覆盖均通过。父级复跑ASan/UBSan通过。此测试证明控制流，不能替代实机归因。

使用同配置独立ARM64上游程序（仅该补丁不同），两次分别临时启动无诊断日志的#68，首次600帧实时输入均逐帧一致、正常退出：原版19.576秒，修版19.538秒。故本组并未形成“原版失败、修版成功”的实机对照，不能宣称消除随机初始丢帧。两者均使用默认16个输入缓冲。

修版随后快速解码600帧仍在45秒期限后被终止，最终记录600帧内容一致，但退出码-9、总时长47.069秒，明确判为失败。修复待重试包不能据此宣称解决结束卡住问题；正常快速完成与结束阶段排空还需单独排查。

随后将输入缓冲仅在实验中设为2：原版请求300输出帧得到PTS最高307，前300范围缺3、4、6..13且14..59内容不符；v1候选仅0帧、退出190，日志明确“An invalid frame was output by a decoder”。因此撤回v1为有效修复的结论：只保包而返回0违反有效帧契约，前述桩测试未覆盖该契约。该补丁保留为失败实验记录，不得安装。下一候选必须同时处理待提交包的内部重试、source-change等待及错误边界。

v2改为现有dequeue/poll加内部pending重试，20ms poll、1ms让出CPU、两秒连续无进展则ETIMEDOUT清理；无pending仍沿用原阻塞等待。扩展测试检查每次返回0必须有有效帧，ASan/UBSan与父级复跑通过。该deadline不能中断阻塞ioctl、poll内部持续EINTR或原有无pending等待，外部45秒上限仍保留。

同次#68启动的2-buffer压力序列为：原版失败 → v1零帧失败 → v2 300帧逐帧正确/退出0（9.623秒）→ 反向原版也300帧正确/退出0（9.577秒）。反向结果表明时序波动仍在，不能把单次v2成功夸大为稳定A/B根因确认。所有缓冲数量变更均仅用于单次CLI参数，未改系统默认。

v2默认16-buffer快速解码仍失败：最终600帧内容一致，但45秒期限后终止、退出-9、总47.070秒。结束阶段卡住与初始丢包需要分别修复，v2不具备安装验收条件。无SFR/固件故障记录。v2独立程序SHA256 `f4a08a2bc0d8365287f9c6860dea87bbdbdd5a6fbf017bed4ed68e3c9dc6a5aa`；公开补丁已验证从原版应用后逐字节等同编译源码。补丁只作为可审查实验保存，未替换系统FFmpeg、未启用Steam硬解、未写入boot或REC。

本轮收尾已实际SSH验证恢复 `7.2.6-axon10s-dsiclkfix1`（#56），系统running，独立游戏模式user service active，仅2GiB ZRAM，无失败系统服务。

## 结束等待的现场定位

#68 + v2快速600帧再次超时。只读/proc取样显示，启动后约3秒及6秒时framemd5已完整写出600行；decoder线程停在ppoll无限等待，其他工作线程等待futex。因此不能将停在544帧的进度记录解释为只解出544帧。

用户态仅增加晚期日志后仍复现：第598帧处调用STOP_DECODE，随后第598、599、600帧的dequeue均为draining=1、done=0、timeout=-1，之后阻塞。没有EOS事件、非空LAST或空终止缓冲记录。早先“已交付LAST后重复等待”的假设不受本次证据支持；尚不能用done入口guard修复，因为done还可能代表提前到达的EOS通知。

诊断版第二轮缩短外部期限为20秒：仍600帧正确，但22.071秒后退出-9。下一步核对真实DMA EOS缓冲协议；不通过用户态伪造EOF掩盖驱动未返回终止标记。

补充去掉`-frames:v`、自然读取同一600帧文件至EOF：#68仍出现同样STOP后无终止标记的阻塞。decoder晚期日志已取出600帧，但输出文件在外部终止后仅599行（下游仍需结束/排空），退出-9、22.070秒。故失败不依赖帧数上限。记录的输出帧数与decoder已取帧数不可混用。

## #71 真实DMA EOS缓冲：结束阻塞修复通过，起播时间戳另有问题

临时内核 `7.2.6-axon10s-video-realeos1`，镜像SHA256 `dc30835dc50064c83c0069101b8077bcc9358c458f61d41715ded91a6cb60d44`。仅将#68的Axon/IRIS2/固件1.0.90/H264分支从NULL EOS改成4KiB真实DMA缓冲，其余分支不变；按上游方案在会话关闭后释放。`core.h`新增实例字段，所有Venus对象已强制重编。嵌入设备树、48固件initramfs、56 DSI保留检查通过，0007公开补丁逐字节重建实际vdec/core源码。

采用独立FFmpeg v2，首次自然EOF快速解码600帧：逐帧一致、退出0、2.277秒。晚期日志明确出现EOS_EVENT，随后EMPTY_LAST(flags=0x104001)，与#68发送STOP后没有任何终止标记形成对照。去掉诊断日志后同样600帧一致、2.232秒退出0。连续会话中实时600帧19.562秒、2-buffer压力600帧2.226秒均完整且正常退出；无SFR/固件故障记录。本组支持真实DMA缓冲修复已复现的结束阻塞，未据此推断全部硬解场景通过。

初始输入seek到第5秒另有失败：软件450帧、PTS0..449，硬件479帧、PTS约128820..128848，虽退出0仍判失败。按完整源视频hash反查，479帧内容全部对应源121..599；因此这里不能笼统描述为画面损坏。数值分析：源121预滚PTS=-966667us，FFmpeg将其拆为tv_sec=0/tv_usec=-966667，内核将usec转u32后成为4294000629us，30fps下约128820，精确吻合异常首PTS。负秒数也可能无符号环绕，因此只规范化余数不构成充分修复。先验证保留非负绝对PTS的对照，再决定用户态修复；尚未测试同一V4L2会话内的反复seek/重配置。

仅增加`-copyts`保留输入绝对时间戳，仍使用输入`-ss 5`且自然EOF（不加额外trim/setpts）：软件与硬件均450帧、PTS150..599逐帧一致，硬件1.774秒退出0。原来的负PTS对照失败、非负PTS对照通过，支持时间戳转换这一具体方向。`-copyts`在这里是归因实验，尚未作为系统/播放器通用修复部署。

#71测试后正常重启返回#56。此次#56的QCA6390启动读取board数据失败(-2)，没有无线接口，但USB shell与系统running正常。通过USB确认唯一设备0000:01:00.0为17cb:1101且驱动ath11k_pci后，对该设备执行一次unbind/bind，wlp1s0与原IP/SSH恢复；未改固件文件、未部署自动重试服务。失败发生在boot约6秒，重绑定约121秒成功，具体原因尚未证明。该偶发无线启动问题单独保留为未完成项。

最终SSH复核已安装#56、系统running、独立游戏模式active、仅2GiB ZRAM、无失败系统服务。#71仍仅临时启动，系统FFmpeg与boot/REC均未替换。

## #71 + decoder PTS token：负时间戳修复验证

独立 FFmpeg 在 v2 receive 修复之上加入 decoder-only 正值 token 与 4096 项原始 PTS 映射，成功 QBUF 后才提交映射；回收帧恢复原始 signed PTS，过期或未知 token 显式报错。没有修改系统 FFmpeg。独立二进制 SHA256 `b9fb8a8a6db00b56b0d363a18fb98e4391f61096b9f46f4491ae69d848ad16d2`。

不使用 `-copyts`：第5秒起播450帧，1.774秒；128×128长素材5000帧，3.631秒，跨过映射容量；2个输入缓冲压力600帧，2.228秒。三组硬件结果均与软件逐帧内容及时间戳完全一致、退出0。真实同会话反复seek与分辨率重配置尚未验证，不能据此启用Steam硬解。

原生 GStreamer 1.28.7 显式 filesrc → qtdemux → h264parse → v4l2h264dec → fakesink(sync=false) 对600帧素材连续两次正常退出0，外部25秒上限。此项仅验证另一用户态硬解管线能排空结束，未做逐帧对照，也未验证Steam CEF接入。

针对此前无线启动board文件读取-2，部署了严格限定设备、错误签名及固件hash的一次性恢复服务。健康状态实机无操作检查通过；实际故障启动时自动恢复仍待观察，不能视作底层原因已修复。

本轮发送正常重启以返回已安装#56后，SSH暂时超时且Mac未枚举到USB命令口；尚未确认返回成功，需恢复连接后补充验证。boot/REC未改写。

后续连接已恢复：USB及SSH均确认返回#56，系统running、游戏模式active、仅2GiB ZRAM、无失败系统服务。无线恢复服务开机执行并检测到接口已存在，成功无操作退出。上一启动日志到systemd-shutdown/journal停止为止，包含/tmp卸载busy与watchdog超时设置失败，尚不能解释整个重启耗时；不再将暂时失联记作未恢复。

进一步源码审查发现 FFmpeg 8.1.3 h264_v4l2m2m 未注册 flush 回调。通用 avcodec_flush_buffers 不清理私有 pending 包、draining 或硬件队列；capture重配置保留token映射并不等于同会话seek支持。此前初始-ss验收不能覆盖运行中的播放器拖动进度。正准备同一AVCodecContext的中途seek和EOF后seek对照，禁止关闭重开掩盖此缺口。

## 同一解码实例 seek/flush 实机失败已复现

新增 `runtime/diagnostics/video-seek-same-context.c`，每次仅创建一个 AVCodecContext，在中途或自然EOF后调用 av_seek_frame + avcodec_flush_buffers，绝不关闭重开。逐帧转为规范化YUV420P并去除行padding后计算MD5，打印原始PTS；适用本次8-bit420素材。外部timeout25秒、KILL宽限2秒，零帧重播显式失败。测试程序ARM64 SHA256 `c0b133c102559ba1101a41432e8f025b68b9bcba21cd2dada0347ddd03567498`，链接已验证token+v2静态库，临时#71。

- 中途模式：先60帧，软硬件完全一致；再向后关键帧seek至5秒附近。软件phase2为480帧，硬件481帧。额外一帧PTS30720（timebase1/15360，即2秒），随后480帧PTS与hash均匹配。两者退出0，但硬件因残留旧帧判失败。
- EOF模式：第一遍软硬件600帧全部匹配；seek0+flush后软件再次600帧、退出0，硬件立即EOF、0帧、退出1。

这确认“初始起播通过”不能替代播放器拖动进度/重复播放验收。当前补丁仍不安装为系统FFmpeg，也不启用Steam硬解。

生命周期审查还发现，不能直接把现有codec_end+init挂入flush：STREAMOFF失败时end仍释放OUTPUT，旧外部帧回收可能继续QBUF；提取实际函数的ASan/UBSan桩测试已复现这一控制流。需先实现退休会话与回收排队的同步、失败时保留资源及显式错误传播，才可受控测试内部重建硬件会话。此处不宣称已经修复seek。

本轮seek测试后已正常返回#56并通过SSH复核：系统running、独立游戏模式active、仅2GiB ZRAM、无失败系统服务，无线恢复服务健康无操作退出。#71、独立解码程序均未固化到系统启动/FFmpeg包。

## FFmpeg flush 候选：已复现的 seek 和重播失败修复通过

0004候选在相同AVCodecContext内退休旧私有硬件会话，再建立新会话。加锁串行化旧帧回收QBUF与退休；STREAMOFF失败保留旧映射并报告flush_error，下一次显式flush可重试；外持旧帧延长旧context、fd及两队列映射生命周期。共享清理不再在外部引用存在时提前释放OUTPUT。并非只在测试程序中关闭重开decoder。

独立Linux ARM64完整编译通过。五源码补丁逐字节重建通过，父级和第二智能体独立审查。Linux GCC13.3 ASan/UBSan提取实际函数测试及父级复跑通过：两队列停止失败、部分初始化失败、重试、错误传播、晚期帧引用及真实pthread并发退休屏障。macOS未命名sem_init不支持导致最初测试中止，已明确改为Linux执行，没有把平台差异计作通过。

#71实机、相同600帧素材：中途seek前60帧及seek后480帧均与软件逐帧PTS/尺寸/MD5完全一致、退出0；此前额外旧帧消失。自然EOF前600帧及seek0后600帧均完全一致、退出0；此前零帧重播失败消失。

持帧测试共5阶段，帧数60/45/45/360/600，前后跳转并包含EOF重播，始终同一外部AVCodecContext。每次clone保留旧帧至flush和下一阶段之后，四次转场共8个MD5复核全部相同。各阶段首尾PTS/hash及帧数与软件一致、退出0。该测试只比较阶段边界和旧帧，未比较每个中间帧。内核日志无本轮Venus SFR/固件故障或IOMMU fault记录。

独立ffmpeg二进制SHA256 `5218bc86e87d08b316029bc9ff7ab8332a02417034364b3033e90ec65f350657`；same-context测试程序 `3d6e1b74eac89b9f04759f827af4f8e5542d8d43fc7e019cc3799ed449e653ba`；lifetime程序 `7f38379b076fb06845e08f4a7e34221413cd5ef96e83b7c83c4acc96119f8769`，部署后hash核对一致。未替换系统FFmpeg，未启用Steam硬解，未改boot/REC。真实分辨率重配置、长期播放器使用、发行包和Steam自身解码链路接入仍需验收；其他codec/encoder仅共享路径审查，未做实机集成验证。

本轮flush测试后已正常返回#56，USB与SSH复核系统running、游戏模式active、仅2GiB ZRAM、无失败系统服务；无线服务健康无操作退出。GitHub dry-run push返回缺少HTTPS凭据，未进行远端发布，关键节点暂保留本地提交。

## 真实分辨率切换：系统GStreamer通过，FFmpeg提前EOF已定位

连续raw AnnexB H264流：前60帧128×128，后60帧640×360；每段独立SPS/PPS+IDR，8bit420、30fps、B帧。输入SHA256 `3e67117ddc2ad0f29d70fe55585a380839b0724ad271c7b809ade8a6eb4cb55c`。新avcodec直连harness全程一个实例，不seek/flush/reopen，每帧hash后立即释放，不经过filter/encoder。raw流无可靠PTS，本次按序号/可见尺寸/规范化YUV420P hash验收，不将其计作时间戳验收。

#71+token/v2/flush候选：软件120帧正确，硬件仅59帧便自然EOF、退出0；前59帧内容完全一致。AV_LOG_DEBUG显示CAPTURE已从128×128重配置为640×384，但之后立即EOF。最小事件日志进一步确认：SOURCE_CHANGE重配成功后，draining=0时收到V4L2_EVENT_EOS，现有handler把capture.done置1，导致提前返回EOF；没有在该点观察到DQBUF错误。

单独去掉EOS通知直接置done的对照得到119帧：第一尺寸59帧，第二60帧但可见高度误报384。故消除提前EOF还不够，仍需保留切换前最后一帧、读取正确可见裁剪。Linux [stateful decoder接口](https://docs.kernel.org/userspace-api/media/v4l/dev-decoder.html#dynamic-resolution-change)要求切换时处理旧CAPTURE输出至LAST，保持OUTPUT streaming；EOS通知不能代替缓冲排空。Venus G_SELECTION的可见矩形来自CAPTURE+COMPOSE，当前FFmpeg仅在S_SELECTION成功后读取默认CROP，不能取得该值。

同一临时内核、同一文件，系统GStreamer1.28.7显式v4l2h264dec输出120帧且正常EOS。进一步使用videoconvert/I420/appsink按VideoMeta或VideoInfo的offset/stride抽取可见YUV行：120帧、60+60尺寸边界、所有像素MD5与软件完全一致、退出0。这证明当前硬件及系统原生解码链路可处理此样本，尚不能推断Steam CEF或任意播放器已接入硬解。

诊断工具新增video-reconfig.c、video-reconfig-gstreamer.py、compare-video-reconfig.py。GStreamer脚本异常/零帧/超240帧均显式失败，映射finally释放；外部25秒上限。FFmpeg完整DRC修复正在准备，EOS-only对照不作为完成修复发布。


## FFmpeg DRC完整候选实机通过（0005）

在0002/0003/0004上增加0005。保留旧分辨率帧至LAST再仅重配CAPTURE；OUTPUT与token表继续使用；EOS事件不提前宣告结束。失败的STREAMOFF保留映射，等待旧引用时重查条件，回调在锁内取走context引用，避免零计数后访问已释放buffer。

实机验收修正了两项模拟假设与一项驱动交互：实际内核v4l2-event.c空队列返回ENOENT，原EAGAIN-only候选零帧退出，现兼容两者并保留EINTR重试/EIO传播；DRC会退回bytesused0、flags0x4041、timestamp0的ERROR非LAST缓冲，原候选在60帧后被严格token检查拒绝，现仅在pending DRC时回收该空缓冲并继续等LAST；Venus S_FMT覆盖inst->crop，故必须在重配前保存COMPOSE，重配后恢复可见尺寸，不能把384行分配高度当360行画面。未放宽真实帧token检查。开启debug日志曾改变时序避开空缓冲失败，因此最终验收使用普通日志版本。

最终独立ARM64编译通过，无本轮新增编译警告。父级复跑三套Linux GCC ASan/UBSan提取实际函数测试通过：event/LAST/错误优先级/空ERROR分支、S_FMT重置crop、flush与并发引用生命周期。第二智能体审查与实机结果分别记录，不用模拟通过替代硬件通过。

- 原120帧：60帧128×128+60帧640×360，所有序号/可见尺寸/YUV420P MD5与软件一致，正常EOF，退出0。
- 连续180帧：60帧128×128+60帧640×360+60帧128×128，所有像素hash和尺寸与软件一致，正常EOF，退出0。验证放大、缩小与连续两次变化。
- 原五阶段seek/EOF回归：60/45/45/360/600帧，阶段首尾PTS/hash与软件一致，8次外持旧帧hash检查全部通过，退出0。此项未比对每个中间帧。

最终decode-drc-fixed SHA256 `2681a4113d8782e15ec2241653fdbcd8ac7e1f73ba1e9763b40beb6135e2cf8c`；seek-lifetime-drc `97aa901532c948216c8bb2b543301f2e4df4aa2faf0c1100d847d5031a71e83b`。部署后hash核对一致。未替换系统库、未打开Steam硬解、未改boot/REC。

限制：raw流无可靠PTS，DRC只验帧内容/顺序/尺寸；DRC测试不跨尺寸保留旧外部帧；同线程持旧帧继续请求重配仍可能等待；原多memory-plane计数问题未混入修复；本机NV12为单memory-plane。不能据此宣称所有播放器、Steam CEF、其他codec/encoder已修复。

本轮DRC测试后已正常返回已安装#56。SSH复核内核7.2.6-axon10s-dsiclkfix1、系统running、独立游戏模式active、仅2GiB ZRAM、0个失败系统服务；USB命令口重新枚举。候选及日志保留，boot/REC未改写。


## Steam CEF真实硬解接入：缺失设备别名已修复

live CEF Chrome126.0.6478.183，ARM64 libcef BuildID a29cadf31ff4e0c93949d65c973e2292062756e0。官方对应V4L2Device扫描video-dec及video-dec0..9，stateful后端直接V4L2，不调用系统FFmpeg；Steam定制是否全部相同需实测。此前FFmpeg通过不能直接推导CEF通过。

临时#71验证video1名称qcom-venus-decoder、driver qcom-venus，video0为encoder；armada属于video组。补video-dec0映射，临时通过原生settingsStore开启硬解，重启实际游戏模式用户服务。确认disable-accelerated-video-decode消失，SystemInfo video_decode=enabled，但videoDecoding仍为空。实际HTML视频播放才给出决定性证据。

在游戏模式页面插入1px透明、静音的合成视频，结束或35秒超时均移除。CDP Media属性按playerId记录，避免把页面缓存的其他VP9播放器混为H264结果。320×240/3秒H264 baseline：V4L2VideoDecoder、platform=true，ended，90帧、0丢帧。1280×720/20秒H264 high：1.21秒跳10秒，11.07秒跳回3秒，最后自然ended到20秒，579total、1dropped；该1280×720播放器同样V4L2VideoDecoder/platform=true。跳转运行帧数不应按原文件600帧验收。GPU processCrashCount保持0；但随后核对完整内核日志发现Steam启动阶段有Venus固件崩溃，详见下段。不可把GPU进程未崩溃等同视频固件正常。

这证明实际Steam CEF能够使用当前内核的H264硬解，而非仅外部FFmpeg成功；尚未验证全屏物理呈现、像素hash、长期覆盖层交互、HEVC/VP9或所有商店视频。其他缓存VP9播放器显示VpxVideoDecoder，不宣传全格式硬解。测试未替换系统FFmpeg或CEF。

持久化70-axon-venus-decoder.rules精确匹配decoder名称及driver；保留权限和原videoN节点。删除手工测试alias后经udev change重新创建，并确认DEVLINKS与armada读写权限。该规则对Venus禁用的#56不生成节点。测试后原生硬解设置已恢复false，webviews保持true，正常重启返回#56；启动结果另行核验。


### CEF启动期间VPx固件崩溃：全局硬解仍不可固化

最终归档完整内核日志发现：本次启动monotonic49.79秒起session error1001，49.887秒固件SFR `VIDEO.VPU.1.0-00090-PROD-1 Err_Fatal .../decoders/vpx/src/vpx_decoder.c:1126:67861`，伴随1009及no valid instance；恢复初次失败，52.576秒报告recovered。之后H264短片/720p跳转测试通过。Media记录还显示页面缓存VP9播放器最终使用软件VpxVideoDecoder，但不能仅据缓存属性锁定故障的具体player/格式；日志直接指向VPx固件路径。

因此设备别名缺失已修复、CEF H264接入已证明，但全局开启会暴露另一个固件故障，仍保持关闭。GPU crashCount0与Venus固件SFR是不同维度，不能互相替代。本轮不据H264成功固化#71或打开日常硬解。下一步核对VP8/VP9能力枚举、实际流参数与固件边界，单独复现修复。


回滚已复核：#56、running、独立游戏模式active、0失败系统服务、仅2GiB ZRAM，video-dec0不存在。settingsStore读回video=false/webviews=true，steamwebhelper实际含disable-accelerated-video-decode。udev规则保留但稳定内核无匹配节点，不影响当前使用。

针对VPx的下一步证据：源码审查发现SM8250的HFI6平台能力来自hfi_platform_v6.c静态表；hfi_parser平台解析成功即返回，广告VP8/VP9和VP9 P0/P2_10B并不等于旧1.0.90固件实测支持。需单独核对原始流codec/profile/coded size及并发，按VP8、VP9-P0等最小样本逐项受控测试，不能仅按vpx_decoder.c把VP9或多会话认定为唯一根因。


## VPx首包故障隔离与#72输入尺寸候选失败

在Steam硬解保持关闭的临时#71上，分别测试单会话320×240/30fps/60帧/8bit420合成VP8和VP9 Profile0 WebM。软件均完整解码60帧，素材SHA256：VP8 `364d470ad84ee1eb27d72a652bd6f988a6c01fd100d50a4edaf8bc03068cd4c8`，VP9 `4808a358909300e8caf9d71a1f76f02ae9b1011c5475fb82b63d4561b24c0a48`。外部timeout25秒+KILL2秒，不并发运行。

GStreamer显式v4l2vp8dec/v4l2vp9dec，demux后每包节流33333微秒，计划收到30帧后停止（不是伪造EOS）；自然drain模式另要求60帧且真实EOS。脚本按实际I420可见行hash，处理map/unmap/异常，检查NULL关闭状态；停止统计数不表示硬件恰好只解了该帧数。

#71：两格式均首帧前失败、0帧、退出1，同一固件SFR vpx_decoder.c:1126:67861。VP9解码器sink只收到1个buffer，内核fatal monotonic85.339980，随后错误传播产生sink EOS monotonic86.339110623，约晚1秒；不是正常60包EOF。因此本次首包失败不能先归因EOS虚拟地址，也不依赖两个同时运行的播放器。VP8首轮未带input探针，不借用VP9时序作为它的独立证据。

准备#72，只将现有本机HFI6XX输入尺寸helper的格式条件从H264扩展为H264/VP8/VP9，保留所有guard、错误传播、EOS及其余驱动。原因是session_init先发128×128，原helper只纠正H264。实际函数ASan/UBSan guard测试及独立审查通过，完整内核编译和DT/initramfs48/DSI56保留项验证通过。镜像SHA256 `54aa22e72435e79905d35496659b2bc8981eafbf64a570dca63d31967ad26390`，临时fastboot boot，无分区写入。

#72实机仍失败：VP8与VP9均1个输入buffer、0帧、退出1，同处固件SFR，fatal均早于输入EOS。系统FFmpeg vp8_v4l2m2m作为独立用户态交叉验证，同样0帧/退出69/同处SFR，60包读入、59次decode errors。故仅补输入尺寸无效，GStreamer mutable-caps警告也不足以解释跨实现固件崩溃。未运行无意义的完整drain或并发压力测试：首包已经失败。

#72不作为修复安装，失败补丁仅存docs/experiments/72-vpx-input-size-FAILED.patch，不属于推荐runtime补丁链。固件随后报告recovered，不能用恢复成功宣称故障修复。下一步应核对VPx初始化/输出格式等实际协议差异。没有证据支持直接添加IVF头：主线要求压缩视频帧；所查官方AOSP Qualcomm OMX的IVF写入仅用于调试文件，且并非同机SM8250版本，私有固件额外约定仍未知。

#72试验后正常返回#56，SSH确认running、游戏模式active、0失败服务、仅2GiB ZRAM；settingsStore确认视频硬解false、GPU网页加速true。boot/REC未修改，#72仅保留实验镜像及失败证据。


## #73 VPx pre-input buffer requirements query

Diagnostic based on #71, restricted to Axon10s/SM8250/HFI6/FW1.0.90/VP8 or VP9. Sets actual input dimensions, queries firmware after set_num_bufs but before resource loading/input, logs host calculations, and deliberately returns -ECANCELED. This prevents VPx decoding and is not an installable repair. Extracted actual-function ASan/UBSan, independent review, build and DT/initramfs48/DSI56 preservation checks passed. Temporary image SHA256: `1f08d0bb5f1766cdf77c6a5a9705094f7bab3e8c27e51d868c20a51db4f8428f`.

Both hardware queries completed with query_ret=0, all host calls=0, and explicit query-only stop. Each probe returned exit1/zero frames as intended cancellation, not successful decoding. VP8 and VP9 P0 were 320x240, capture aligned320x256, input_count4, output_count8/11. bit_depth field0 is pre-header state, not the known8-bit fixture depth. One earlier VP9 attempt used a nonexistent filename and failed before querying; only the corrected vp9-p0.webm run counts. Captured kernel log contains no known SFR/Err_Fatal.

Internal per-buffer bytes, firmware / host:

|Codec|SCRATCH type6|SCRATCH1 type7|PERSIST1 type5|
|---|---:|---:|---:|
|VP8|5652480 / 5652480|78528 / 80896|23040 / 23040|
|VP9|5652480 / 5652480|79360 / 81408|9011712 / 9068288|

Internal actual counts all1; firmware did not return additional nonzero PERSIST/SCRATCH2. Both codecs DPB size155648/176128, linear OPB147456/147456. No observed host internal underallocation: do not replace static sizes or enlarge buffers based on these results. Raw fields: experiments/73-vpx-buffer-requirements.json; diagnostic patch: experiments/73-vpx-query-only-DIAGNOSTIC.patch.

These are current pre-header requirements, not final DPB demand. FW OUTPUT/OUTPUT2 counts32 follow earlier set_num_bufs32; host actual1 is not application queue length. Query success does not establish resource loading or decode success. Next bounded hypothesis: compare requirements before/after count declaration to establish whether32 is configuration echo, then assess actual registered DPB counts. No justification yet for forcing32 DPBs. Steam global hardware video remains off; boot/REC unchanged.

After the query trial, normal reboot restored installed #56 (7.2.6-axon10s-dsiclkfix1). SSH verified system running, game-mode user service active, no failed system units, and only2GiB ZRAM swap.


## #74 VPx count declaration comparison

Based on#71, diagnostic-only exact Axon/SM8250/HFI6/FW1.0.90/VP8-or-VP9 guard. Query before original set_num_bufs, send original input/32/32 declaration once, query again, then cancel before loading/first input. All failures propagate; non-VPx retains original sequence. Extracted-function ASan/UBSan and independent review passed; full compile and preservation checks passed. Image SHA256 `6308c15ec0958127d34f2edcacee8737a62562106d0e2e242fbac9486bf46a86`. Temporary fastboot boot only.

Both codecs completed both queries with ret0 and explicit cancellation, no known firmware SFR/Err_Fatal in captured kernel log. Probe exit1/zero frames is intentional, not successful decoding. Before declaration, OUTPUT and OUTPUT2: VP8 hold6/min0/actual6; VP9 hold11/min0/actual11. After declaration, both codecs hold32/min32/actual32. INPUT actual6 became4. Internal requirements and all sizes were unchanged. Thus32 in#73 is affected by host declaration and is not evidence of a natural32-buffer minimum. Do not inflate DPB allocation on this basis. Raw fields and diagnostic-only patch are in experiments/74-vpx-count-before-after.json and74-vpx-count-query-DIAGNOSTIC.patch.

Code trace: initial output startup loads/registers internal resources but allocates no DPB before the initial input. Actual DPB allocation happens after the sequence-change event in capture startup; static/platform and event-derived minima determine allocation. VP9 has a special fw_min_cnt=11 override, VP8 uses the event count with its platform minimum. All codecs, including working H264, share32/32 declaration. This does not establish DPB shortage as the first-packet fault.

Focused downstream comparison: current sm8250_res.num_vpp_pipes is4 (not2); Qualcomm IRIS2 also defaults work_route4 and mode1 for progressive320x240, without VPx decoder special cases. No basis for a mode/route change. Exact720p boundary differs (< downstream, <= mainline), outside this fixture. Source: https://android.googlesource.com/kernel/msm/+/9b46d8c49a673cca641aef1c83f409e83cd88f18/drivers/media/platform/msm/vidc/msm_vidc_clocks.c . Limited decoder-entry inspection also provided no evidence for a VPx-specific framing property; no framing patch proposed.

After#74 normal reboot, USB and SSH verified stable#56, system running, game mode active, zero failed units, only2GiB ZRAM. Settings readback video=false/webviews=true. Early SSH timeout resolved after startup; USB confirmed healthy network, no manual recovery needed.


## #75 bounded firmware log output: LOAD_RESOURCES invalid-state evidence

Diagnostic-only#71 decoding path with hfi_venus.c debug-queue output enabled only for Axon/SM8250/HFI6/FW1.0.90. No query cancellation or decoder changes. At most32 messages per boot,256 bytes each; validates aligned packet size, type and payload bounds, copies shared buffer under existing lock, prints outside. Nonmatching path unchanged. Default fw_level0x18 preserved. Actual-function ASan/UBSan plus4-thread budget tests, independent review and complete kernel/preservation checks passed. Image SHA256 `5712d676e05c6b165c7badea10ed2cc8439b6e3d8262c53a79dfd557bf156475`.

First VP8 stop probe at default0x18: one upstream input, zero output, exit1, same SFR at34.990036; no debug text. This alone cannot prove firmware emitted no messages. After firmware recovery, enabled0x1f temporarily and ran a tiny QUERYCAP/S_FMT/REQBUFS probe, no QBUF or STREAMON. It initialized the VP8 session, allocated4 input buffers, released them, exited0; actual FW session-created and command messages appeared. Restored0x18. This verifies the logging path accepts real firmware messages without provoking decoding.

A single additional VP8 probe temporarily used0x1c (HIGH|ERROR|FATAL), avoiding most per-command LOW logs. It again returned one upstream buffer, zero frames, exit1. New firmware evidence:

- 133.257519: VenusDecoder: LOAD_RESOURCES
- 133.283616: VenusDecoder: Load Resources Command received in Invalid State4
- 133.356676: same vpx_decoder.c:1126:67861 fatal

The failure is now tied to resource-loading/state transition, not established as bitstream parsing. Earlier 'first packet' wording described the GStreamer sink count; that count does not prove ETB reached firmware. Do not interpret private firmware state4 as a known host HFI state without evidence. Next investigate actual LOAD/START/ETB ordering and downstream initialization differences. No arbitrary state bypass, buffer inflation or work-mode change justified. Firmware debug verbosity restored0x18; no permanent setting or boot/REC writes. Diagnostic logging perturbs IRQ timing; failure still reproduced. Full private logs retained, bounded excerpts and diagnostic patch/session-only source saved under experiments/75-*.

Independent source review confirms internal allocation/registration precedes synchronous hfi_session_load_res; START and initial ETB follow successful load. No normal double-LOAD path found: initial DEINIT starts resources, capture reconfiguration uses CONTINUE. Downstream also uses init_done -> LOAD -> START, with no VPx skip; do not remove LOAD. The earlier110s session-only probe and133s fresh session creation are distinct attempts, not proof of reused loaded session. Source: https://android.googlesource.com/kernel/msm/+/9b46d8c49a673cca641aef1c83f409e83cd88f18/drivers/media/platform/msm/vidc/msm_vidc_common.c#3913 . Next compare pre-load properties and internal buffer registration sequence.

After#75, normal reboot restored installed#56. USB/SSH verified system running, game mode active, no failed system services, only2GiB ZRAM. Steam settings readback after initialization: video=false/webviews=true. No boot/REC or persistent verbosity changes.


## Empty-queue isolation and rejected#76 profile initialization

A small direct V4L2 probe sets OUTPUT320x240 VP8/H264 and CAPTURE NV12, allocates OUTPUT MMAP buffers, then STREAMON with no QBUF, MMAP, bitstream, EOS/DECODER_CMD or CAPTURE stream. Driver min_queued_buffers0 invokes LOAD/START; success is immediately STREAMOFF/released/closed, failure closes, external timeout15s+kill2s. Format/readback logged; source saved as experiments/76-empty-load-probe.c.

Baseline#75 H264 empty STREAMON succeeded, exit0. VP8 empty STREAMON returned EIO, exit1; FW LOAD InvalidState4 at47.415331 then same SFR47.520537. No data was ever submitted, so this instance is independent of video content, GStreamer and translation. CAPTURE320x256/147456B, OUTPUT size491520,4 allocated, colorspace0. H264 also printed an output2 insufficient-memory debug message with equal sizes147456 while succeeding; that line alone is not an allocation failure verdict.

Pre-load source comparison found internal registration types/order/SET_BUFFERS layout equivalent to pinned Qualcomm: SCRATCH/1/2 then PERSIST/1, one-buffer packets36B. Downstream preallocates DPB, but dynamic mode does not register it before LOAD and FTB remains after START. No basis for blind pre-load DPB registration. Two property differences remained: explicit profile/level and secondary output ordering.

#76 tested only explicit downstream defaults before other vdec properties, exact Axon/SM8250/HFI6/FW1.0.90/DEC/VP8-or-VP9 guard. VP8 HFI MAIN=1/LEVEL_VERSION3=8 (not legacy PROFILE_VERSION3); VP9 P0=1/LEVEL61=0x800. All other code based#71, plus#75 bounded logger. Actual-helper ASan/UBSan, independent review, kernel compile and preservation passed. Image SHA256 `b67f377f237a9c7d5989dbae77dc36f10bc494766fdd6356062fda5b56815a35`.

Actual#76 VP8 empty STREAMON still EIO/exit1, same LOAD InvalidState4 at46.145496 and SFR46.236585. Profile-only candidate rejected; no VP9 decode or full stream tests warranted by this failure. Patch saved only as experiments/76-vpx-profile-FAILED.patch, not production chain. Next single-variable candidate restores#71 and changes only DPB/secondary-output property order; do not compound the failed profile change.


## Rejected#77 secondary-output ordering

Based on#71 (without failed#76 profile change), changed only exact Axon/SM8250/HFI6/FW1.0.90/DEC/VP8-or-VP9 secondary layout OPB=OUTPUT2/DPB=OUTPUT: set DPB raw format, enable OUTPUT2, disable OUTPUT. Nonmatching path retains original multistream helper then raw-format order. All failures propagate, sizes/counts/dynamic-mode/resource registration unchanged. Actual-helper ASan/UBSan, independent review, compile and preservation passed. Same bounded#75 logger. Image SHA256 `8359ab30e67005063129ab5dd95e1b9b4ec6121f03573311452cb54ef56f3cdb`.

Actual VP8 empty-queue probe still STREAMON EIO/exit1. FW LOAD at35.473515, InvalidState4 at35.474042, same SFR35.563712. No QBUF or bitstream. Order-only hypothesis therefore rejected; patch retained only as experiments/77-vpx-secondary-order-FAILED.patch. A combined profile/order candidate remains untested; individual failures do not rule out an interaction. No full decode test was run after empty-load failure. All trials temporary, debug level reset0x18, boot/REC unchanged.

The empty-queue probe and H264 control are now the minimal reproduction for pre-decode resource-load failure. Next source audit must verify actual primary/secondary buffer allocation-mode values, not infer them from a conditional branch alone.

After#77, normal reboot restored installed#56. USB/SSH verify system running, game-mode user unit active, no failed system units, only2GiB ZRAM; settings video=false/webviews=true. Neither#76 nor#77 installed.

Allocation-mode audit correction: helper-level calls do not prove wire behavior. Current HFI6 serializer falls through4xx; PARAM_BUFFER_ALLOC_MODE returns-ENOTSUPP, and venus_session_set_property treats it as success without queue write. Thus mainline does not actually send dynamic OUTPUT/OUTPUT2. Pinned downstream OUTPUT_PORT=STATIC is compressed input, not DPB; CAPTURE_PORT=DYNAMIC skips the DPB STATIC pre-registration branch. No allocation-mode send was found in those downstream paths, and firmware default cannot be inferred from them. No mode-change candidate warranted.


## Rejected #78 combined VPx initialization

Exact union of #72 input size, #76 profile defaults and #77 secondary-output ordering, based on #71 plus #75 bounded firmware logging. All six patch application orders produced identical source; extracted-helper ASan/UBSan tests, independent review, compilation and image preservation checks passed. Source SHA256 `4597a4350c19e47fe68df4e9a65b58b5367b4a16e961b24e43bd725ed058f0e2`; image SHA256 `b703094d603253c35e7ca34a055e5306fd0ea9b767ab1017d45d9d539051f52d`, kernel `7.2.6-axon10s-video-vpxcombined1`. #72 original guard remains unchanged; do not describe the whole union as exact firmware gated.

After an interrupted tool session, live verification found installed #56. Previous-boot logs showed #78 had booted and later shut down normally, but no completed probe was recorded. This was not counted as a test failure. The same verified image was temporarily booted again for the actual trial below.

One direct VP8 empty OUTPUT STREAMON, with zero QBUF/bitstream/ETB, returned EIO and probe exit1. Firmware LOAD_RESOURCES at55.578382, Invalid State4 at55.579370, then vpx_decoder.c:1126:67861 fatal at55.683396. The combined candidate therefore also fails before decoding; no full-stream or VP9 trial followed. Debug level restored0x18. Patch retained only as experiments/78-vpx-combined-FAILED.patch, outside the production patch chain; bounded evidence in78-empty-load-results.txt. No boot/REC writes.

Next diagnostic: capture the bounded raw SYS_INIT_DONE codec capability reply before HFI6 static platform parsing. Firmware-advertised support must be distinguished from resource-load/decode success. Do not add speculative properties or bypass LOAD_RESOURCES.

After #78, USB confirmed #56 during startup; SSH subsequently verified kernel7.2.6-axon10s-dsiclkfix1, system running, game-mode service active, no failed system units and only2GiB ZRAM. Steam settings readback video=false/webviews=true.


## #79 raw firmware capability reply captured

Diagnostic-only #71 decoder and #75 bounded firmware logger, adding a read-only helper immediately before unchanged SYS_INIT dispatch. Board/SM8250/HFI6/message guards, four replies per boot, independent aligned16..12288B size validation, at most64 payload words grouped eight per line. No version gate because image version may not yet have arrived. Parse only successful first property0x1009 with at least three words; unknown layouts remain unknown. No packet, codec-mask, parser, command sequence or error-handling mutation.

Actual-helper15-case ASan/UBSan/Werror harness passes malformed tight allocations, guard exclusions, unknown property, partial lines, concurrent budget and packet/core immutability. Parent review, kernel compilation, package checks, exact embedded initramfs48/DT and DSI56 preservation passed. Source SHA256 `18e51e399f0f2a0e4f4698d4670a3ab0ca23c1216ad4360a86e00f95f46922c3`; image SHA256 `8f5636a488b9f549b49d7821547cfe94320fb3a0771248fa59f6781e95431bfa`, temporary kernel7.2.6-axon10s-video-syscaps1.

Boot itself produced SYS_INIT reply size3192, error0, property count77, payload794 words, dump64 words (explicitly truncated). First property0x1009 reports decoder mask0x701a, encoder mask0xb002. Verified current HFI bits H2640x2, VP80x1000, VP90x4000 are all present in decoder mask. Thus VP8/VP9 are actually advertised by this firmware, not merely invented by the host static capability table. Advertisement still does not prove LOAD_RESOURCES or decoding success; #78 empty-load failure remains unresolved. Remaining properties were neither fully captured nor interpreted.

No additional session/decode probe was needed. Captured boot log contains no SFR/Err_Fatal match; this is not a codec stability test. Default verbosity0x18 retained; no boot/REC writes. Public bounded raw evidence and diagnostic-only patch in experiments/79-*. Existing malformed-transport/parser validation limitations are not repaired by this logger.

Focused follow-up source audit rejects a blind static-parser bypass: hfi_parser.c264..410 only populates host metadata, with no firmware command/ack/state transition. hfi_msgs.c487..513 still completes HFI6 session initialization; resource/default-property commands occur outside that parser. helpers.c538..554 chooses dynamic mode independently for HFI6. Metadata has indirect consumers (minimum geometry and output format), so mismatch is not categorically excluded, but this prefix establishes no exact VP8 discrepancy or value to substitute. No new behavior-changing trial is justified by the parser hypothesis.

Normal reboot restored installed #56; USB and SSH verified kernel, system running, active game-mode service, no failed system units and only2GiB ZRAM.
Steam readback after startup confirmed video=false/webviews=true; initial CDP connection refusal resolved when Steam finished starting.


## #91 offline H264-only compatibility candidate

An explicit default-off, boot-read-only `venus_dec.axon_h264_compat` option restricts the Axon/SM8250/HFI6 decoder to H264 when enabled. It is independent of asynchronously received firmware-version metadata. Both format lookup and contiguous enumeration filter compressed formats; S_FMT rejects the original non-H264 OUTPUT_MPLANE fourcc before TRY_FMT can substitute H264, queue access or instance changes. Raw capture formats, encoder, other devices and disabled-mode behavior remain unchanged. TRY_FMT retains its normal fallback semantics; mislabeled compressed payloads are outside format filtering. This profile affects all clients of the decoder, not CEF alone, and does not repair VPx firmware support.

Actual-function Werror/ASan/UBSan tests and independent source review passed. Full91 compile/package and independent preservation review passed without warnings. SourceSHA915e26bcf532e2218fbe106dcd406c9acf374e1c002f6873bf7af850e6476ccf; imageSHA6d9af326b5305b599696fa6d38cd8e3657143f4ea845c983cd4243f30fc1b76b. Build starts from87 quiet/ICC/ZRAM config and DT, adds Venus and existing71 real-EOS fixes, and explicitly enables the compatibility option in the candidate CMDLINE. Original44/87 initramfs entries are unchanged; archive48 only adds Venus firmware and directory entries. No90 audio overlays are included.

No91 boot or CEF fallback validation has occurred at this checkpoint. Phone remains installed87 with hardware video globally disabled. Required next checks: temporary boot identity/firmware/policy; H264-only OUTPUT enumeration; non-H264 S_FMT rejection; actual H264 playback and VP8/VP9 software fallback without Venus fatal/LOAD failures across Steam startup; cleanup and return87. Do not report restricted format exposure alone as functioning fallback.


### #91 temporary runtime: hardware H264 and software VPx

Temporaryboot09742a2d-6a4d-49c7-9bd7-1cb528be834c reached activegame mode withcompat=Y, taint0, bootdiskRO1 and workingUSB. The13 root firmware files match the previously tested archive48 exactly; this is asset identity, not a new firmware-version response trace. Installed87 remains unchanged.

Device numbering changed: video0 is encoder andvideo1 decoder, with video-dec0 correctly resolving tovideo1. The first fixed-video0 probe safely stopped atQUERYCAP identity verification; no S_FMT followed. After correcting only the target, bounded fresh-fd tests passed: compressed enumeration exposes exactlyH264; VP8/VP9/HEVC/unknown S_FMT each returnsEINVAL and G_FMT remainsH264. No buffers or streams were submitted by this interface probe.

With an independent timed setting-disable fallback armed, enabled Steam hardwarevideo and restarted the independent game-mode service. CEF tests associated each new player by an exact uniqueBlob URL retained only in memory, excluding old cached players. H264320×240/90frames, H2641280×720/90frames and H2641280×720/600frames each naturally ended with0dropped frames and V4L2VideoDecoder/platform=true. VP8 andVP9-P0 each naturally ended60frames/0dropped usingVpxVideoDecoder/platform=false. Globalvideo remainedtrue when read back after the three-codec tests. Matching kernel logs across Steam startup and playback contained no new Venus SFR/Err_Fatal/VPx InvalidState records. No player reload, systemFFmpeg replacement or decoded-pixel correctness claim is involved.

Hardwarevideo was restoredfalse with verified readback and unchanged webviews setting; recovery timer/service were then confirmed inactive/not-found. This proves bounded H264 hardware plusVPx software fallback on this candidate, not VPx hardware repair, all-media reliability, physical presentation or long-term stability. Post-video native suspend and normal return87 remain separate checks.


Post-video native s2idle completed in28.022186552s with RTC IRQ128, suspend success0→1/fail0, alarm cleared and installed policy unchanged. Steam UI heartbeat returned122frames/2015ms with max16.8ms and no probe elements. A further320×240 H26490-frame playback after resume ended with zero drops and V4L2/platform=true. Hardwarevideo was alreadyfalse at this latter test; the existing CEF retained hardware decoding, illustrating that setting readback does not immediately reconfigure an existing process. Restoredfalse was independently verified again, recovery timer/service inactive, and final runtime remained game-active/taint0/bootRO1 with no matching Venus fatal. The initial wrong-node probe remained an expected failed unit until reboot.

Normal reboot returned installed #87 (boot44909f32-01ab-49c7-91e3-23a82b33e25f). USB and SSH confirmed system running, independent game mode active, taint0, boot disk read-only, no failed system units and only2GiB ZRAM. Steam readback confirmed hardwarevideo=false/webviews=true. No #91 boot-partition or REC writes occurred.
