# sbbox-tuned

> 基于 **sing-box 1.14 单内核** 的全协议抗封锁与安全加固代理套件。
> 涵盖 **Hysteria2 / NaiveProxy / TUIC v5 / AnyTLS / Nowhere / VLESS-Reality**，配备 SPKI/SHA-256 证书指纹锁定、内核级 BBRv3 流控与全客户端自动订阅。

**语言：** **简体中文** · [English](./README.en.md)

---

## ⚡ 快速一键部署

### 1. 默认推荐部署（四大主力协议 + 自动申请证书）
```bash
bash <(curl -Ls https://raw.githubusercontent.com/shjzzzz/sbbox-tuned/main/sbbox.sh) alns=1 ym=你的域名
```

### 2. 全协议部署（含 Reality 与自研 Nowhere 协议）
```bash
bash <(curl -Ls https://raw.githubusercontent.com/shjzzzz/sbbox-tuned/main/sbbox.sh) reap=1 alns=1 ym=你的域名
```

---

## 📡 协议矩阵与梯队

| 梯队 | 协议方案 | 传输方式 | 伪装与安全特性 | 适用场景 |
| :---: | :--- | :--- | :--- | :--- |
| 🥇 | **Hysteria2** | UDP / QUIC (H3) | Salamander 密码混淆 + 端口跳跃 | 弱网恶劣丢包极速回血、跑满千兆带宽 |
| 🥈 | **NaiveProxy** | H3 (QUIC) & H2 (TCP) | Chromium 原生网络栈内核反探测伪装 | 高危封锁期与敏感业务防指纹识别 |
| 🥉 | **TUIC v5** | UDP / QUIC (H3) | 标准 QUIC 0-RTT + Congestion Control | 跨洋低延迟交互、UDP 流量平滑转发 |
| 💣 | **AnyTLS** | TCP + TLS 1.3 | 消除 TLS-in-TLS 特征 + 自适应 8 级填充 | 纯 TCP 环境全平台高隐匿穿透 |
| ⚡ | **Nowhere** | TLS/QUIC 混合中继 | 上下行独立传输分流（上行 TCP / 下行 UDP） | 规避运营商 UDP 恶性丢包并保持下行极速 |
| 🛡️ | **VLESS-Reality** | TCP (xtls-rprx-vision) | 借用官方 SNI 借壳偷渡（免真实证书） | 全平台客户端即开即用备用通道 |

---

## 🛠️ 管理工具 `sbbox`

安装完成后直接输入 `sbbox` 即可呼出交互式管理看板：

```bash
sbbox status          # 查看 sing-box / nowhere 守护进程、端口与流控状态
sbbox node            # 查看全部协议参数、连接链接与订阅地址
sbbox sub             # 获取各平台专用订阅链接与终端二维码
sbbox restart         # 平滑重启 sing-box 及关联 sidecar 进程
sbbox log             # 查看实时访问日志
sbbox cert sync       # 证书轮换检查与 SPKI 指纹热重载
sbbox keepalive on    # 开启后台智能保活自愈机制
sbbox autoupdate on   # 开启每周内核自动安全平滑更新
```

---

## 🚀 性能与安全加固亮点

1. **单内核统一承载**：由官方最新稳定版 sing-box 单进程直接驱动四大协议，拒绝多进程套娃，内存占用降低 70%。
2. **中间人劫持防护（Pinning）**：提取证书 SHA-256 指纹（`pinSHA256`）与 SPKI 公钥 Hash 写入客户端配置，杜绝证书替换或中间人嗅探。
3. **Nowhere 上下行分流 Sidecar**：上行使用 TLS/TCP 彻底避开国内运营商对 UDP 上行的 QoS 丢包；下行使用 QUIC/UDP 享受无队头阻塞极速传输。
4. **内核级流控对齐**：系统级自动加载 BBRv3 + FQ，优化 TCP/UDP 套接字缓冲区，保障高并发大吞吐稳定不掉线。
