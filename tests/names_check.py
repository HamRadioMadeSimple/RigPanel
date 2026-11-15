"""Structure check for the rigpanel package (no radio, no window needed):  python tests/names_check.py

Every module does `from .earlier import *`, so two mistakes slip through silently:
  1. the same top-level name defined in two modules - the later one wins everywhere after it
     (1.4.1: Voice Scan's s_text replaced the main S-meter's, which then showed S9+110);
  2. a module using a name that is only defined in a LATER module - fine until that code runs
     (1.3: screen_bounds lived after the pop-out waterfall that used it, Compact View broke).
Exits 1 and lists the problems if it finds any."""
import ast
import builtins
import os
import sys

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rigpanel")
ORDER = ["core", "tables", "radios", "worker", "widgets", "waterfall", "freqlist", "minis", "vscan", "extras",
         "builder", "app", "main"]


def top_names(tree):
    out = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(t):
                    if isinstance(x, ast.Name):
                        out.add(x.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name != "*":
                    out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, (ast.If, ast.Try, ast.For)):
            for x in ast.walk(n):
                if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
                    out.add(x.id)
                elif isinstance(x, (ast.FunctionDef, ast.ClassDef)):
                    out.add(x.name)
    return out


def local_names(tree):
    """Every name bound anywhere in the module (args, loop variables, comprehensions, ...)."""
    out = set()
    for x in ast.walk(tree):
        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
            out.add(x.id)
        elif isinstance(x, ast.arg):
            out.add(x.arg)
        elif isinstance(x, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            out.add(x.name)
        elif isinstance(x, ast.ExceptHandler) and x.name:
            out.add(x.name)
        elif isinstance(x, (ast.Import, ast.ImportFrom)):
            for a in x.names:
                out.add((a.asname or a.name).split(".")[0])
    return out


def main():
    mods = [m for m in ORDER if os.path.exists(os.path.join(PKG, m + ".py"))]
    trees = {m: ast.parse(open(os.path.join(PKG, m + ".py"), encoding="utf-8").read()) for m in mods}
    defined = {m: top_names(t) for m, t in trees.items()}
    problems = []
    seen = {}
    for m in mods:
        for name in sorted(defined[m]):
            if name.startswith("__"):
                continue
            if name in seen and name not in ("tk", "ttk", "tkfont", "re", "os", "sys", "time", "json", "math",
                                              "queue", "socket", "threading", "platform", "xmlrpc", "http"):
                problems.append(f"'{name}' is defined in {seen[name]}.py AND {m}.py (the later one wins)")
            seen.setdefault(name, m)
    for i, m in enumerate(mods):
        earlier = set().union(*(defined[x] for x in mods[:i + 1]))
        later = {}
        for x in mods[i + 1:]:
            for name in defined[x]:
                later.setdefault(name, x)
        mine = local_names(trees[m]) | earlier | set(dir(builtins))
        for x in ast.walk(trees[m]):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id not in mine and x.id in later:
                problems.append(f"{m}.py line {x.lineno} uses '{x.id}', which is only defined later in {later[x.id]}.py")
    if problems:
        print("PROBLEMS:")
        for p in sorted(set(problems)):
            print("  " + p)
        sys.exit(1)
    print(f"names check: OK ({len(mods)} modules, {sum(len(v) for v in defined.values())} top-level names)")


if __name__ == "__main__":
    main()
