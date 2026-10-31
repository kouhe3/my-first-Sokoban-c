#!/usr/bin/env python3
"""Split ConsoleApplication1.c into one translation unit per function.

Diagnostic tool for the byte-layout investigation: cl emits per-function
COMDATs sorted by name, so a single-file build cannot reproduce the original
function order.  Linking one file per function in source order does reproduce
it (see Reverse.md §5), at the cost of larger .rdata / .msvcjmc sections.

Usage:
  python tools/split_multi_tu.py --src ConsoleApplication1.c --out .build/multi

The generated files keep GBK/cp936 encoding so string literals stay byte
identical.
"""

import argparse
import os
import re

FUNCTIONS = [
    "init_level1",
    "init_level2",
    "init_level0",
    "handle_input",
    "move_and_push",
    "move_player",
    "draw_map",
    "count_remaining_boxes",
    "main",
]

GLOBALS = """int g_rows = 1;
int g_player_y = 1;
int g_player_x = 1;
char g_map[100][ROW_STRIDE];
int g_level;
"""

HEADER = """#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <string.h>

#define ROW_STRIDE 100

extern int g_rows;
extern int g_player_y;
extern int g_player_x;
extern char g_map[100][ROW_STRIDE];
extern int g_level;

void init_level1(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x);
void init_level2(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x);
void init_level0(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x);
void handle_input(char map[][ROW_STRIDE], int *player_y, int *player_x);
void move_and_push(char map[][ROW_STRIDE], int old_y, int new_y, int old_x, int new_x);
void move_player(char map[][ROW_STRIDE], int *player_y, int new_y, int *player_x, int new_x);
void draw_map(char map[][ROW_STRIDE], int rows);
int count_remaining_boxes(char map[][ROW_STRIDE]);
"""


def extract(text, name):
    pattern = re.compile(rf"^(void|int) {name}\([^;]*?\)\s*$", re.M)
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"definition of {name} not found")
    start = match.start()
    brace = text.index("{", start)
    depth = 0
    index = brace
    while True:
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                break
        index += 1
    return text[start:index + 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="ConsoleApplication1.c")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    text = open(args.src, "rb").read().decode("gbk")
    os.makedirs(args.out, exist_ok=True)
    open(os.path.join(args.out, "sokoban.h"), "wb").write(HEADER.encode("gbk"))

    for name in FUNCTIONS:
        body = extract(text, name)
        chunks = ['#include "sokoban.h"\n\n']
        if name == "main":
            chunks.append(GLOBALS + "\n")
        chunks.append(body + "\n")
        path = os.path.join(args.out, name + ".c")
        open(path, "wb").write("".join(chunks).encode("gbk"))

    print(f"wrote {len(FUNCTIONS)} translation units to {args.out}")


if __name__ == "__main__":
    main()
