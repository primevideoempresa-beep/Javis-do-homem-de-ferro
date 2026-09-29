#!/usr/bin/env python3
"""Javis Windows Bridge + painel local.

Executa apenas ações explicitamente permitidas. Não existe rota /shell nem execução
arbitrária de CMD/PowerShell.

Uso:
    py windows/javis_windows.py
"""
import json
import os
import platform
import shutil
import subprocess
import threading
import time
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

HOST = "127.0.0.1"
PORT = 8766
# Troque pelo IP do seu Javis (aparece no OLED por 3s ao ligar). So paginas dessa origem
# podem pedir acoes pelo navegador; chamadas locais (ex.: o painel) nao mandam Origin e
# continuam liberadas.
JAVIS_ORIGIN = "http://192.168.15.201"
MAX_TEXT = 1000
MAX_HTML = 200_000
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "pagina" / "index.html"
version = 0

APPS = {
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "vscode": "code.exe",
    "arduino": "arduino-ide.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "whatsapp": "WhatsApp.exe",
}
SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "drive": "https://drive.google.com",
    "calendar": "https://calendar.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "whatsapp_web": "https://web.whatsapp.com",
}
SEARCH = {
    "google": "https://www.google.com/search?q=",
    "youtube": "https://www.youtube.com/results?search_query=",
    "bing": "https://www.bing.com/search?q=",
}

EMPTY = "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Javis</title></head><body></body></html>"


def json_reply(handler, code, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    origin = handler.headers.get("Origin")
    handler.send_header("Access-Control-Allow-Origin", origin if origin == JAVIS_ORIGIN else JAVIS_ORIGIN)
    handler.send_header("Access-Control-Allow-Private-Network", "true")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(data)


def origin_ok(handler):
    # Chamadas locais (painel, scripts de teste) nao mandam Origin: continuam liberadas.
    # Chamadas de navegador (a pagina do Javis) precisam bater com JAVIS_ORIGIN.
    origin = handler.headers.get("Origin")
    return origin is None or origin == JAVIS_ORIGIN


def page_write(html):
    global version
    if not isinstance(html, str) or not html.strip():
        raise ValueError("HTML vazio")
    if len(html) > MAX_HTML:
        raise ValueError("HTML grande demais")
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(html, encoding="utf-8")
    version += 1


def page_read():
    return PAGE.read_text(encoding="utf-8") if PAGE.exists() else EMPTY


def resolve_app(name):
    exe = APPS.get(name)
    if not exe:
        raise ValueError("aplicativo não permitido")
    found = shutil.which(exe)
    if found:
        return found
    # Locais comuns do Windows para programas instalados pelo usuário.
    candidates = []
    pf = os.environ.get("ProgramFiles", r"C:\\Program Files")
    pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    if name == "vscode":
        candidates += [
            os.path.join(local, "Programs", "Microsoft VS Code", "Code.exe"),
            os.path.join(pf, "Microsoft VS Code", "Code.exe"),
        ]
    elif name == "arduino":
        candidates += [
            os.path.join(local, "Programs", "Arduino IDE", "Arduino IDE.exe"),
            os.path.join(pf, "Arduino IDE", "Arduino IDE.exe"),
            os.path.join(pfx86, "Arduino IDE", "Arduino IDE.exe"),
        ]
    elif name == "chrome":
        candidates += [
            os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pfx86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
        ]
    elif name == "edge":
        candidates += [
            os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pfx86, "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError(f"Não encontrei o aplicativo '{name}'. Instale-o ou adicione-o ao PATH.")

def run_app(name):
    exe = resolve_app(name)
    subprocess.Popen([exe], shell=False)
    return f"app {name}"


def open_site(name):
    url = SITES.get(name)
    if not url:
        raise ValueError("site não permitido")
    webbrowser.open(url)
    return f"site {name}"


def search(site, query):
    if site not in SEARCH:
        raise ValueError("buscador não permitido")
    query = str(query).strip()
    if not query or len(query) > 200:
        raise ValueError("pesquisa vazia ou longa demais")
    webbrowser.open(SEARCH[site] + quote_plus(query))
    return f"pesquisa {site}: {query}"


def system_action(action):
    commands = {
        "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
        "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "restart": ["shutdown.exe", "/r", "/t", "10"],
        "shutdown": ["shutdown.exe", "/s", "/t", "10"],
        "cancel_shutdown": ["shutdown.exe", "/a"],
    }
    if action not in commands:
        raise ValueError("ação de sistema não permitida")
    subprocess.Popen(commands[action], shell=False)
    return action


def volume_action(action):
    # Controle via PowerShell somente com script interno fixo, sem entrada do usuário.
    scripts = {
        "up": "[console]::beep(880,40)",
        "down": "[console]::beep(440,40)",
        "mute": "(New-Object -ComObject WScript.Shell).SendKeys([char]173)",
    }
    if action not in scripts:
        raise ValueError("volume inválido")
    subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", scripts[action]],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return f"volume {action}"


def system_info():
    total, used, free = shutil.disk_usage(Path.home().anchor or "C:\\")
    return {
        "os": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu": os.cpu_count(),
        "disk_free_gb": round(free / 1024**3, 1),
        "disk_total_gb": round(total / 1024**3, 1),
    }


def safe_path(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("caminho vazio")
    p = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
    home = Path.home().resolve()
    # Ações de arquivo ficam restritas à pasta do usuário.
    if home not in p.parents and p != home:
        raise ValueError("por segurança, o caminho precisa ficar dentro da pasta do usuário")
    return p


def file_action(action, path, target=None):
    p = safe_path(path)
    if action == "open":
        os.startfile(str(p))
    elif action == "create_folder":
        p.mkdir(parents=True, exist_ok=True)
    elif action == "delete":
        raise ValueError("exclusão não é automática nesta versão; use a interface do Windows")
    elif action == "copy":
        t = safe_path(target or "")
        if p.is_dir():
            shutil.copytree(p, t, dirs_exist_ok=True)
        else:
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, t)
    elif action == "move":
        t = safe_path(target or "")
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(t))
    else:
        raise ValueError("ação de arquivo não permitida")
    return f"arquivo {action}: {p}"


# WhatsApp: abre o aplicativo e coloca texto no clipboard. O envio continua manual.
def whatsapp_draft(text):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("mensagem inválida")
    run_app("whatsapp")
    # clipboard via PowerShell, conteúdo é passado por stdin para evitar shell injection.
    ps = "Set-Clipboard -Value ([Console]::In.ReadToEnd())"
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                    input=text, text=True, check=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True, "draft_id": secrets.token_hex(4), "mensagem": text}


