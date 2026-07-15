#!/usr/bin/env python3
"""
install_hooks.py — enable (or disable) automatic conversion on file upload.

It merges two hooks into the project's .claude/settings.json:

  * SessionStart     -> run setup.sh (idempotent) then scan+convert once.
  * UserPromptSubmit -> scan+convert any file added mid-session.

Both call scripts/hook.py, which only converts NEW/CHANGED files and prints a
short note (never file contents), so the cost per prompt is tiny.

Merging is idempotent and non-destructive: existing hooks and settings are
preserved; our entries are tagged with a marker so re-running does nothing and
--uninstall removes exactly them.

Usage:
    python install_hooks.py [--settings PATH] [--prompt-hook/--no-prompt-hook]
    python install_hooks.py --uninstall
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MARKER = "markitdown/scripts/hook.py"          # identifies our command entries
SETUP = "markitdown/scripts/setup.sh"

SESSION_CMD = (
    "bash .claude/skills/markitdown/scripts/setup.sh >/dev/null 2>&1; "
    "python3 .claude/skills/markitdown/scripts/hook.py"
)
PROMPT_CMD = "python3 .claude/skills/markitdown/scripts/hook.py"


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"error: {path} is not valid JSON ({exc}); refusing to overwrite.",
                  file=sys.stderr)
            raise SystemExit(1)
    return {}


def _entry_has_marker(entry: dict) -> bool:
    for h in entry.get("hooks", []):
        if MARKER in h.get("command", "") or SETUP in h.get("command", ""):
            return True
    return False


def _add_event(settings: dict, event: str, command: str) -> bool:
    hooks = settings.setdefault("hooks", {})
    arr = hooks.setdefault(event, [])
    for entry in arr:
        if _entry_has_marker(entry):
            # Already installed — refresh the command in case it changed.
            for h in entry.get("hooks", []):
                if MARKER in h.get("command", "") or SETUP in h.get("command", ""):
                    h["command"] = command
            return False
    arr.append({"hooks": [{"type": "command", "command": command}]})
    return True


def _remove_event(settings: dict, event: str) -> bool:
    hooks = settings.get("hooks", {})
    arr = hooks.get(event)
    if not arr:
        return False
    before = len(arr)
    hooks[event] = [e for e in arr if not _entry_has_marker(e)]
    if not hooks[event]:
        del hooks[event]
    if hooks == {}:
        settings.pop("hooks", None)
    return len(hooks.get(event, [])) != before


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", default=".claude/settings.json",
                    help="path to settings.json (default: .claude/settings.json)")
    ap.add_argument("--uninstall", action="store_true", help="remove the hooks")
    ap.add_argument("--no-prompt-hook", dest="prompt_hook", action="store_false",
                    help="only install the SessionStart hook (no per-prompt scan)")
    ap.set_defaults(prompt_hook=True)
    args = ap.parse_args(argv)

    path = Path(args.settings)
    settings = _load(path)

    if args.uninstall:
        changed = _remove_event(settings, "SessionStart")
        changed |= _remove_event(settings, "UserPromptSubmit")
        msg = "removed markitdown hooks" if changed else "no markitdown hooks found"
    else:
        changed = _add_event(settings, "SessionStart", SESSION_CMD)
        if args.prompt_hook:
            changed |= _add_event(settings, "UserPromptSubmit", PROMPT_CMD)
        msg = "installed markitdown auto-conversion hooks"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print(f"{msg} -> {path}")
    print("Restart the session (or start a new one) for SessionStart to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
