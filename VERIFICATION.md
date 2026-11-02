# 本次验证记录

日期：2026-11-02（Asia/Shanghai）。目标分支：`iTerm2`。本记录针对仅保留 CPU 占用与 CPU 温度的版本。

## 已完成

- iTerm2 管理的 Python 3.12.13：19 项测试全部通过，包括实际 iTerm2 库的注册协议、CPU 首样本/计数环绕/长间隔、缓存共享、温度解析、超时与进程回收。
- 原生 CPU 两次采样成功：`errors: {}`；首条 CPU 为未知，第二条为有效百分比。诊断输出只含 CPU、温度及错误信息。
- Python 编译、`git diff --check`、README 的 shell 示例语法检查通过。
- 本机 iTerm2 3.7.6 安装完成；Default、直播、上课三个配置仅保留 CPU Usage 和 CPU Temperature 两个新监控组件。原有其他组件保留。
- 通过真实 iTerm2 API，两次间隔 6 秒的调用均返回 CPU 百分比与 `Temp N/A`。已确认旧内存、热状态、风扇、功耗 RPC 均不再注册。
- 只重启监控脚本，未关闭终端会话。仅一个监控 Python 进程；运行快照 RSS 22.25 MiB、ps 瞬时 CPU 0.0%。该快照不是严格性能基准，不包含 iTerm2 UI 或其他脚本开销。
- 修改前再次备份 AutoLaunch 和完整偏好设置。本机未找到 iStats，温度后端保持关闭。

## 限制

CPU 原生接口已在本机 arm64 环境读取成功；这不代表目标机型的摄氏度传感器已验证。未安装或运行第三方传感器工具，也没有用热状态代替温度。

未完成第三方 CPU 温度读数交叉验证、Intel 实机检查或 30–60 分钟真实直播测试。之前包含内存/热状态的 60 秒基准不作为此精简版本的性能数据；可使用 `tools/benchmark_monitor.py` 重测。

CI 在 Linux 和 macOS 执行测试，最终结果以 PR Checks 为准。
