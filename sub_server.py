#!/usr/bin/env python3
import sys, os, re, base64, json, ssl, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 50934
WEB_DIR = sys.argv[2] if len(sys.argv) > 2 else "/root/sbbox/websub"
SB_HOME = os.path.dirname(WEB_DIR.rstrip("/"))
# 可选 HTTPS：argv[3]=证书链 argv[4]=私钥；缺省或加载失败则退回明文 HTTP
TLS_CERT = sys.argv[3] if len(sys.argv) > 3 else ""
TLS_KEY = sys.argv[4] if len(sys.argv) > 4 else ""

# 订阅端口防爆破频次限制 (内存限流器)
_failed_ip_attempts = {}
_ip_lock = threading.Lock()
MAX_FAILURES_WINDOW = 60
MAX_FAILURES_ALLOWED = 10

# 订阅端口监听 0.0.0.0，请求路径必须白名单校验后才能拼进 WEB_DIR，
# 否则 "/../../../etc/passwd" 会变成公网任意文件读取。
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
WEB_DIR_REAL = os.path.realpath(WEB_DIR)

def resolve_token_file(token_path):
    if not SAFE_TOKEN_RE.match(token_path) or token_path.startswith(".") or token_path in ("index.html", "sub_qr.png"):
        return None
    candidate = os.path.realpath(os.path.join(WEB_DIR_REAL, token_path))
    if candidate != WEB_DIR_REAL and not candidate.startswith(WEB_DIR_REAL + os.sep):
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate

def sanitize_clash_yaml(yaml_text):
    if "anytls" not in yaml_text:
        return yaml_text

    lines = yaml_text.splitlines()
    out_lines = []
    in_proxies = False
    current_proxy_lines = []
    current_proxy_name = None
    dropped_names = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        if re.match(r"^[a-zA-Z0-9_-]+:", line):
            if current_proxy_lines:
                is_anytls = any(re.search(r"^\s*type:\s*['\"]?anytls['\"]?", l) for l in current_proxy_lines)
                if is_anytls:
                    if current_proxy_name:
                        dropped_names.add(current_proxy_name)
                else:
                    out_lines.extend(current_proxy_lines)
                current_proxy_lines = []
                current_proxy_name = None
            in_proxies = line.startswith("proxies:")
            out_lines.append(line)
            i += 1
            continue

        if in_proxies:
            m = re.match(r"^\s*-\s*name:\s*(.+)$", line)
            if m:
                if current_proxy_lines:
                    is_anytls = any(re.search(r"^\s*type:\s*['\"]?anytls['\"]?", l) for l in current_proxy_lines)
                    if is_anytls:
                        if current_proxy_name:
                            dropped_names.add(current_proxy_name)
                    else:
                        out_lines.extend(current_proxy_lines)
                    current_proxy_lines = []
                current_proxy_name = m.group(1).strip().strip("'\"")
                current_proxy_lines = [line]
            elif current_proxy_lines:
                current_proxy_lines.append(line)
            else:
                out_lines.append(line)
            i += 1
            continue

        out_lines.append(line)
        i += 1

    if current_proxy_lines:
        is_anytls = any(re.search(r"^\s*type:\s*['\"]?anytls['\"]?", l) for l in current_proxy_lines)
        if is_anytls:
            if current_proxy_name:
                dropped_names.add(current_proxy_name)
        else:
            out_lines.extend(current_proxy_lines)

    if dropped_names:
        final_lines = []
        for l in out_lines:
            m = re.match(r"^\s*-\s*(.+)$", l)
            if m:
                item_name = m.group(1).strip().strip("'\"")
                if item_name in dropped_names:
                    continue
            final_lines.append(l)
        return "\n".join(final_lines) + ("\n" if yaml_text.endswith("\n") else "")
    return yaml_text

class _NullWriter:
    def write(self, b):
        return len(b)
    def flush(self):
        pass

