# 经验教训与规则库 (Lessons Learned & Rules)

## 1. GitHub 远程同步审批红线 (2026-11-01)
- **核心铁律**：任何代码、脚本、配置或文档推送到远程仓库（`git push`、创建或推送 Release Tag 等），**必须由用户明确批准后方可执行**。
- **治理与防范规则**：
  1. 无论本地代码是否通过测试，修改验证完毕后仅在本地做 `git commit` 保存，严禁擅自、隐式或自动执行 `git push`；
  2. 必须在回复中向用户展示修改摘要与测试结果，明确请求确认：“是否批准推送到 GitHub 远程仓库？”；
  3. 仅在收到用户明确肯定的指示后，方可执行远程同步。

## 2. 安装参数与管理子命令解耦规范 (2026-10-31)
- **错误现象**：用户执行官方推荐的默认安装命令 `bash <(curl -Ls ...) alns=1 ym=xxx` 时，脚本报错 `未知命令: alns=1` 并异常中断退出。
- **根本原因**：多功能单脚本（同时作为安装脚本与管理 CLI）在参数提取时，直接将 `$1` 视为子命令 `$cmd` 传入 `case "$cmd"`，导致安装类 `key=value` 参数（如 `alns=1`、`ym=...`、`hyp=1`）被误当成未知管理子命令而触发通配拦截报错。
- **治理与防范规则**：
  1. **智能参数分流**：遍历参数时，若参数包含 `*=*` 或为 `install/reinstall`，必须置位 `has_install_args=1`；仅当参数纯为已知子命令名时才提取为 `$cmd`；
  2. **安装模式豁免**：存在安装类参数（`has_install_args=1`）时，坚决跳过管理分发器的通配报错，直接安全进入核心安装流程；
  3. **放开默认协议集适配范围**：移除协议判定中多余的 `[ ! -x "$SB_BIN" ]` 条件，确保存量机器重跑安装命令时也能正确注入默认协议集。

## 3. TCP 与 UDP 传输参数对齐与协议分立规范 (2026-11-06)
- **背景与根因**：
  1. TUIC 原客户端配置及链接中残留 `cubic` 拥塞控制，在跨网存在偶发抖动与轻微丢包时触发窗口剧烈回退；参考 argosbx 最新实践，TUIC 全端统一为 `bbr` 与原生 UDP 数据报转发（`udp_relay_mode=native`，`reduce-rtt: true`），消除带宽吞吐塌缩与首包延迟。
  2. 原 Naive-H2 客户端配置中误配 `"quic": true`，导致 Naive-H2 与 Naive-H3 均走向 QUIC/UDP，在 UDP 遭运营商劣化或封锁的网络环境下两节点全灭。
  3. sing-box 原生 inbound/outbound 对字段有强类型校验（如 `udp_relay_mode` 仅属 outbound、`anytls` 不支持 `tcp_fast_open`、`hysteria2` 出站不支持 `fast_open` 字段），不可盲目堆叠字段。
- **治理与防范规则**：
  1. **双 Naive 严格分立**：Naive-H3 锁定纯 QUIC+BBR 数据报；Naive-H2 锁定纯 TCP（`quic: false` + UoT v2），形成互补备份。
  2. **Mihomo 针对性加速**：在 Mihomo `clmi.yaml` 中，Hysteria2 节点启用 `fast-open: true` 与 `128M/64M` 接收窗口；TUIC 节点启用 `reduce-rtt: true` 与 `congestion-controller: bbr`。
  3. **严格语法校验**：配置变更后必须执行 `sing-box check` 与 Python YAML 解析校验，再通过 `sbbox selftest` 实测验证握手状态。
