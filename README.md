# iTerm2 状态栏：Apple Silicon 直播监控

`AutoLaunch/system_monitor.py` 用**一个 Python 进程**提供 CPU、内存压力、热状态，以及可选温度/风扇组件。默认只读取 macOS 系统接口，不运行 shell、`ps`、`top`、`system_profiler`、`sudo` 或硬件传感器工具，不需要 Ruby、psutil、PyObjC 或 Homebrew。

这次改造基于 PR [#2](https://github.com/DonnyWong/vim--coc.nvim-/pull/2) 的 `iTerm2` 分支。该分支与 `main` 的 Vim 配置不同；新 PR 的目标分支为 `iTerm2`，方便单独审阅监控变化。

## 安装与旧版迁移

要求：macOS、Python **3.9+**，以及已启用 Python API 的 iTerm2。推荐用 iTerm2 管理的 Python 环境；首次使用可在 Scripts → Manage → New Python Script 中按提示安装运行环境，选择 **Basic**。若界面提示缺少 `iterm2` 包，使用 Scripts → Manage → Manage Dependencies 安装到该环境。终端中的 `python3` 可能是另一个环境。

1. 检出本 PR 的分支，进入仓库根目录。
2. 停止旧的四个监控脚本（Scripts 菜单中运行的脚本可停止），或先退出 iTerm2、在另一终端迁移。备份必须放在 **AutoLaunch 外**，否则旧进程可能继续自动启动。
3. 在仓库根目录执行以下命令。只安装新监控文件，不要把整个旧 `AutoLaunch` 目录一起复制过去。

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

4. iTerm2 Settings → General → Magic → **Enable Python API**。重启 iTerm2；也可从 Scripts → AutoLaunch → system_monitor 手动启动一次，避免重复运行。
5. Profiles → Session → **Status bar enabled** → Configure Status Bar，加入 **CPU Usage、Memory Pressure、Thermal State**。温度、风扇和功耗组件按需添加。旧的内存、温度、风扇、功耗 identifier 已保留，旧布局通常可继续识别；CPU 和热状态为新组件。文本不依赖 Nerd Font。

`SushiStatusBar.py`、天气、AQI、电池脚本仍是历史可选脚本，不在此次监控改造范围。Mac mini 不需要电池脚本；直播时建议停止 0.5 秒刷新的 Sushi 动画及不需要的旧脚本。新安装流程不会启动它们；已经装过的脚本需在 Scripts 菜单停止并移出 AutoLaunch。

卸载：停止 `system_monitor`，把 `system_monitor.py` 移出 AutoLaunch，移除新组件；若回滚旧版，把上述备份中的脚本移回 AutoLaunch 并重启。旧版仍存在本文列出的平台和指标限制。

## 状态栏读数的含义

| 组件 | 数据来源 / 定义 | 使用时的限制 |
| --- | --- | --- |
| CPU Usage | Mach `host_statistics(HOST_CPU_LOAD_INFO)` 的 user/system/nice/idle 计数增量；全部 CPU 的繁忙时间占比，归一到 0–100% | 首次、长时间未采样、计数器重置时为 `N/A`；不表示单个性能核心或 GPU/编码引擎是否满载 |
| Memory Pressure | `sysctlbyname("kern.memorystatus_vm_pressure_level")`：1 Normal、2 Warning、4 Critical | 这是内核的离散压力通知等级，不是活动监视器的连续曲线，也不是“已用内存百分比” |
| Swap | `sysctlbyname("vm.swapusage")` 的已用交换空间 | 单位 G 为 GiB；已有 swap 可能是之前的负载留下的，单看非零值不能判定卡顿 |
| Comp | Mach `HOST_VM_INFO64` 的压缩器实际占用页数 × 系统 VM 页大小 | 单位 GiB；不是压缩前的逻辑内存大小，不硬编码 4 KiB（Apple Silicon 常为 16 KiB） |
| Out | 两次 VM `swapouts` 页数差 × 页大小 ÷ 真实采样间隔 | 单位 M/s 为 MiB/s；是逻辑换出量，不是压缩后 SSD 实际写入带宽；第一次为 `N/A` |
| Thermal State | Foundation `NSProcessInfo.thermalState`：Nominal / Fair / Serious / Critical | 系统热状态，不是摄氏度，也不能量化降频；Critical 表示热状态已明显影响系统性能 |
| CPU Temperature / Fan Speed | 可选 iStats 传感器读数，默认关闭 | `N/A` 表示未知，不能推断为 0°C、停转或无风扇；有效数字 0 RPM 会保留，多风扇逐项显示 |
| Power | 默认 `Power N/A`，不采样 | 旧脚本的适配器额定瓦数不是实时耗电，Mac mini 也不能套用笔记本充电器指标 |

内存组件空间足够时显示 `Mem Normal | Swap 1.0G | Comp 2.3G | Out 0.0M/s`，窄窗口保留压力和 swap。任一接口无权限、被系统移除或返回未知值，该项显示 `N/A`，其他指标继续工作，不把读取失败伪装成正常。

Apple 将内存压力与可用内存、交换速率、有线内存和缓存共同联系起来，不能用进程 `%mem` 求和替代。[Apple 内存说明](https://support.apple.com/guide/activity-monitor/view-memory-usage-actmntr1004/mac)
压力 sysctl 返回的是用户态通知值 **1/2/4**，不是 XNU 内部的 0/1/2/3 枚举；这是本实现及测试明确区分的地方。[XNU 实现](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_memorystatus_notify.c)
热状态的定义见 [Apple ProcessInfo.ThermalState](https://developer.apple.com/documentation/foundation/processinfo/thermalstate-swift.enum)。

## 开销和刷新频率

默认 CPU、内存、热状态共享 **5 秒缓存**；多个组件、标签页、分屏只读同一份采样结果，不按会话创建监控进程。不挂后台忙循环，没有组件请求时不主动采样。首次 CPU 需要两个样本。停用很久后再次显示会重新建立速率基线。

可选传感器各自至少 **30 秒**一次，单个子进程最多 **2 秒 / 8 KiB 输出**；用参数数组调用，不经 shell。超时或取消会杀死并回收进程组。失败后显示 `N/A`，按 60、120、240、300 秒退避（配置的更长周期仍有效）。温度失败不会隐藏正常的风扇读数，也不会阻塞基础指标；不会反复输出错误刷日志。

可复制配置示例并修改，重启脚本后生效：

```sh
cp system_monitor.example.json "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/system_monitor.json"
```

- `interval`：5–60 秒，默认 5；长时间直播可设为 10。
- `sensor_interval`：30–3600 秒，默认 30。
- `enable_istats`：默认 `false`。
- `istats_path`：默认 `null`；启用时按 GUI 进程的 PATH、`/opt/homebrew/bin`、Apple Silicon Ruby 目录、`/usr/local/bin`、Intel Ruby 目录查找。gem/rbenv 自定义安装可填写绝对路径。GUI 的 PATH 不一定等于交互式 zsh 的 PATH。

配置错误会在脚本控制台明确报错。配置文件为本机文件，已加入 `.gitignore`；修改后需要重启脚本。此实现不设置风扇转速、不调整电源策略。

## 温度、风扇和 M6 支持边界

CPU/VM/sysctl/Foundation 接口不依赖 Intel SMC 键名；已有本机短时验证见 [VERIFICATION.md](VERIFICATION.md)。这不代表所有 M6 机型或所有 macOS 版本都已验证。

macOS 没有供本脚本通用读取所有机型摄氏度和风扇转速的稳定高层接口。iStats 依赖机型相关传感器；其上游文档列出的测试机型主要是老 Intel Mac，**未找到对 M6 传感器支持的可靠保证**。仅把 `/usr/local` 改成 `/opt/homebrew` 不能解决传感器兼容性。[iStats 上游](https://github.com/Chris911/iStats)

默认保持温度和风扇后端关闭。若你已安装 iStats，应先在目标机器上手动验证：

```sh
command -v istats
istats cpu temp --value-only
istats fan speed --value-only
```

确认读数来自已知传感器、随负载合理变化，且可与另一个可信读数交叉核对后，才将 `enable_istats` 改为 `true`，必要时填写 `istats_path`。解析器会拒绝空输出、文字错误、非数值及明显越界值，但**数值格式正常不等于硬件支持已验证**。找不到工具、无风扇或输出空白都显示 `N/A`；不自动安装、扫描 SMC 键、调用 sudo 或尝试控制风扇。

可行替代：

- 日常直播看 **Thermal State + Memory Pressure + Swap/Out**。这些信号比未验证的摄氏度更适合先定位热约束和内存问题。
- 需要摄氏度和 RPM 时，可评估 [Stats](https://github.com/exelban/stats) 的传感器页面，并检查其当前发布说明是否支持自己的**具体机型和 macOS**。本 PR 不宣称 Stats 或 iStats 已验证 M6，也未把 Stats 当作可直接调用的 CLI。
- 临时功耗诊断先运行 `/usr/bin/powermetrics --help` 查看本机支持的 sampler。只有列出所需 sampler 时，才手动运行下面的有限采样；不要让状态栏每 5 秒启动它：

  ```sh
  sudo /usr/bin/powermetrics --samplers cpu_power,gpu_power,thermal -i 5000 -n 3
  ```

  sampler 名称随硬件/系统不同；不要假设 Apple Silicon 有 Intel 的 `smc` sampler。`powermetrics` 的 CPU/GPU/SoC 功耗是估计量，不是整机插座功率，也不一定提供温度。系统 `man powermetrics` 同样注明其平台限制和估计性质。
- 要测 Mac mini **整机实际输入功率**，用外接插座功率计；不要把充电器额定瓦数、Activity Monitor 的 Energy Impact 或 CPU 功耗直接当作整机瓦数。

## 检查与直播验收

基础诊断和测试不需要安装 iTerm2 Python 包：

```sh
python3 AutoLaunch/system_monitor.py --diagnose --samples 2
python3 -m unittest discover -s tests -v
python3 tools/benchmark_monitor.py --samples 12
```

诊断输出逐项数据和错误；首条 CPU / Out 为 `null`，约 5 秒后第二条应有速率。正常 macOS 用户会话无需 sudo；受限执行沙箱可能阻止 pressure / swap，应在普通终端再核对。不要把权限拒绝当作 M6 不支持。`--config /绝对路径/settings.json` 可指定诊断配置。

基准约 60 秒，测量采样进程的 CPU 时间、单次采样耗时与峰值 RSS；**不含 iTerm2 UI、可选传感器或直播负载的影响**。测试覆盖 CPU 首样本/环绕、压力等级、4/16 KiB 页、缓存共享、失败降级、路径查找、解析、超时/取消与真实 macOS 接口；安装了 iTerm2 包时还校验实际 Python API 的注册协议，无须连接或改变正在使用的 iTerm2。GitHub Actions 在 Linux/macOS 运行测试。

要判断“24GB 是否够、1080p60 是否稳定”，用实际工作负载跑 **30–60 分钟**：OBS、抖音直播伴侣、iTerm2、Neovim 和平时的浏览器标签都打开，采用实际直播场景和编码设置。在活动监视器对照内存压力、swap 与压缩内存；在 OBS 的统计窗口分别观察渲染延迟、编码延迟和网络掉帧。记录开播、复杂场景切换及出现卡顿时的读数，再短暂停止本脚本做同场景对照。

持续 Warning/Critical、持续换出且同时卡顿，或热状态长期 Serious/Critical，才值得进一步减少工作负载并定位进程。不要用单次高内存占用或已有 swap 推断内存不足；CPU 不高也不能排除 GPU、编码器或网络瓶颈。具体帧丢失类型需结合 [OBS 官方排障说明](https://obsproject.com/kb/encoding-performance-troubleshooting) 判断。本 PR 没有替代这项实际直播验收，也不承诺零掉帧。

iTerm2 的脚本运行和组件安装依据：[运行脚本](https://iterm2.com/python-api/tutorial/running.html)、[状态栏示例](https://iterm2.com/python-api/examples/statusbar.html)。

