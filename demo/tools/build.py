"""Inline demo/src/*.js into templates, emitting self-contained pages in dist/.

Artifact pages are served under a CSP that blocks all external hosts, so every
script must be inline. Run: python tools/build.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, TEMPLATES, DIST = ROOT / "src", ROOT / "templates", ROOT / "dist"
MARKER = re.compile(r"<!--INLINE:([a-zA-Z0-9_.,\-]+)-->")


def inline(match):
    parts = []
    for name in match.group(1).split(","):
        path = SRC / name.strip()
        if not path.exists():
            sys.exit(f"ERROR: {path} not found (referenced in an INLINE marker)")
        # Each module is wrapped in an IIFE. Every src/ module ends with the same
        # dual-export footer, `const api = {...}`, and top-level const in a classic
        # script goes into the *shared* global lexical scope — so a second module
        # declaring `api` throws "Identifier 'api' has already been declared" and
        # silently fails to run. Node hides this because it scopes each module for
        # you. The IIFE restores that scoping; the modules still publish themselves
        # through window.Demo, which is how the pages consume them.
        parts.append(
            "<script>\n(function () {\n"
            f"{path.read_text(encoding='utf-8')}"
            "\n})();\n</script>"
        )
    return "\n".join(parts)


def main():
    DIST.mkdir(exist_ok=True)
    built = 0
    for template in sorted(TEMPLATES.glob("*.html")):
        html = MARKER.sub(inline, template.read_text(encoding="utf-8"))
        if "<!--INLINE:" in html:
            sys.exit(f"ERROR: unresolved INLINE marker in {template.name}")
        (DIST / template.name).write_text(html, encoding="utf-8")
        print(f"built dist/{template.name}")
        built += 1
    if built == 0:
        sys.exit("ERROR: no templates found")


if __name__ == "__main__":
    main()
