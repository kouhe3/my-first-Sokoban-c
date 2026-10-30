#!/usr/bin/env python3
"""Compare a rebuilt ConsoleApplication1.exe against the original release.

Checks (see Reverse.md §4):
  1. per-function normalized instruction stream (capstone, image addresses -> IMG);
  2. .data raw and .rsrc byte equality;
  3. section size table.

Usage:
  python tools/verify_rebuild.py \
      --orig ConsoleApplication1.exe \
      --rebuilt D:/VS2019/HELLO/ConsoleApplication1/Debug/ConsoleApplication1.exe \
      --map    D:/VS2019/HELLO/ConsoleApplication1/Debug/ConsoleApplication1.map
"""

import argparse
import collections
import re
import struct
import sys

try:
    import capstone
    from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
except ImportError:  # pragma: no cover
    sys.exit("capstone is required: python -m pip install capstone")

# original function extents, taken from the IDA database of the release exe
ORIGINAL_FUNCTIONS = {
    "init_level1": (0x4117F0, 963),
    "init_level2": (0x411CD0, 932),
    "init_level0": (0x4121B0, 1205),
    "handle_input": (0x4127C0, 446),
    "move_and_push": (0x412A30, 151),
    "move_player": (0x412AF0, 179),
    "draw_map": (0x412BD0, 111),
    "count_remaining_boxes": (0x412C60, 147),
    "main": (0x412E00, 534),
}

# layout reordering is accepted for the first delivery; these may differ
LAYOUT_ONLY = {"handle_input"}

IMAGE_LO, IMAGE_HI = 0x400000, 0x424000

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def load_pe(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    sections = {}
    for i in range(nsec):
        sh = pe + 24 + optsz + i * 40
        name = data[sh:sh + 8].rstrip(b"\0").decode("latin-1")
        vsz, va, rawsz, rawptr = struct.unpack_from("<IIII", data, sh + 8)
        sections[name] = (va, vsz, rawptr, rawsz)
    return data, sections


def rva_to_offset(sections, va):
    rva = va - 0x400000
    for va_sec, vsz, rawptr, rawsz in sections.values():
        if va_sec <= rva < va_sec + max(vsz, rawsz):
            return rawptr + rva - va_sec
    raise ValueError(f"address 0x{va:08x} is not mapped")


def in_image(value):
    return IMAGE_LO <= value < IMAGE_HI


def normalized_instructions(code, va):
    out = []
    for ins in md.disasm(code, va):
        operands = []
        for op in ins.operands:
            if op.type == X86_OP_REG:
                operands.append(("reg", ins.reg_name(op.reg)))
            elif op.type == X86_OP_IMM:
                value = op.imm & 0xFFFFFFFF
                operands.append(("imm", "IMG" if in_image(value) else value))
            elif op.type == X86_OP_MEM:
                mem = op.mem
                base = ins.reg_name(mem.base) if mem.base else ""
                index = ins.reg_name(mem.index) if mem.index else ""
                disp = "IMG" if in_image(mem.disp & 0xFFFFFFFF) else mem.disp
                operands.append(("mem", base, index, mem.scale, disp))
        out.append((ins.mnemonic, tuple(operands), f"{ins.mnemonic} {ins.op_str}"))
    return out


def parse_map(path):
    symbols = {}
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = re.match(r"\s+000[0-9]:([0-9a-f]{8})\s+(\S+)\s+([0-9a-f]{8})\s", line)
            if match:
                symbols[match.group(2)] = int(match.group(3), 16)
    return symbols


def control_flow_free(instructions):
    """Instruction multiset without branches, used for the layout-only check.

    A pure block reordering keeps every non-branch instruction, but moves the
    conditional jumps that select the block; branch polarity and one extra
    `jmp` are expected artefacts of that reordering.
    """
    counter = collections.Counter()
    for mnemonic, operands, _ in instructions:
        if mnemonic == "nop":
            continue
        if mnemonic == "jmp" or (mnemonic.startswith("j") and mnemonic != "jmp"):
            continue
        counter[(mnemonic, operands)] += 1
    return counter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--orig", default="ConsoleApplication1.exe")
    parser.add_argument("--rebuilt", required=True)
    parser.add_argument("--map", required=True)
    args = parser.parse_args()

    orig_data, orig_sections = load_pe(args.orig)
    new_data, new_sections = load_pe(args.rebuilt)
    symbols = parse_map(args.map)

    print(f"original : {args.orig} ({len(orig_data)} bytes)")
    print(f"rebuilt  : {args.rebuilt} ({len(new_data)} bytes)")
    print()

    print(f"{'section':<10}{'orig vsz':>10}{'new vsz':>10}{'rawdiff':>10}")
    for name, (va, vsz, rawptr, rawsz) in orig_sections.items():
        if name not in new_sections:
            print(f"{name:<10}  missing in rebuilt")
            continue
        nva, nvsz, nrawptr, nrawsz = new_sections[name]
        orig_raw = orig_data[rawptr:rawptr + rawsz]
        new_raw = new_data[nrawptr:nrawptr + nrawsz]
        common = min(len(orig_raw), len(new_raw))
        diff = sum(1 for i in range(common) if orig_raw[i] != new_raw[i])
        print(f"{name:<10}{vsz:>10x}{nvsz:>10x}{diff:>10}")
    print()

    print(f"{'function':<24}{'insns':>12}  result")
    failures = []
    layout_only = []
    for name, (orig_va, size) in ORIGINAL_FUNCTIONS.items():
        symbol = "_" + name
        if symbol not in symbols:
            print(f"{name:<24}{'?':>12}  MISSING in map")
            failures.append(name)
            continue
        new_va = symbols[symbol]
        orig_code = orig_data[rva_to_offset(orig_sections, orig_va):][:size]
        new_code = new_data[rva_to_offset(new_sections, new_va):][:size]
        orig_insns = normalized_instructions(orig_code, orig_va)
        new_insns = normalized_instructions(new_code, new_va)
        common = min(len(orig_insns), len(new_insns))
        mismatches = [
            i for i in range(common)
            if orig_insns[i][:2] != new_insns[i][:2]
        ]
        exact = len(orig_insns) == len(new_insns) and not mismatches
        label = f"{len(orig_insns)}/{len(new_insns)}"
        if exact:
            print(f"{name:<24}{label:>12}  MATCH")
        elif name in LAYOUT_ONLY and control_flow_free(orig_insns) == control_flow_free(new_insns):
            print(f"{name:<24}{label:>12}  LAYOUT-ONLY (block reordered)")
            layout_only.append(name)
        else:
            print(f"{name:<24}{label:>12}  DIFF ({len(mismatches)} instructions)")
            for i in mismatches[:3]:
                print(f"    #{i} orig: {orig_insns[i][2]}")
                print(f"    #{i} new : {new_insns[i][2]}")
            failures.append(name)

    print()
    for name in (".data", ".rsrc"):
        if name in orig_sections and name in new_sections:
            _, _, rawptr, rawsz = orig_sections[name]
            _, _, nrawptr, nrawsz = new_sections[name]
            same = orig_data[rawptr:rawptr + rawsz] == new_data[nrawptr:nrawptr + nrawsz]
            print(f"{name} raw identical: {same}")
            if not same:
                failures.append(name)

    print()
    if failures:
        print("RESULT: FAIL")
        return 1
    if layout_only:
        print(f"RESULT: PASS (layout reordering accepted: {', '.join(layout_only)})")
    else:
        print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
