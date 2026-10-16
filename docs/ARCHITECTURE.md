# 移植方法与关键发现

## 系统结构

原机 Qualcomm 引导链 → Android boot v2 容器 → 自编译 ARM64 Linux 与板级设备树 → 内部 ext4 根文件系统 → ArmadaOS 用户空间 → SDDM / Plasma / Gamescope / Steam。

ARM64 原生内核负责硬件，兼容组件处理需要的 x86 游戏/程序。具体游戏可能涉及 FEX、Proton/Wine 与 DXVK；进入 Steam 菜单不代表所有游戏已经兼容。

## 关键工作

1. 参考 ArmadaOS、ROCKNIX 的 SM8250 路线与 Y700 移植结构，使用标准 ARM64 defconfig 加板级配置。保留中兴设备自身的供电、存储、显示和触屏描述。
2. 从原厂设备树提取 RM692A4 面板命令与时序，适配 Synaptics S3908/TCM 触屏。原厂数据为硬件描述来源，完整原厂内核无法直接作为主线驱动使用。
3. 排查 boot 镜像末尾旧 Android RTIC 元数据。移除额外 173 字节 RTIC 树、保留三个原厂硬件 DTB 后，标准配置内核成功启动；该发现仅适用于本机打包路径。
4. 在 initramfs/systemd 交接中安排显示、固件与用户会话；独立 Plasma 启动前释放早期 splash 的 DRM 占用。
5. 将原 Android super 空间在 GPT 层面合入一个连续根分区，备份、校验迁移对象并验证恢复。保留启动链、校准与恢复用途的分区。
6. 专用 Recovery 使用 RAM 根文件系统、按键菜单与 USB 诊断通道，提供机器可读状态和修复入口。
7. 游戏模式采用 SDDM 会话切换；Steam 游戏输入需要 uinput，物理蓝牙手柄在菜单里可用不能证明游戏虚拟手柄已经创建。

## 不能直接搬用的部分

其他 SM8250/Y700 设备的 ABL、设备树、分区表及校准固件不能直接刷入本机。Recovery 的 Android boot 容器、原厂 recovery DTBO、BCB 及 A/B 状态处理也必须符合本机结构。现有布局和脚本仅经过单台开发设备验证。
