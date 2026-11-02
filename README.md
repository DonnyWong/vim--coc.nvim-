# iTerm2 状态栏：CPU 占用与 CPU 温度

`AutoLaunch/system_monitor.py` 用一个 Python 进程提供 **CPU Usage** 和 **CPU Temperature** 两个组件。CPU 占用来自 macOS Mach 系统接口；温度使用可选的 iStats 后端，默认关闭，显示 `Temp N/A`。

脚本只采样这两项，不读取内存压力、swap、压缩内存、热状态、风扇或功耗。默认不启动外部命令，不需要 Ruby、psutil、PyObjC 或 Homebrew。

本 PR 基于 [PR #2](https://github.com/DonnyWong/vim--coc.nvim-/pull/2) 的 `iTerm2` 分支，目标分支也是 `iTerm2`。

## 安装与迁移

要求：macOS、Python **3.9+**，以及已启用 Python API 的 iTerm2。推荐使用 iTerm2 管理的 Python 环境；可通过 Scripts → Manage → New Python Script 按提示安装，选择 Basic。如缺少 `iterm2` 包，通过 Manage Dependencies 安装到该环境。

1. 停止旧监控脚本，或先退出 iTerm2、在另一终端迁移。
2. 在仓库根目录运行以下命令。备份放在 AutoLaunch 外，以免同时启动旧脚本。

```sh
(
set -eu
monitor_scripts="$HOME/Library/Application Support/iTerm2/Scripts"
monitor_auto="$monitor_scripts/AutoLaunch"
mkdir -p "$monitor_auto"
monitor_backup="$(mktemp -d "$monitor_scripts/monitor-backup.XXXXXX")"
for monitor_file in cpu_temperature.py fan_speed.py memory_usage.py power_wattage.py system_monitor.py; do
    if [ -e "$monitor_auto/$monitor_file" ]; then
        mv "$monitor_auto/$monitor_file" "$monitor_backup/"
    fi
done
cp AutoLaunch/system_monitor.py "$monitor_auto/system_monitor.py"
printf 'Backup: %s\n' "$monitor_backup"
)
```

3. Settings → General → Magic → **Enable Python API**。重启 iTerm2，或从 Scripts → AutoLaunch 启动一次 `system_monitor`。
4. Profiles → Session → Status bar enabled → Configure Status Bar，添加 **CPU Usage、CPU Temperature**。移除旧的 Memory Pressure、Thermal State、Fan Speed 和 Power 组件，避免留下无法调用的旧组件。温度的旧 identifier `vxider.iterm-components.cpu_temperature` 保留。

原有 Sushi、网络、路径等其他组件由用户自己的布局决定，迁移命令只替换监控脚本。卸载时停止 `system_monitor`，把脚本移出 AutoLaunch 并移除这两个组件；回滚时把备份脚本移回并重启。

## 读数与开销

| 组件 | 数据来源 | 显示与限制 |
| --- | --- | --- |
| CPU Usage | Mach `host_statistics(HOST_CPU_LOAD_INFO)` 的 user/system/nice/idle 计数增量 | `CPU 25%`，全部核心归一到 0–100%；首次采样、长时间未采样、计数重置或失败时显示 `CPU N/A` |
| CPU Temperature | 可选 `istats cpu temp --value-only` | 有效读数显示 `CPU 48.5°C`；后端未启用、不可用或读数失败时显示 `Temp N/A` |

CPU 默认 **5 秒**刷新一次，多个窗口和分屏共享缓存。没有组件请求时不主动采样，温度也不会触发 CPU 采样。温度启用后默认 **30 秒**一次，通过参数数组调用，不经 shell；单次最多 **2 秒 / 8 KiB 输出**，超时或取消会回收整个进程组。失败后丢弃旧值，按 60、120、240、300 秒退避，配置的更长周期仍有效。

可选配置，修改后重启脚本：

```sh
cp system_monitor.example.json "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/system_monitor.json"
```

- `interval`：CPU 刷新间隔，5–60 秒，默认 5。
- `sensor_interval`：温度刷新间隔，30–3600 秒，默认 30。
- `enable_istats`：默认 `false`；仅在目标机器验证温度读数后启用。
- `istats_path`：默认 `null`；依次检查 GUI 的 PATH、`/opt/homebrew` 和 `/usr/local` 的常见位置。自定义 gem/rbenv 安装可填写绝对路径；GUI 的 PATH 可能与终端不同。

## Apple Silicon 温度限制

CPU 占用不依赖 Intel SMC 传感器。摄氏度读数仍依赖具体机型与第三方后端；仅修改 Homebrew 路径不能保证传感器兼容。

[iStats 上游](https://github.com/Chris911/iStats) 没有提供可据以确认 M6 CPU 温度支持的保证，因此默认关闭后端。未读到温度时显示 `N/A`，不以热状态或估算数字代替摄氏度。

如本机已安装 iStats，可先手动检查：

```sh
command -v istats
istats cpu temp --value-only
```

确认传感器含义、随负载变化是否合理，并与另一个可信读数交叉核对后，再启用 `enable_istats`。数字解析通过只能证明格式符合要求，不能证明传感器适配正确。可评估 [Stats](https://github.com/exelban/stats) 的传感器页面，并核对其对具体机型和 macOS 的支持；本脚本没有集成 Stats，也未验证其 M6 支持。

## 验证

```sh
python3 AutoLaunch/system_monitor.py --diagnose --samples 2
python3 -m unittest discover -s tests -v
python3 tools/benchmark_monitor.py --samples 12
```

诊断只输出 CPU 计数、CPU 占用、温度及读取错误。首条 CPU 为 `null`，约 5 秒后第二条应有有效占用值。默认温度报告后端关闭。`--config /绝对路径/settings.json` 可指定配置。

基准测量 CPU 采样进程，不含 iTerm2 UI、可选温度命令或直播负载。测试覆盖 CPU 首样本/环绕/计数重置、缓存、失败降级、路径查找、温度解析、超时/取消，以及恰好两个组件的注册。安装 `iterm2` 包后会校验真实库的注册协议。结果见 [VERIFICATION.md](VERIFICATION.md)，远程 CI 以 PR Checks 为准。

CPU 和温度不能独自判断 1080p60 是否稳定；长时间直播仍应观察 OBS 的渲染、编码和网络丢帧统计。本次没有完成长时间直播负载测试。

iTerm2 文档：[运行脚本](https://iterm2.com/python-api/tutorial/running.html)、[状态栏示例](https://iterm2.com/python-api/examples/statusbar.html)。
