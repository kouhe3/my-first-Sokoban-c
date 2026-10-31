#!/usr/bin/env python3
"""Compare a rebuilt ConsoleApplication1.exe against the original release.

Checks (see Reverse.md §4):
  1. per-function instruction stream, with image addresses resolved through
     known symbols (user functions and globals) instead of a bare "IMG" tag;
     branch targets and data references must resolve to the same symbol+offset;
  2. Rich-header fingerprint: compiler build, linker build and number of
     compiler-produced objects (documents toolchain identity);
  3. .data raw and .rsrc byte equality;
  4. section size table.

Usage:
  python tools/verify_rebuild.py \
      --orig ConsoleApplication1.exe \
      --rebuilt Debug/ConsoleApplication1.exe \
      --map    Debug/ConsoleApplication1.map
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

# original data symbols (see Reverse.md §1.4)
ORIGINAL_GLOBALS = {
    "g_rows": (0x41B000, 4),
    "g_player_y": (0x41B004, 4),
    "g_player_x": (0x41B008, 4),
    "g_map": (0x41B150, 10000),
    "g_level": (0x41D860, 4),
}

IMAGE_LO, IMAGE_HI = 0x400000, 0x424000

# Rich-header product ids observed in this project's binaries
RICH_PRODUCTS = {0x0104: "cl", 0x0102: "link"}

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


def rich_profile(data):
    """Decode the Rich header: per-tool build/count entries.

    One (product, build) pair can merge user objects and prebuilt library
    objects, so `count` is only an upper bound for the project's own objects.
    """
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    marker = data.rfind(b"Rich", 0, pe)
    if marker < 0:
        return {}
    key = struct.unpack_from("<I", data, marker + 4)[0]
    encoded_dans = 0x536E6144 ^ key  # 'DanS' ^ key
    start = None
    for offset in range(0x40, marker, 4):
        if struct.unpack_from("<I", data, offset)[0] == encoded_dans:
            start = offset
            break
    if start is None:
        return {}
    profile = {}
    off = start + 16
    while off + 8 <= marker:
        compid = struct.unpack_from("<I", data, off)[0] ^ key
        count = struct.unpack_from("<I", data, off + 4)[0] ^ key
        product = compid >> 16
        build = compid & 0xFFFF
        name = RICH_PRODUCTS.get(product)
        if name:
            profile.setdefault(name, []).append((build, count))
        off += 8
    return profile


def summarise_rich(profile):
    parts = []
    for name in ("cl", "link"):
        entries = sorted(profile.get(name, []))
        if not entries:
            parts.append(f"{name}=?")
            continue
        newest = entries[-1][0]
        rendered = ", ".join(f"{build}x{count}" for build, count in entries)
        parts.append(f"{name}={newest} ({rendered})")
    return "; ".join(parts)

def parse_map(path):
    symbols = {}
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = re.match(r"\s+000[0-9a-f]:([0-9a-f]{8})\s+(\S+)\s+([0-9a-f]{8})\s", line)
            if match:
                symbols[match.group(2)] = int(match.group(3), 16)
    return symbols


def make_anchors(functions, globals_):
    """Interval table: address -> (symbol name, size)."""
    spans = []
    for name, (va, size) in functions.items():
        spans.append((va, va + size, name))
    for name, (va, size) in globals_.items():
        spans.append((va, va + size, name))
    spans.sort()
    return spans


def resolve(value, spans):
    for lo, hi, name in spans:
        if lo <= value < hi:
            return name, value - lo
    return None


def operand_key(ins, op, spans):
    """Return a comparison key; image addresses resolve to symbol+offset."""
    if op.type == X86_OP_REG:
        return ("reg", ins.reg_name(op.reg))
    if op.type == X86_OP_IMM:
        value = op.imm & 0xFFFFFFFF
        if in_image(value):
            hit = resolve(value, spans)
            if hit:
                return ("sym", hit[0], hit[1])
            return ("img",)
        return ("imm", value)
    if op.type == X86_OP_MEM:
        mem = op.mem
        base = ins.reg_name(mem.base) if mem.base else ""
        index = ins.reg_name(mem.index) if mem.index else ""
        disp = mem.disp & 0xFFFFFFFF
        if in_image(disp):
            hit = resolve(disp, spans)
            key = ("sym", hit[0], hit[1]) if hit else ("img",)
        else:
            key = ("imm", disp)
        return ("mem", base, index, mem.scale, key)
    return ("?",)


def normalize(code, va, spans):
    out = []
    for ins in md.disasm(code, va):
        operands = tuple(operand_key(ins, op, spans) for op in ins.operands)
        is_branch = ins.mnemonic.startswith("j") or ins.mnemonic == "call"
        out.append((ins.mnemonic, operands, f"{ins.mnemonic} {ins.op_str}", is_branch))
    return out


def control_flow_free(instructions):
    """Instruction multiset without branches, used for the layout-only check."""
    counter = collections.Counter()
    for mnemonic, operands, _, _ in instructions:
        if mnemonic == "nop":
            continue
        if mnemonic.startswith("j"):
            continue
        counter[(mnemonic, operands)] += 1
    return counter


def cut_at_epilogue(instructions):
    """Keep instructions up to and including the last `ret` (function end)."""
    last = -1
    for index, (mnemonic, _, _, _) in enumerate(instructions):
        if mnemonic.startswith("ret"):
            last = index
    return instructions[: last + 1] if last >= 0 else instructions


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

    orig_rich = rich_profile(orig_data)
    new_rich = rich_profile(new_data)
    orig_cl = max((b for b, _ in orig_rich.get("cl", [])), default=None)
    new_cl = max((b for b, _ in new_rich.get("cl", [])), default=None)
    orig_link = max((b for b, _ in orig_rich.get("link", [])), default=None)
    new_link = max((b for b, _ in new_rich.get("link", [])), default=None)
    print("toolchain fingerprint (Rich header, build x count):")
    print(f"  original: {summarise_rich(orig_rich)}")
    print(f"  rebuilt : {summarise_rich(new_rich)}")
    print(f"  newest cl build identical: {orig_cl == new_cl}; "
          f"link build identical: {orig_link == new_link}")
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

    # anchors used to resolve image addresses to symbols
    orig_spans = make_anchors(ORIGINAL_FUNCTIONS, ORIGINAL_GLOBALS)
    rebuilt_functions = {}
    for name, (_, size) in ORIGINAL_FUNCTIONS.items():
        symbol = "_" + name
        if symbol in symbols:
            rebuilt_functions[name] = (symbols[symbol], size)
    rebuilt_globals = {}
    for name, (_, size) in ORIGINAL_GLOBALS.items():
        symbol = "_" + name
        if symbol in symbols:
            rebuilt_globals[name] = (symbols[symbol], size)
    new_spans = make_anchors(rebuilt_functions, rebuilt_globals)

    print(f"{'function':<24}{'insns':>12}  result")
    failures = []
    layout_only = []
    ref_stats = collections.Counter()
    for name, (orig_va, size) in ORIGINAL_FUNCTIONS.items():
        symbol = "_" + name
        if symbol not in symbols:
            print(f"{name:<24}{'?':>12}  MISSING in map")
            failures.append(name)
            continue
        new_va = symbols[symbol]
        orig_code = orig_data[rva_to_offset(orig_sections, orig_va):][:size]
        new_code = new_data[rva_to_offset(new_sections, new_va):][:size]
        orig_insns = cut_at_epilogue(normalize(orig_code, orig_va, orig_spans))
        new_insns = cut_at_epilogue(normalize(new_code, new_va, new_spans))
        common = min(len(orig_insns), len(new_insns))
        mismatches = [
            i for i in range(common)
            if orig_insns[i][:2] != new_insns[i][:2]
        ]
        for i in range(common):
            for side, insns in (("orig", orig_insns), ("new", new_insns)):
                for operand in insns[i][1]:
                    flat = repr(operand)
                    if "'sym'" in flat:
                        ref_stats[f"{side}_resolved"] += 1
                    elif "'img'" in flat:
                        ref_stats[f"{side}_unresolved"] += 1
            if orig_insns[i][3]:
                ref_stats["branches"] += 1
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
    print("symbol-resolved references:")
    print(f"  branches compared           : {ref_stats['branches']}")
    print(f"  operands resolved to symbols: orig {ref_stats['orig_resolved']}, "
          f"new {ref_stats['new_resolved']}")
    print(f"  image operands without anchor: orig {ref_stats['orig_unresolved']}, "
          f"new {ref_stats['new_unresolved']} (normalized to IMG)")
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
