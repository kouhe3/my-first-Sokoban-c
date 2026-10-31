#!/usr/bin/env python3
"""Report which MSVC toolset built a PE file (see Reverse.md §1.6).

Two independent fingerprints are printed:
  1. OptionalHeader linker version (MajorLinkerVersion.MinorLinkerVersion, e.g. 14.29);
  2. Rich header build numbers, which are the v142 toolset build (30133 vs 30159).

A Rich header carries one record per object/library that went into the link, so
several builds appear at once; they are grouped and listed instead of being
collapsed into a single "the" version.

Usage:
  python tools/msvc_version.py ConsoleApplication1.exe Debug/ConsoleApplication1.exe
"""

import collections
import struct
import sys

# build -> label, only builds verified on this machine / in Reverse.md
KNOWN_BUILDS = {
    30133: "cl/link 19.29.30133 (VS2019 16.11.0)",
    30159: "cl/link 19.29.30159 (local v142)",
    30034: "19.29.30034 (VS2019 16.10 era; original project + libs)",
}

DANS_XOR = 0x536E6144  # "DanS"


def read_pe(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise SystemExit(f"{path}: not a PE file")
    opt = pe + 24
    major, minor = data[opt + 2], data[opt + 3]
    return data, major, minor


def parse_rich(data):
    """Return [(product_id, build, count)] from the Rich header, {} if absent."""
    rich = data.find(b"Rich")
    while rich != -1:
        key = struct.unpack_from("<I", data, rich + 4)[0]
        dans = data.rfind(struct.pack("<I", DANS_XOR ^ key), 0, rich)
        if dans != -1:
            entries = []
            offset = dans + 16  # DanS + 3 padding dwords, all XORed
            while offset + 8 <= rich:
                compid_raw, count_raw = struct.unpack_from("<II", data, offset)
                compid, count = compid_raw ^ key, count_raw ^ key
                entries.append((compid >> 16, compid & 0xFFFF, count))
                offset += 8
            if entries:
                return entries
        rich = data.find(b"Rich", rich + 1)
    return []


def report(path):
    data, major, minor = read_pe(path)
    entries = parse_rich(data)
    print(f"{path}")
    print(f"  linker version      : {major}.{minor}")
    if not entries:
        print("  Rich header         : absent")
        return
    # build 0 entries are the filler slots ("0x00010000 xN"), not a toolset
    real = [entry for entry in entries if entry[1]]
    if not real:
        print("  Rich header         : only filler entries")
        return
    grouped = collections.defaultdict(lambda: [0, set()])
    for product, build, count in real:
        grouped[build][0] += count
        grouped[build][1].add(product)
    print("  rich builds         :")
    for build, (count, products) in sorted(grouped.items(), reverse=True):
        ids = " ".join(f"0x{product:04x}" for product in sorted(products))
        label = KNOWN_BUILDS.get(build, "unknown build")
        print(f"    {build:5d}  x{count:<3d} {ids}  {label}")


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    for path in argv:
        report(path)
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
