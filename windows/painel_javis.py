import json
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8766"

def get(path, params=None):
    url = BASE + path + (("?" + urlencode(params)) if params else "")
    with urlopen(url, timeout=4) as r:
        return json.loads(r.read().decode())

def post(path, data):
    req = Request(BASE + path, data=json.dumps(data).encode(), headers={"Content-Type":"application/json"})
    with urlopen(req, timeout=4) as r:
        return json.loads(r.read().decode())

def action(fn):
    def run():
        try: fn()
        except Exception as e: messagebox.showerror("Javis", str(e))
    threading.Thread(target=run, daemon=True).start()

root = tk.Tk()
root.title("Javis AI — Windows")
root.geometry("760x560")
root.minsize(700, 500)

header = tk.Frame(root, padx=16, pady=12)
header.pack(fill="x")
tk.Label(header, text="🤖 JAVIS AI", font=("Segoe UI", 22, "bold")).pack(side="left")
status = tk.Label(header, text="● verificando", font=("Segoe UI", 11))
status.pack(side="right")

nb = tk.Frame(root, padx=16)
nb.pack(fill="both", expand=True)


def btn(text, fn, row, col):
    b = tk.Button(nb, text=text, command=lambda: action(fn)(), height=2, font=("Segoe UI", 10))
    b.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

for c in range(3): nb.grid_columnconfigure(c, weight=1)
for r in range(7): nb.grid_rowconfigure(r, weight=1)

btn("🌐 Google", lambda: get("/open", {"t":"google"}), 0, 0)
btn("▶ YouTube", lambda: get("/open", {"t":"youtube"}), 0, 1)
btn("💬 WhatsApp", lambda: get("/open", {"t":"whatsapp"}), 0, 2)
btn("💻 VS Code", lambda: get("/open", {"t":"vscode"}), 1, 0)
btn("🔧 Arduino", lambda: get("/open", {"t":"arduino"}), 1, 1)
btn("📁 Explorer", lambda: get("/open", {"t":"explorer"}), 1, 2)
btn("🔒 Bloquear PC", lambda: get("/system", {"a":"lock"}), 2, 0)
btn("😴 Suspender", lambda: get("/system", {"a":"sleep"}), 2, 1)
btn("🔄 Reiniciar (10s)", lambda: (messagebox.showwarning("Confirmação", "Reiniciar o Windows em 10 segundos?"), get("/system", {"a":"restart"})), 2, 2)

query = tk.StringVar()
tk.Entry(nb, textvariable=query, font=("Segoe UI", 12)).grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
btn("🔎 Pesquisar", lambda: get("/search", {"site":"google", "q":query.get()}), 3, 2)

text = tk.StringVar()
tk.Entry(nb, textvariable=text, font=("Segoe UI", 12)).grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
btn("📋 Copiar texto", lambda: post("/clipboard", {"text":text.get()}), 4, 2)

btn("📄 Criar página", lambda: post("/page/write", {"html":"<!doctype html><html><body><h1>Javis</h1><p>Página criada pelo Javis Windows.</p></body></html>"}), 5, 0)
btn("🌎 Abrir página", lambda: get("/page/open", {"where":"browser"}), 5, 1)
btn("🖥 Informações do PC", lambda: messagebox.showinfo("PC", json.dumps(get("/info")["info"], ensure_ascii=False, indent=2)), 5, 2)


def check():
    try:
        r = get("/ping")
        status.config(text="● ONLINE")
    except Exception:
        status.config(text="● Bridge offline")
    root.after(2500, check)

check()
root.mainloop()
