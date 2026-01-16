from __future__ import annotations

from pathlib import Path


def main() -> int:
    p = Path(r"addons/smileliving/static/src/js/livechat_product_action.js")
    s = p.read_text(encoding="utf-8")

    balance = 0
    in_s = in_d = in_t = False
    in_line = in_block = False
    esc = False
    prev = ""

    for i, ch in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else ""

        if in_line:
            if ch == "\n":
                in_line = False
            continue

        if in_block:
            if prev == "*" and ch == "/":
                in_block = False
            prev = ch
            continue

        if not (in_s or in_d or in_t):
            if ch == "/" and nxt == "/":
                in_line = True
                continue
            if ch == "/" and nxt == "*":
                in_block = True
                continue

        if in_s:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_s = False
            continue

        if in_d:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_d = False
            continue

        if in_t:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "`":
                in_t = False
            continue

        if ch == "'":
            in_s = True
            continue
        if ch == '"':
            in_d = True
            continue
        if ch == "`":
            in_t = True
            continue

        if ch == "{":
            balance += 1
        elif ch == "}":
            balance -= 1
            if balance < 0:
                print("Went negative at index", i)
                return 2

    print("Final balance:", balance)
    return 0 if balance == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
