# ZRAM 适配与验证（2026-10-16）

已安装 #45 / 7.2.6-axon10s-zram1，当前配置仅启用 2 GiB LZ4 ZRAM（优先级100），旧磁盘 swap 已于 2026-10-17 停用。当前公开下载仍为 #43，本候选镜像尚未发布。

## 为什么重编内核

当前 #44 未启用 ZSMALLOC。仅补装原版模块会改变 NR_ZSPAGES / NR_VM_ZONE_STAT_ITEMS 及相关结构布局，不能靠 vermagic 一致判断 ABI 安全。新内核沿用 #44 配置及原始内嵌 DTB/initramfs，内置 ZRAM、ZSMALLOC、LZ4，开启 PSI，并使用独立 release。最终 Image 中 DTB/initramfs 与 #44 原始字节一致。

## 已通过

- 临时 fastboot boot，随后写入 boot_a 并逐字节长度范围回读核对；新镜像SHA256 `248deb4799d6fd74105e6a5bbff145d351141bcd377fc86aca05184452615536`，大小71290880字节。
- REC 未改写，当前完整分区校验一致；#44 完整 boot 备份在维护主机和手机两端保留。
- 三组64 MiB块设备数据读写：同值页、重复非同值数据、随机数据，SHA256全部一致。重复非同值数据占用约4.8 MiB实际内存；该压缩率只代表测试数据。
- 受限cgroup的128 MiB匿名内存完成MADV_PAGEOUT，smaps记录131072 KiB换出，读回哈希一致；测试期间ZRAM读写错误为零。
- 最初双 swap 方案的第二次正常重启后，无手动启用操作，ZRAM和磁盘swap均自动上线、优先级正确；axon-memory.service成功，Wi-Fi/SSH、USB gadget和独立Steam游戏模式服务恢复，无systemd failed服务。

## 启动整合修复

原系统屏蔽 fstab 与 zram generator，并通过 axon-test.target 启动，因此写fstab或只挂multi-user.target都不能保证启动。独立 axon-memory.service 接入实际目标，初始化空闲ZRAM；2026-10-17 改为仅使用 ZRAM，删除磁盘 swap 自动启用逻辑，并注释 fstab 中的旧条目；重复执行不会重置正在使用的压缩盘，异常初始化状态会拒绝破坏性重置。

本次启动还暴露Wi-Fi固件MAC与原配置绑定不一致。已备份原连接，解除设备MAC匹配约束，并沿用本机原连接地址作为克隆MAC，正常重启自动联网通过。具体地址和凭据不公开。

## 未完成与回滚

仍待用户物理画面/触摸确认、实际游戏负载和长期运行回归。ZRAM不能保证所有内存耗尽均不退出，也没有证明GPU冻结已修复。PSI接口已存在，原系统自定义target没有自动拉起systemd-oomd，本轮不额外启用其杀进程策略。

用户态回滚：禁用axon-memory.service即可阻止下次启动配置；不要在低可用内存时直接swapoff。内核回滚使用已验证#44完整boot备份，经Fastboot恢复boot_a并回读；REC保留。旧内核无zram0时服务明确失败，不会自动恢复旧磁盘 swap；回滚旧内核时须另行选择并配置交换方案。

## 2026-10-17 单一交换方案

按用户要求取消双方案并行：仅保留 2 GiB LZ4 ZRAM。旧 2 GiB swapfile 保留作备份，不参与交换。停用时其占用为零；脚本在处理有占用的旧 swap 时要求 MemAvailable 大于已用磁盘 swap 加 512 MiB 余量，swapoff 失败则报告服务失败。重复执行不重置正在使用的 ZRAM。swappiness 40 保持不变。

正常重启实机验证通过：#45，/proc/swaps 仅有 /dev/zram0（2097148 KiB 可用，优先级100），压缩算法 lz4；axon-memory.service active，systemd 无失败服务，SSH 恢复。
