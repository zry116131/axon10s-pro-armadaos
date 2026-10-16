# #56 Steam 独立游戏模式启动切换取证

2026-10-17，固定已安装 #56、现有 CPU/GPU 策略、2 GiB LZ4 ZRAM、关闭视频硬解且保留 GPU WebViews，不改 glthread/ANGLE。实际会话是 `gamescope-session-plus@steam.service`；CDP 页面标题含“大屏幕模式”不改变其独立 Gamescope 会话性质。

## 180秒双启动试验

从 Steam 菜单启动已安装《Hollow Knight: Silksong》两次。每次只等待启动阶段，不发送游戏输入、不加载或创建存档；核对新游戏进程身份后发送 SIGTERM 结束测试，观察返回 Steam。这个方法不等同于游戏内正常退出按钮，也没有覆盖游戏内 overlay 或战斗场景。游戏日志确认 D3D11/Turnip Adreno 650。

180个1Hz样本正常结束，内核事件读取成功，CEF无积压/读取错误：

| 指标 | 结果 |
| --- | --- |
| 最低 MemAvailable | 442372 KiB，约432 MiB |
| 最大 swap 使用 | 723468 KiB，约707 MiB；仅ZRAM |
| 最低 /dev/shm 可用空间 | 2391396352 bytes，约2.23 GiB |
| oom_kill 增量 | 0 |
| 新增 CEF 退出/共享图像事件 | 0 |
| 新增被采样的内核 GPU 故障/超时事件 | 0 |
| GPU 进程身份 | PID与启动时间始终相同 |
| GPU线程 | 最多20个，180轮均保留GpuWatchdog；未观察到D态 |
| 内存 PSI avg10 最大值 | 6.01%，有压力但未发生本次OOM |

退出后可见 Steam 页面10秒内获得601次rAF回调，p50/p95约16.7ms，最大16.8ms。这验证页面继续更新，不是物理呈现帧率或输入体验验收。退出后一个ZRAM快照显示508989440字节原始页占186556416字节实际内存；它与上表峰值时点不同，不能拿该快照计算峰值压缩率。

该轮修正了线程名和关键线程优先级，但后来发现合成器实际comm为`gamescope-wl`，旧过滤器只匹配`gamescope`，所以此180秒记录不能用于证明合成器线程等待情况。CEF/内存/内核事件记录仍有效。最终工具补上别名与栈采集，并输出线程遗漏数量；50线程合成测试验证watchdog、主线程和gamescope-wl栈覆盖，另有实机smoke。

## 内存故障策略读回

第三次启动时实机检查：游戏进程oom_score_adj=900，Steam、CEF GPU与gamescope-wl均200，且处于同一会话cgroup；OOMPolicy=continue。该游戏因此具有较高OOM候选优先级，配置不会因任一子进程OOM自动执行整个服务的stop策略。这不是实际OOM回归，也不保证所有其他游戏、所有受害者选择或UI自身OOM都可无损恢复。未人为耗尽全机内存。

## 当前结论

本次未复现冻结；不能宣布历史CEF GPU watchdog退出已修复，也不能从无OOM样本认定历史事件的原因。保留当前参数，不据此新增禁用加速、关闭watchdog或重载内部页面的改动。原始进程记录和游戏日志留在私有维护目录。

## 补齐合成器后的90秒验证

加入实际进程别名后再次启动并结束同一游戏，90个样本正常结束：90轮均采到gamescope-wl（最多11线程），合成器及CEF GPU的PID/启动时间保持不变，所采线程仅见S/R、无D态。最低MemAvailable645712 KiB，最大swap使用999496 KiB；oom_kill增量0，无新增CEF或内核故障事件，CEF积压0，内核事件源正常。仍是短启动切换试验，未覆盖物理输入验收、overlay、长期游玩或历史冻结复现。