def plan(path, qs):
    if path == "/open":
        target = qs.get("t", [""])[0]
        if target in APPS:
            return run_app(target)
        if target in SITES:
            return open_site(target)
        raise ValueError("alvo desconhecido")
    if path == "/search":
        return search(qs.get("site", [""])[0], qs.get("q", [""])[0])
    if path == "/system":
        return system_action(qs.get("a", [""])[0])
    if path == "/volume":
        return volume_action(qs.get("a", [""])[0])
    if path == "/file":
        return file_action(qs.get("a", [""])[0], qs.get("path", [""])[0], qs.get("target", [""])[0])
    if path == "/page/open":
        where = qs.get("where", [""])[0]
        if not PAGE.exists(): page_write(EMPTY)
        if where == "browser":
            webbrowser.open(f"file:///{PAGE.as_posix()}")
            return "página no navegador"
        if where == "vscode":
            subprocess.Popen([resolve_app("vscode"), str(PAGE)], shell=False)
            return "página no VS Code"
        raise ValueError("destino inválido")
    raise ValueError("rota desconhecida")


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        origin = self.headers.get("Origin")
        self.send_header("Access-Control-Allow-Origin", origin if origin == JAVIS_ORIGIN else JAVIS_ORIGIN)
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if not origin_ok(self):
            return json_reply(self, 403, {"ok": False, "erro": "origem nao autorizada"})
        if u.path == "/ping":
            return json_reply(self, 200, {"ok": True, "platform": "windows", "port": PORT})
        if u.path == "/info":
            return json_reply(self, 200, {"ok": True, "info": system_info()})
        if u.path == "/commands":
            return json_reply(self, 200, {"apps": sorted(APPS), "sites": sorted(SITES), "search": sorted(SEARCH),
                                          "system": ["lock", "sleep", "restart", "shutdown", "cancel_shutdown"],
                                          "volume": ["up", "down", "mute"],
                                          "files": ["open", "create_folder", "copy", "move"]})
        if u.path == "/page/read":
            return json_reply(self, 200, {"html": page_read()})
        if u.path == "/pagina":
            data = page_read().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        try:
            what = plan(u.path, parse_qs(u.query))
            return json_reply(self, 200, {"ok": True, "executado": what})
        except (ValueError, OSError, subprocess.SubprocessError) as e:
            return json_reply(self, 400, {"ok": False, "erro": str(e)})

    def do_POST(self):
        path = urlparse(self.path).path
        if not origin_ok(self):
            return json_reply(self, 403, {"ok": False, "erro": "origem nao autorizada"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_HTML * 2:
                return json_reply(self, 413, {"erro": "conteúdo grande demais"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if path == "/page/write":
                page_write(body.get("html"))
                return json_reply(self, 200, {"ok": True})
            if path == "/wa/draft":
                return json_reply(self, 200, whatsapp_draft(body.get("text")))
            if path == "/clipboard":
                text = body.get("text", "")
                if not isinstance(text, str) or len(text) > MAX_TEXT:
                    raise ValueError("texto inválido")
                ps = "Set-Clipboard -Value ([Console]::In.ReadToEnd())"
                subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                               input=text, text=True, check=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return json_reply(self, 200, {"ok": True})
            return json_reply(self, 404, {"erro": "rota desconhecida"})
        except (ValueError, json.JSONDecodeError, OSError, subprocess.SubprocessError) as e:
            return json_reply(self, 400, {"ok": False, "erro": str(e)})

    def log_message(self, *_):
        pass


def run_server():
    print(f"Javis Windows Bridge: http://{HOST}:{PORT}")
    print("Comandos livres de CMD/PowerShell: BLOQUEADOS")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    run_server()
