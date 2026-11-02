# iTerm2 状态栏：CPU 占用与 CPU 温度

`AutoLaunch/system_monitor.py` 用一个 Python 进程提供 **CPU Usage** 和 **CPU Temperature** 两个组件。CPU 占用来自 macOS Mach 系统接口；Apple Silicon 温度使用 **macmon** 的 CPU 传感器平均值，已在本机 Apple M6 / macOS 27.2 上验证。

状态栏只显示这两项。Python 核心只读取 CPU 计数；温度启用后每 30 秒执行一次短命令。macmon 的 JSON 快照内部包含其他硬件指标，脚本只使用 `temp.cpu_temp_avg`，不注册内存、swap、热状态、风扇或功耗组件。不需要 sudo、后台服务、HTTP 端口、Ruby、psutil 或 PyObjC。

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
monitor_config="$HOME/Library/Application Support/iTerm2/system_monitor.json"
mkdir -p "$monitor_auto"
monitor_backup="$(mktemp -d "$monitor_scripts/monitor-backup.XXXXXX")"
if [ -e "$monitor_config" ]; then
    cp "$monitor_config" "$monitor_backup/system_monitor.current.json"
elif [ -f "$monitor_auto/system_monitor.json" ]; then
    cp "$monitor_auto/system_monitor.json" "$monitor_config"
fi
for monitor_file in cpu_temperature.py fan_speed.py memory_usage.py power_wattage.py system_monitor.py system_monitor.json; do
    if [ -e "$monitor_auto/$monitor_file" ]; then
        mv "$monitor_auto/$monitor_file" "$monitor_backup/"
    fi
done
cp AutoLaunch/system_monitor.py "$monitor_auto/system_monitor.py"
printf 'Backup: %s\n' "$monitor_backup"
)
```

3. Apple Silicon 上安装温度工具，验证有非空的 `temp.cpu_temp_avg`，再复制配置。示例会启用 macmon；没有配置文件时温度后端保持关闭。

```sh
brew install macmon
macmon pipe --samples 1 --interval 100
monitor_config="$HOME/Library/Application Support/iTerm2/system_monitor.json"
if [ ! -e "$monitor_config" ]; then
    cp system_monitor.example.json "$monitor_config"
