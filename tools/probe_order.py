"""Report the .text layout order of the nine user functions from a link map.

Original binary order (source order): init_level1, init_level2, init_level0,
handle_input, move_and_push, move_player, draw_map, count_remaining_boxes, main
starting at 0x4117F0.
"""
import re
import sys

NAMES = [
    "init_level1", "init_level2", "init_level0", "handle_input",
    "move_and_push", "move_player", "draw_map",
    "count_remaining_boxes", "main",
]
ORIG_FIRST = 0x4117F0

PATTERN = re.compile(
    r"^\s+[0-9A-Fa-f]{4}:([0-9A-Fa-f]{8})\s+_(\S+)\s+([0-9A-Fa-f]{8})\s"
)


def main(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = PATTERN.match(line)
        if m and m.group(2) in NAMES:
            rows.append((int(m.group(3), 16), m.group(2)))
    if not rows:
        print("NO_USER_SYMBOLS")
        return 1
    rows.sort()
    for va, name in rows:
        print(f"{va:#010x}  {name}")
    order = [name for _, name in rows]
    delta = rows[0][0] - ORIG_FIRST
    print(f"ORDER_SOURCE={'YES' if order == NAMES else 'NO'}")
    print(f"FIRST_USER_FN={rows[0][0]:#010x} "
          f"(original {ORIG_FIRST:#010x}, delta {delta:+#x})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
