from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class State:
    in_s: bool = False
    in_d: bool = False
    in_t: bool = False
    in_line: bool = False
    in_block: bool = False
    esc: bool = False


def check(js: str) -> tuple[int, int, int]:
    st = State()
    paren = brace = bracket = 0
    prev = ""

    for i, ch in enumerate(js):
        nxt = js[i + 1] if i + 1 < len(js) else ""

        if st.in_line:
            if ch == "\n":
                st.in_line = False
            continue

        if st.in_block:
            if prev == "*" and ch == "/":
                st.in_block = False
            prev = ch
            continue

        if not (st.in_s or st.in_d or st.in_t):
            if ch == "/" and nxt == "/":
                st.in_line = True
                continue
            if ch == "/" and nxt == "*":
                st.in_block = True
                continue

        if st.in_s:
            if st.esc:
                st.esc = False
            elif ch == "\\":
                st.esc = True
            elif ch == "'":
                st.in_s = False
            continue

        if st.in_d:
            if st.esc:
                st.esc = False
            elif ch == "\\":
                st.esc = True
            elif ch == '"':
                st.in_d = False
            continue

        if st.in_t:
            if st.esc:
                st.esc = False
            elif ch == "\\":
                st.esc = True
            elif ch == "`":
                st.in_t = False
            continue

        if ch == "'":
            st.in_s = True
            continue
        if ch == '"':
            st.in_d = True
            continue
        if ch == "`":
            st.in_t = True
            continue

        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1

        if paren < 0 or brace < 0 or bracket < 0:
            raise ValueError(
                f"Went negative at index {i}: paren={paren} brace={brace} bracket={bracket}"
            )

    return paren, brace, bracket


def main() -> int:
    p = Path(r"addons/smileliving/static/src/js/livechat_product_action.js")
    s = p.read_text(encoding="utf-8")
    paren, brace, bracket = check(s)
    print("Final balance:", {"()": paren, "{}": brace, "[]": bracket})
    return 0 if (paren, brace, bracket) == (0, 0, 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
