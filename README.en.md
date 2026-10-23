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
sbbox warp status|update # View WARP outbound status and rotate WireGuard credentials
sbbox argo status|update # Cloudflare Argo Tunnel status and 1-click kernel update
```

---

## 🔒 Cloudflare SSL/TLS Certificate Coordination

Tailored certificate workflows with seamless local reuse:

### Method A: Host Certificate Reuse (Recommended)
If your VPS already runs the XHTTP / Nginx stack (or uses a 15-year Cloudflare Origin CA certificate), `sbbox` automatically detects `/etc/nginx/certs`, **reuses existing certificates, and extracts SPKI pins** without binding port 80.

### Method B: Cloudflare DNS-01 API Token Auto-Renewal
For standalone domains without port 80 access:
1. Create an API Token in Cloudflare Dashboard with `Zone.DNS:Edit` permissions;
2. Run `CF_Token="your_token" ~/.acme.sh/acme.sh --issue --dns dns_cf -d yourdomain.com`;
3. Run `sbbox cert sync` to load new certs and hot-reload SPKI fingerprints and client subscriptions.

---

## 🔐 Subscription Server (HTTPS)

The subscription server started by `sbbox sub` **serves HTTPS automatically** when the certificate domain (`ym`) has a valid certificate and `python3` is installed:

```text
https://<cert-domain>:<sub-port>/<token>            # v2rayN / generic Base64
https://<cert-domain>:<sub-port>/<token>?clash=1    # Clash / Mihomo
https://<cert-domain>:<sub-port>/<token>?singbox=1  # sing-box
https://<cert-domain>:<sub-port>/<token>/qr         # QR code PNG (token required)
```

* **Use the cert domain**: the host in the URL must be the certificate domain; using the server IP fails certificate validation.
* **Renewals apply automatically**: the server reloads the certificate when its files change; no restart needed.
* **Fallback**: without a valid cert domain (or with only `busybox`) it falls back to HTTP and prints the URL.
* **Hardening**: the QR image requires a valid token; the server is multi-threaded with connection timeouts so an idle connection cannot block it; HEAD requests return no body.
* **Upgrading**: re-run the installer (it rewrites the subscription unit and restarts it) to switch; afterwards replace old `http://IP:port/...` subscription URLs in your clients with the new HTTPS domain URL.

---

## ☁️ Cloudflare WARP & Argo Tunnel Management

* **Cloudflare Argo Tunnel (`cloudflared`)**:
  - `sbbox argo status`: Check installed `cloudflared` kernel version and systemd status;
  - `sbbox argo update`: Download and update to the latest official release (built-in latest **`2026.10.3`**);
  - `sbbox argo on <token>`: Configure Zero Trust Tunnel Token and register systemd daemon;
  - `sbbox argo off`: Stop and disable Argo Tunnel.
* **Cloudflare WARP Outbound & Streaming Unlock**:
  - `sbbox warp status`: Check WireGuard credentials and assigned Cloudflare IPv6 outbound;
  - `sbbox warp update`: Fetch/rotate fresh official WireGuard credentials to unlock OpenAI/ChatGPT/Claude/Netflix streaming and AI services.

---

## 🚀 Key Highlights

1. **Single-Core Efficiency**: Driven directly by official sing-box core without process chaining, slashing memory footprint by 70%.
2. **MitM Protection (Pinning)**: Automatically extracts certificate SHA-256 (`pinSHA256`) and SPKI public key hashes to prevent traffic spoofing.
3. **Nowhere Split-Path Sidecar**: Routes upstream over TLS/TCP to avoid carrier UDP QoS penalties; routes downstream over QUIC/UDP for line-rate speed.
4. **Kernel Flow Optimization**: Deploys system-wide BBRv3 + FQ and tunes socket buffers to eliminate bufferbloat and dropped connections.
5. **Debian / Ubuntu adaptive (v2.7.70)**: the OS family is derived from `ID` / `ID_LIKE` in `/etc/os-release` (Mint, Kali, Raspberry Pi OS, Armbian, ...); dependencies now include `tar gzip procps util-linux kmod` (often missing on minimal images); `iptables-persistent` is installed separately so its failure no longer fails the whole batch; a persisted kernel channel is no longer overridden by the default on reinstall.
6. **Security audit hardening (v2.7.70)**: API service `secret`; DoH DNS by default; independent TUIC uuid (existing installs keep the old value until `sbbox rotate`); Naive TLS min 1.3; custom AnyTLS `padding_scheme` (AnyTLS keeps TLS 1.2 for client compatibility); systemd sandboxing (`PrivateTmp`, `ProtectKernel*`, `ProtectControlGroups`, `RestrictSUIDSGID`, `LockPersonality`, `OOMScoreAdjust=-500`).
7. **Stability (v2.7.70)**: NIC tuning pins DHCP-provided route MTU 9000 back to 1500 (QUIC sizes packets by it and oversized ones are silently dropped on the public path) and stops dhcpcd from accepting the advertised MTU.
8. **Both Naive nodes use QUIC by default**: links and the sing-box client config carry `quic=1`; for Shadowrocket the subscription converts `naive+https://` to `http3://` too (it used to become `http2://`, which fell back to TCP).
