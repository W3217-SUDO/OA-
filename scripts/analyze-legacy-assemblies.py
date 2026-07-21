#!/usr/bin/env python3
"""Extract type, method, and enum metadata from legacy .NET assemblies.

The script never loads or executes the target assemblies.  It parses PE/.NET
metadata with dnfile and writes CSV files suitable for the OA migration audit.
"""

from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

import dnfile


def text(value: object) -> str:
    return "" if value is None else str(value)


def description_from_blob(blob: bytes) -> str:
    """Decode the fixed string used by DescriptionAttribute."""
    if len(blob) < 3 or blob[:2] != b"\x01\x00":
        return ""
    first = blob[2]
    if first == 0xFF:
        return ""
    if first & 0x80 == 0:
        size, offset = first, 3
    elif first & 0xC0 == 0x80 and len(blob) >= 4:
        size, offset = ((first & 0x3F) << 8) | blob[3], 4
    elif len(blob) >= 6:
        size = ((first & 0x1F) << 24) | (blob[3] << 16) | (blob[4] << 8) | blob[5]
        offset = 6
    else:
        return ""
    try:
        return blob[offset : offset + size].decode("utf-8")
    except UnicodeDecodeError:
        return ""


def constant_value(row: object) -> object:
    raw = bytes(row.Value.value)
    kind = int(row.Type)
    formats = {2: "?", 3: "H", 4: "b", 5: "B", 6: "h", 7: "H", 8: "i", 9: "I", 10: "q", 11: "Q", 12: "f", 13: "d"}
    if kind in formats:
        return struct.unpack("<" + formats[kind], raw[: struct.calcsize(formats[kind])])[0]
    if kind == 14:
        return raw.decode("utf-16-le", errors="replace")
    return raw.hex()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("assembly_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    type_rows: list[dict[str, object]] = []
    method_rows: list[dict[str, object]] = []
    enum_rows: list[dict[str, object]] = []

    for assembly in sorted(args.assembly_dir.glob("Dchien.Legal*.dll")):
        pe = dnfile.dnPE(str(assembly))
        if not pe.net or not pe.net.mdtables.TypeDef:
            continue

        constants = {}
        if pe.net.mdtables.Constant:
            for item in pe.net.mdtables.Constant.rows:
                parent = getattr(item.Parent, "row", None)
                if parent is not None:
                    constants[id(parent)] = constant_value(item)

        descriptions: dict[int, str] = {}
        if pe.net.mdtables.CustomAttribute:
            for item in pe.net.mdtables.CustomAttribute.rows:
                parent = getattr(item.Parent, "row", None)
                ctor = getattr(item.Type, "row", None)
                owner = getattr(getattr(ctor, "Class", None), "row", None)
                if parent is None or text(getattr(owner, "TypeName", "")) != "DescriptionAttribute":
                    continue
                value = description_from_blob(bytes(item.Value.value))
                if value:
                    descriptions[id(parent)] = value

        for typedef in pe.net.mdtables.TypeDef.rows:
            namespace = text(typedef.TypeNamespace)
            name = text(typedef.TypeName)
            if name == "<Module>":
                continue
            full_name = f"{namespace}.{name}" if namespace else name
            base = getattr(getattr(typedef, "Extends", None), "row", None)
            base_name = text(getattr(base, "TypeName", ""))
            type_rows.append(
                {"assembly": assembly.name, "namespace": namespace, "type": name, "full_name": full_name, "base_type": base_name}
            )
            for method_index in typedef.MethodList:
                method = method_index.row
                method_rows.append(
                    {"assembly": assembly.name, "type": full_name, "method": text(method.Name), "rva": int(method.Rva or 0)}
                )
            if base_name != "Enum":
                continue
            for field_index in typedef.FieldList:
                field = field_index.row
                field_name = text(field.Name)
                if field_name == "value__" or id(field) not in constants:
                    continue
                enum_rows.append(
                    {
                        "assembly": assembly.name,
                        "enum": full_name,
                        "name": field_name,
                        "value": constants[id(field)],
                        "description": descriptions.get(id(field), ""),
                    }
                )

    outputs = {
        "assembly-types.csv": (type_rows, ["assembly", "namespace", "type", "full_name", "base_type"]),
        "assembly-methods.csv": (method_rows, ["assembly", "type", "method", "rva"]),
        "enum-values.csv": (enum_rows, ["assembly", "enum", "name", "value", "description"]),
    }
    for name, (rows, fields) in outputs.items():
        with (args.output_dir / name).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    print(f"types={len(type_rows)} methods={len(method_rows)} enum_values={len(enum_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
