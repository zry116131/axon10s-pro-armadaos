# Secondary PON 修复验证（2026-10-17）

稳定 #45 的启动日志可复现第二个 PMIC PON 注册同名 reboot-mode 设备失败：-EEXIST，主 reboot_modes sysfs 接口丢失。主 pm8941_pwrkey 输入驱动仍存在。

临时候选 #54（7.2.6-axon10s-pon1）仅将空的 /soc@0/spmi@c440000/pmic@a/pon@800 标记 disabled。该节点没有子功能或重启模式；保留主 PMIC PON、电源键、bootloader/recovery 值。等价板级片段见 runtime/pm8009-pon.dtsi。

构建严格基于保留的 #45 源码/输出。逐属性比较确认 DT 只有这一项新增；内核配置仅 LOCALVERSION 不同，原 initramfs 字节相同，USB/ZRAM不变，Venus仍关闭。镜像 SHA256：d2fc58c78c1d643afcca3601ba77e07924bbcea159f43bd8c0a7b94c63404aa9。

实机两次 fastboot 临时启动 #54：重复注册错误消失，/sys/class/reboot-mode/qcom-pon/reboot_modes 恢复并列出 bootloader recovery；主电源键输入驱动存在，仅2GiB ZRAM启用，Steam独立游戏模式active，无systemd失败服务。

重启路径验证：#54 -> 已安装专用REC #37（USB root shell可用、分区布局识别成功）-> Fastboot -> 再次临时#54 -> Fastboot。Fastboot读回槽A successful=yes。未写boot/REC分区，尚未验证实际按键事件及长期运行；临时验证不等于持久安装。

最后正常启动返回已安装 #45，SSH、独立Steam游戏模式和仅ZRAM交换再次检查通过。
