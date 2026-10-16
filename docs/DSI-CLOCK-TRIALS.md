# DSI 启动时钟诊断（2026-10-17）

已安装 #54 的两条 already disabled/unprepared 警告来自 PHY 时钟 provider 注册时的 orphan 补齐路径，调用栈没有经过传输恢复。暂不将其归因于原板级传输补丁0007，也没有证据证明这是 Steam CEF 冻结原因。

#55 仅增加定点日志并临时启动：disp_cc_mdss_pclk0_clk_src -> dsi0_phy_pll_out_dsiclk，flags=0x1004；子/父prepare和enable计数均0，父rate0。CLK_OPS_PARENT_ENABLE导致临时启用PLL，返回-110后仍执行关闭，产生两条WARN。

此结果确认了错误路径及触发对象。下一步评估在无引用、仅补齐软件时钟拓扑时避免提前启动PLL；尚未应用功能补丁。#55未安装。诊断不改变控制流，不屏蔽警告。

## #56 最小修复临时验证

补丁仅限定zte,axon10s-pro、pclk0父关系、旧父为空、双方prepare/enable计数均0。在原prepare锁之内取得enable锁并再次检查，调用原clk_reparent补齐软件拓扑，保持后续频率/精度重算；其他情况保持原路径。不更改CLK_OPS_PARENT_ENABLE，不影响正常显示时设置频率和启用时钟。独立审查通过。

临时启动#56确认命中一次，PLL启动超时与两条already disabled/unprepared警告消失，无新增内核WARNING。正常显示阶段像素时钟173661988Hz，byteclk130246490Hz，prepare/enable均1，与#54基线一致。面板connected/enabled、背光399、Steam独立游戏模式active，仅2GiB ZRAM，无systemd失败服务。

游戏模式停止/重启后服务、显示使能和时钟状态恢复正常；停止会话期间时钟仍被其他显示用户保持开启，因此该测试不证明面板完整断电再上电或真实休眠恢复。实际画面/触摸和长期稳定性仍待确认。#56目前仅临时启动，已安装版本仍为#54。此改动没有证明Steam GPU进程冻结已解决。

#56镜像SHA256：5c40bf2bd1dfa31f5fa80f5a7dab2eca56f706f614b192f5de1b1f57055d57eb。DT/initramfs与#54一致，配置仅release变化。补丁位于runtime/kernel-patches/0001-axon-idle-dsi-orphan.patch。

## #56 已安装与用户确认

用户已确认临时#56画面、触摸正常。随后将该镜像写入boot_a并验证整个启动分区字节，原REC完整哈希不变，六LUN主/备GPT及启动成功标记不变；#54完整备份已在手机和维护机各保留一份，哈希一致。

正常重启再次确认#56、修复分支命中一次、无PLL超时或重复关闭警告；面板enabled，像素时钟173661988Hz且prepare/enable为1，独立Steam游戏模式active，仅2GiB ZRAM。用户确认针对临时同一镜像；长期运行与面板完整断电循环仍未验收。
