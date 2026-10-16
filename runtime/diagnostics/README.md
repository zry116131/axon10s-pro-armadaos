# Steam 冻结取证

在准备复现之前以 root 执行 capture-freeze.py --output 新文件.jsonl --seconds 180 --cef-log /home/armada/.local/share/Steam/logs/cef_log.txt。不注册开机服务；到时退出。输出文件不得已存在，权限0600，上限8MiB。

每秒记录关键进程/线程的CPU时间、等待位置、GPU相关内核栈函数名、内存/PSI/共享内存、内核故障分类、CEF新增白名单事件时间戳。不保存网页、完整命令行或原始日志，不使用ptrace或停止进程，不改变watchdog。CEF每轮最多读取32KiB，支持轮换和截断。

GPU优先，但进程上限32、每进程线程上限32；一秒间隔可能错过短时异常。CPU活跃/futex等待不足以证明死锁；应结合驱动等待及故障事件、oom_kill增量和CEF退出时点判断。无异常的短采样只能验证工具可运行，不能证明冻结已修复。

已在本机验证：CEF fork子进程保留zygote命令行，因此以GpuWatchdog线程名补充标记gpu_thread_hint（推断角色）。5秒实机检查每次均捕获该进程且内核栈可读，工具正常退出。此检查没有复现冻结。

线程采样现在保存 comm，并优先保留 GpuWatchdog 和进程主线程，再取合成/渲染线程；超过32个时输出遗漏数量。实际合成器名为 gamescope-wl，已加入进程与内核栈采集匹配。`python3 test-process-coverage.py` 用50个候选线程验证关键线程不会被截掉，并验证 gamescope-wl 的栈采集。只看CPU活跃、futex等待或单次D态仍不足以认定死锁。
