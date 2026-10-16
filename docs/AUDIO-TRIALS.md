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

下一步保持硬件配置，补早期RAM USB命令shell与挂根步骤标记，再定位阻塞位置。尚无录音测试、实际麦克风路由或9380/9385型号验收。

## 供电边界

复位极性与原厂active-high/sleep-low行为一致；主线ACTIVE_LOW表示逻辑assert时拉低。S4A实测1800mV。BOB实测3032mV，与原厂codec请求3296mV不同；其为共享电源，本轮不改电压、不启用录音，后续采集前需单独核对影响。