fi
```

4. Settings → General → Magic → **Enable Python API**。重启 iTerm2，或从 Scripts → AutoLaunch 启动一次 `system_monitor`。
5. Profiles → Session → Status bar enabled → Configure Status Bar，添加 **CPU Usage、CPU Temperature**。移除旧的 Memory Pressure、Thermal State、Fan Speed 和 Power 组件，避免留下无法调用的旧组件。温度的旧 identifier `vxider.iterm-components.cpu_temperature` 保留。

配置必须放在 `~/Library/Application Support/iTerm2/system_monitor.json`，位于 `Scripts` 目录外。**不要将 JSON 放入 AutoLaunch**：iTerm2 会尝试启动其中的文件，导致“应用程序 system_monitor.json 无法打开”。上述迁移命令会保留旧配置内容，并将旧位置的 JSON 移入备份。`--config` 仍可指定其他位于 AutoLaunch 外的文件。

原有 Sushi、网络、路径等其他组件由用户自己的布局决定，迁移命令只替换监控脚本。卸载时停止 `system_monitor`，把脚本移出 AutoLaunch 并移除这两个组件；回滚时把备份脚本移回并重启。

## 读数与开销

| 组件 | 数据来源 | 显示与限制 |
| --- | --- | --- |
| CPU Usage | Mach `host_statistics(HOST_CPU_LOAD_INFO)` 的 user/system/nice/idle 计数增量 | `CPU 25%`，全部核心归一到 0–100%；首次采样、长时间未采样、计数重置或失败时显示 `CPU N/A` |
| CPU Temperature | `macmon pipe --samples 1 --interval 100` 的 `temp.cpu_temp_avg` | 如 `CPU 76.8°C`，代表 CPU 传感器平均值，不是最热点；后端未启用、缺失、返回 null 或读数失败时显示 `Temp N/A` |

CPU 默认 **5 秒**刷新一次，多个窗口和分屏共享缓存。没有组件请求时不主动采样，温度也不会触发 CPU 采样。温度默认 **30 秒**一次，多个窗口共享同一次调用。macmon 每次只取一个样本并退出，参数数组调用不经 shell；最多 **4 秒 / 64 KiB 输出**，超时或取消会回收整个进程组。失败后丢弃旧值，按 60、120、240、300 秒退避，配置的更长周期仍有效。

可选配置，修改后重启脚本：

```sh
cp system_monitor.example.json "$HOME/Library/Application Support/iTerm2/system_monitor.json"
```

- `interval`：CPU 刷新间隔，5–60 秒，默认 5。
- `sensor_interval`：温度刷新间隔，30–3600 秒，默认 30。
- `temperature_backend`：`disabled`、`macmon` 或 `istats`；无配置文件时为 `disabled`，配置示例使用 `macmon`。
- `macmon_path`：默认 `null`；检查 GUI 的 PATH、`/opt/homebrew/bin/macmon` 和 `/usr/local/bin/macmon`，也可指定绝对路径。本机安装配置显式指定 `/opt/homebrew/bin/macmon`。
- `istats_path`：旧 iStats 后端的绝对路径或 `null`；保留 PATH、Apple Silicon/Intel Ruby 常见路径发现。旧配置 `enable_istats: true` 仍可用，但不能同时启用 macmon。iStats 保留 2 秒 / 8 KiB 限制，未验证其 M6 支持。

## Apple Silicon 温度限制

macmon 是 [Homebrew 官方源](https://formulae.brew.sh/formula/macmon) 提供的 Apple Silicon 工具；[v0.10.0](https://github.com/vladkens/macmon/releases/tag/v0.10.0) 增加了 M6 CPU 架构支持。本次在系统报告为 Apple M6、Mac18,5、macOS 27.2 的机器实际读取成功，见 [VERIFICATION.md](VERIFICATION.md)。

其[温度实现](https://github.com/vladkens/macmon/blob/v0.10.0/src/metrics.rs)读取 SMC / IOHID 硬件传感器，对有效 CPU 读数求平均。本机 SMC 的 39 个 `Tp` / `Te` / `Ts` 温度读数均值约 76.82°C，与相邻时间的 macmon 平均值约 76.6–77.0°C 对应。这是同一传感器来源的交叉检查，不是外部仪器校准。

这些是机型相关的私有接口；其他芯片、macOS 更新或虚拟机可能没有有效温度。缺少 CPU 温度时保持 `N/A`，不回退到 GPU 温度、热状态或上次成功值。JSON 解析拒绝字符串、布尔值、非有限值和越界值。状态栏的平均温度不能代表最热点温度。

## 验证

```sh
python3 AutoLaunch/system_monitor.py --diagnose --samples 2
python3 AutoLaunch/system_monitor.py --diagnose --samples 2 --config system_monitor.example.json
python3 -m unittest discover -s tests -v
python3 tools/benchmark_monitor.py --samples 12
```

诊断只输出 CPU 计数、CPU 占用、温度、后端名称及读取错误。首条 CPU 为 `null`，约 5 秒后第二条应有有效占用值；温度在 30 秒缓存期内保持同一次读数。`--config /绝对路径/settings.json` 可指定本机配置。

基准测量 CPU 采样进程，不含 iTerm2 UI、可选温度命令或直播负载。测试覆盖 CPU 首样本/环绕/计数重置、缓存、失败降级、路径查找、温度解析、超时/取消，以及恰好两个组件的注册。安装 `iterm2` 包后会校验真实库的注册协议。结果见 [VERIFICATION.md](VERIFICATION.md)，远程 CI 以 PR Checks 为准。

CPU 和温度不能独自判断 1080p60 是否稳定；长时间直播仍应观察 OBS 的渲染、编码和网络丢帧统计。本次没有完成长时间直播负载测试。

iTerm2 文档：[运行脚本](https://iterm2.com/python-api/tutorial/running.html)、[状态栏示例](https://iterm2.com/python-api/examples/statusbar.html)。
