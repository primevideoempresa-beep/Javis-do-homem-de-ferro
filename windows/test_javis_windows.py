import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import javis_windows as c

assert c.APPS["vscode"] == "code.exe"
assert c.SITES["youtube"].startswith("https://")
assert c.SEARCH["google"].endswith("q=")
for path, qs in [
    ("/shell", {}),
    ("/open", {"t":["format-c"]}),
    ("/search", {"site":["x"], "q":["abc"]}),
    ("/system", {"a":["rm"]}),
]:
    try:
        c.plan(path, qs)
        raise AssertionError(f"deveria recusar {path}")
    except ValueError:
        pass
print("testes Windows OK")