class SubHandler(BaseHTTPRequestHandler):
    # 空闲/慢速连接超时，避免占满服务线程
    timeout = 10
    # 隐私：不落访问日志，也不把客户端 IP / UA 写进 journald；
    # 真正的处理器错误仍写 stderr（不带客户端地址），便于排错
    def version_string(self):
        return "nginx"

    def log_request(self, code="-", size="-"):
        pass

    def send_error(self, code, message=None, explain=None):
        # 不返回 Python 默认错误页（带 "Error response" 特征），只给状态码
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        # 去掉控制字符，并遮住请求行里像订阅 token 的长路径段，再写 stderr
        msg = re.sub(r"[^\x20-\x7e]", "?", format % args)
        msg = re.sub(r"/[A-Za-z0-9._-]{16,}", "/<redacted>", msg)
        sys.stderr.write("sbbox-sub: " + msg[:200] + "\n")

    def end_headers(self):
        BaseHTTPRequestHandler.end_headers(self)
        # HEAD：头部已发出，其后的响应体丢弃
        if self.command == "HEAD":
            self._real_wfile = self.wfile
            self.wfile = _NullWriter()

    def do_HEAD(self):
        try:
            self.do_GET()
        finally:
            if hasattr(self, "_real_wfile"):
                self.wfile = self._real_wfile

    def do_GET(self):
        client_ip = self.client_address[0]
        now = time.time()
        with _ip_lock:
            attempts = [t for t in _failed_ip_attempts.get(client_ip, []) if now - t < MAX_FAILURES_WINDOW]
            if len(attempts) >= MAX_FAILURES_ALLOWED:
                self.send_error(429)
                return
            _failed_ip_attempts[client_ip] = attempts

        raw_path = self.path.split("#")[0]
        query = raw_path.split("?", 1)[1] if "?" in raw_path else ""
        token_path = unquote(raw_path.split("?")[0]).lstrip("/")
        if token_path in ("", "index.html"):
            # 根路径与未知路径一致返回 404，不暴露服务身份
            self.send_response(404)
            self.end_headers()
            return
        # QR 内含带 token 的订阅 URL，必须携带有效 token 才可取：/<token>/qr
        if token_path.endswith("/qr") and resolve_token_file(token_path[:-3]):
            qr_file = os.path.join(WEB_DIR_REAL, "sub_qr.png")
            if not os.path.isfile(qr_file):
                qr_file = os.path.join(SB_HOME, "sub_qr.png")
            if os.path.isfile(qr_file):
                with open(qr_file, "rb") as f: content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        force_format = ""
        for suffix in ("/clash", "/singbox", "/sb", "/json", "/b64", "/v2rayn", "/v2ray", "/shadowrocket", "/nowhere"):
            if token_path.endswith(suffix):
                force_format = suffix.lstrip("/")
                token_path = token_path[:-len(suffix)]
                break

        token_file = resolve_token_file(token_path)
        if token_file is None:
            with _ip_lock:
                _failed_ip_attempts.setdefault(client_ip, []).append(time.time())
            self.send_response(404)
            self.end_headers()
            return

        ua = self.headers.get("User-Agent", "").lower()
        q_lower = query.lower()

        is_b64 = force_format in ("b64", "v2rayn", "v2ray") or "format=b64" in q_lower or "b64=1" in q_lower or "v2rayn=1" in q_lower or "v2ray=1" in q_lower
        is_clash = not is_b64 and (force_format == "clash" or "clash=1" in q_lower or "format=clash" in q_lower or any(k in ua for k in ("clash", "mihomo", "stash", "meta", "subconverter", "verge", "flclash")))
        is_singbox = not is_b64 and (force_format in ("singbox", "sb", "json") or "singbox=1" in q_lower or "sb=1" in q_lower or "format=singbox" in q_lower or "format=json" in q_lower or "sing-box" in ua or "sbox" in ua or "nekoray" in ua)

        if is_clash:
            clash_file = os.path.join(SB_HOME, "clmi.yaml")
            if os.path.isfile(clash_file):
                with open(clash_file, "r", encoding="utf-8", errors="ignore") as f:
                    content_str = f.read()
                # AnyTLS 进入全部订阅（含原版 Clash）。原版 Clash 不认识 anytls 类型，可能拒绝加载整份配置；
                # 不再做 sanitize_clash_yaml 清洗。需要剔除时由客户端自行删除该节点。
                content = content_str.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/yaml; charset=utf-8")
                self.send_header("profile-update-interval", "24")
                self.send_header("content-disposition", 'attachment; filename="sbbox_clash.yaml"')
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if is_singbox:
            sb_file = os.path.join(SB_HOME, "sbox_client.json")
            if os.path.isfile(sb_file):
                with open(sb_file, "rb") as f: content = f.read()
                # TUN 按客户端平台自适应：?os=windows|linux|macos|android|ios，缺省时看 User-Agent；识别不出则原样下发
                plat = ""
                m = re.search(r"(?:^|&)os=([a-z]+)", q_lower)
                hint = m.group(1) if m else ua
                for key, name in (("android", "android"), ("sfa", "android"), ("iphone", "ios"), ("ios", "ios"), ("sfi", "ios"),
                                  ("darwin", "macos"), ("macos", "macos"), ("sfm", "macos"), ("mac", "macos"),
                                  ("windows", "windows"), ("win", "windows"), ("linux", "linux")):
                    if key in hint:
                        plat = name
                        break
                try:
                    cfg = json.loads(content)
                    for ib in cfg.get("inbounds", []):
                        if ib.get("type") != "tun":
                            continue
                        # 规范修正 TUN MTU 为 1500，杜绝 9000 巨型帧公网 PMTU 黑洞丢包
                        ib["mtu"] = 1500
                        if plat:
                            ib["stack"] = "mixed"
                            if plat == "windows":
                                ib["strict_route"] = True
                            elif plat == "linux":
                                ib["strict_route"] = True
                                ib["auto_redirect"] = True
                            else:
                                # macOS 不支持 strict_route；Android / iOS 由系统 VPN 接管路由，不需要
                                ib["strict_route"] = False
                                ib.pop("auto_redirect", None)
                    content = json.dumps(cfg, indent=4, ensure_ascii=False).encode("utf-8")
                except Exception:
                    pass
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("content-disposition", 'attachment; filename="sbox_client.json"')
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        raw_links = []
        nodes_txt = os.path.join(SB_HOME, "nodes.txt")
        if os.path.isfile(nodes_txt):
            with open(nodes_txt, "r", encoding="utf-8", errors="ignore") as f:
                raw_links = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        else:
            with open(token_file, "rb") as f: b64 = f.read().strip()
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                raw_links = [line.strip() for line in decoded.splitlines() if line.strip() and not line.strip().startswith("#")]
            except Exception: pass

        def ensure_node_security(l):
            # 1. 确保 tuic:// 与 anytls:// 保留 security=tls 强校验参数（避免 v2rayN 缺少 TLS 导致 sing-box core 闪退）
            if l.startswith("anytls://"):
                if "security=" not in l:
                    if "?" in l:
                        l = l.replace("?", "?security=tls&", 1)
                    elif "#" in l:
                        p = l.split("#", 1)
                        l = f"{p[0]}?security=tls#{p[1]}"
                    else:
                        l = l + "?security=tls"
                if "udp=" not in l:
                    l = l.replace("?", "?udp=1&", 1) if "?" in l else l + "?udp=1"
                if "allowInsecure=" not in l:
                    l = l.replace("?", "?allowInsecure=0&allow_insecure=0&", 1) if "?" in l else l + "?allowInsecure=0&allow_insecure=0"
            # 2. 确保 tuic:// 显式声明 version=5（小火箭解析规范强依赖，避免误判为 TUIC v4 握手失败）
            if l.startswith("tuic://"):
                if "version=" not in l:
                    if "?" in l:
                        l = l.replace("?", "?version=5&", 1)
                    elif "#" in l:
                        p = l.split("#", 1)
                        l = f"{p[0]}?version=5#{p[1]}"
                    else:
                        l = l + "?version=5"
            return l

        is_nowhere = force_format == "nowhere" or "format=nowhere" in q_lower or "nowhere=1" in q_lower
        if is_nowhere:
            raw_links = [l for l in raw_links if l.startswith("nowhere://")]

        selected_links = [ensure_node_security(l) for l in raw_links]

        # Shadowrocket（小火箭）客户端适配：
        # - 小火箭仅支持 http3:// 与 http2:// 格式的 Naive 链接（按 UA 现场转换）
        # - 小火箭 2.2.65+ 原生支持 anytls:// 协议（默认保留下发，旧版本可通过 noanytls=1 剔除）
        # - TUIC 节点已通过 ensure_node_security 保证 version=5 声明
        # - 保留全部协议链接（含 nowhere://），方便支持该协议的客户端或插件完整加载
        is_sr = "shadowrocket" in ua or force_format == "shadowrocket" or "shadowrocket=1" in q_lower or "format=shadowrocket" in q_lower
        if is_sr:
            if "noanytls=1" in q_lower:
                selected_links = [l for l in selected_links if not l.startswith("anytls://")]
            # 两条 Naive 默认都开 QUIC：小火箭没有 quic=1 开关，只能靠 http3:// 前缀走 QUIC，所以 naive+https:// 也转成 http3://
            selected_links = [("http3://" + l[len("naive+quic://"):]) if l.startswith("naive+quic://")
                              else ("http3://" + l[len("naive+https://"):]) if l.startswith("naive+https://")
                              else l for l in selected_links]

        if not selected_links:
            with open(token_file, "rb") as f: content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        body = base64.b64encode("\n".join(selected_links).encode("utf-8"))
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Subscription-Userinfo", "upload=0; download=0; total=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class TLSServer(ThreadingHTTPServer):
    """握手放在各自的工作线程里（带超时），证书续期后按 mtime 自动重载。"""
    _ctx = None
    _stamp = None

    def _context(self):
        stamp = (os.stat(TLS_CERT).st_mtime, os.stat(TLS_KEY).st_mtime)
        if self._ctx is None or stamp != self._stamp:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(TLS_CERT, TLS_KEY)

            # 对抗主动探测与域名嗅探：未知 SNI 或直接 IP 探测直接拒绝握手，不泄露证书主体
            valid_domains = set()
            ym_file = os.path.join(SB_HOME, "ym")
            if os.path.isfile(ym_file):
                try:
                    with open(ym_file, "r", encoding="utf-8") as yf:
                        d = yf.read().strip().lower()
                        if d: valid_domains.add(d)
                except Exception: pass
            try:
                cert_dict = ssl._ssl._test_decode_cert(TLS_CERT)
                for k, v in cert_dict.get("subjectAltName", []):
                    if k == "DNS": valid_domains.add(v.lower())
                for sub in cert_dict.get("subject", []):
                    for k, v in sub:
                        if k == "commonName": valid_domains.add(v.lower())
            except Exception: pass

            def _sni_callback(sock, req_sni, cb_ctx):
                if not req_sni:
                    return ssl.ALERT_DESCRIPTION_UNRECOGNIZED_NAME
                if valid_domains and req_sni.lower() not in valid_domains:
                    return ssl.ALERT_DESCRIPTION_UNRECOGNIZED_NAME
                return None

            ctx.sni_callback = _sni_callback
            self._ctx, self._stamp = ctx, stamp
        return self._ctx

    def process_request_thread(self, request, client_address):
        try:
            request.settimeout(10)
            request = self._context().wrap_socket(request, server_side=True)
        except Exception:
            self.shutdown_request(request)
            return
        ThreadingHTTPServer.process_request_thread(self, request, client_address)

def run():
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.request_queue_size = 128
    if TLS_CERT and TLS_KEY:
        TLSServer._context(TLSServer)  # 启动时先校验一次，证书不可用就直接报错退出
        httpd = TLSServer(("0.0.0.0", PORT), SubHandler)
    else:
        httpd = ThreadingHTTPServer(("0.0.0.0", PORT), SubHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
