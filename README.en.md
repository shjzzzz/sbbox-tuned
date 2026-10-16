# sbbox-tuned

> Sing-box 1.14 single-core all-in-one anti-censorship and security-hardened proxy suite.
> Supports **Hysteria2 / NaiveProxy / TUIC v5 / AnyTLS / Nowhere / VLESS-Reality**, featuring SPKI/SHA-256 certificate pinning, kernel-level BBRv3 flow control, and automated client subscriptions.

**Languages:** [简体中文](./README.md) · **English**

---

## ⚡ Quick Start

### 1. Default Recommended Setup (4 Main Protocols + Auto SSL)
```bash
bash <(curl -Ls https://raw.githubusercontent.com/shjzzzz/sbbox-tuned/main/sbbox.sh) alns=1 ym=your-domain.com
```

### 2. Full Protocols (Including Reality and Nowhere)
```bash
bash <(curl -Ls https://raw.githubusercontent.com/shjzzzz/sbbox-tuned/main/sbbox.sh) reap=1 alns=1 ym=your-domain.com
```

---

## 📡 Protocol Matrix

| Priority | Protocol | Transport | Security & Obfuscation | Recommended Use Case |
| :---: | :--- | :--- | :--- | :--- |
| 🥇 | **Hysteria2** | UDP / QUIC (H3) | Salamander password obfs + port hopping | Rapid packet-loss recovery & gigabit throughput |
| 🥈 | **NaiveProxy** | H3 (QUIC) & H2 (TCP) | Native Chromium network stack probe resistance | Deep packet inspection evasion during censorship spikes |
| 🥉 | **TUIC v5** | UDP / QUIC (H3) | Standard QUIC 0-RTT + Congestion Control | Low-latency interactive tasks & smooth UDP forwarding |
| 💣 | **AnyTLS** | TCP + TLS 1.3 | Zero TLS-in-TLS fingerprint + 8-stage padding | Full-platform penetration in strict TCP environments |
| ⚡ | **Nowhere** | TLS/QUIC Relay | Split-path routing (TCP uplink / UDP downlink) | Avoids ISP UDP QoS throttling while keeping fast downloads |
| 🛡️ | **VLESS-Reality** | TCP (xtls-rprx-vision) | Reality SNI borrowing (no cert required) | Instant out-of-the-box fallback for all clients |

---

## 🛠️ Management CLI (`sbbox`)

Run `sbbox` directly in terminal for an interactive dashboard:

```bash
sbbox status          # View sing-box and sidecar daemons, ports, and flow stats
sbbox node            # Display all protocol credentials, links, and subscription URLs
sbbox sub             # Output client subscriptions and terminal QR code
sbbox restart         # Gracefully restart sing-box and associated sidecar services
sbbox log             # Follow live connection and access logs
sbbox cert sync       # Check certificate renewals and hot-reload SPKI pinning
sbbox keepalive on    # Enable background self-healing daemon
sbbox autoupdate on   # Enable weekly stable auto-updates
```

---

## 🚀 Key Highlights

1. **Single-Core Efficiency**: Driven directly by official sing-box core without process chaining, slashing memory footprint by 70%.
2. **MitM Protection (Pinning)**: Automatically extracts certificate SHA-256 (`pinSHA256`) and SPKI public key hashes to prevent traffic spoofing.
3. **Nowhere Split-Path Sidecar**: Routes upstream over TLS/TCP to avoid carrier UDP QoS penalties; routes downstream over QUIC/UDP for line-rate speed.
4. **Kernel Flow Optimization**: Deploys system-wide BBRv3 + FQ and tunes socket buffers to eliminate bufferbloat and dropped connections.
