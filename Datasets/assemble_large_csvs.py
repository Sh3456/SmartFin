"""Rebuild the large CSVs from their repository-friendly text parts.

Run from the SmartFin repository root:
    python Datasets/assemble_large_csvs.py

Only Python's standard library is used. Parts are joined as bytes to preserve
the original CSV bytes, row order, delimiters, and line endings.
"""
from pathlib import Path
import sys

DATA_DIR = Path(__file__).resolve().parent
PARTS_DIR = DATA_DIR / "parts"
PARTS = {
    "devices.csv": [
        "devices_01.part", "devices_02.part", "devices_03.part",
        "devices_04.part", "devices_05.part", "devices_06.part",
    ],
    "transactions.csv": [
        "transactions_01.part", "transactions_02.part", "transactions_03.part",
        "transactions_04.part", "transactions_05.part", "transactions_06.part",
        "transactions_07.part", "transactions_08.part",
    ],
}


def assemble(output_name: str, part_names: list[str]) -> None:
    output_path = DATA_DIR / output_name
    missing = [name for name in part_names if not (PARTS_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing parts for {output_name}: {', '.join(missing)}")
    with output_path.open("wb") as output:
        for name in part_names:
            with (PARTS_DIR / name).open("rb") as part:
                while True:
                    block = part.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
    print(f"Created {output_path} ({output_path.stat().st_size:,} bytes)")


def main() -> int:
    try:
        for output_name, part_names in PARTS.items():
            assemble(output_name, part_names)
    except OSError as exc:
        print(f"Dataset assembly failed: {exc}", file=sys.stderr)
        return 1
    print("Done. Import the reconstructed CSV files into MySQL Workbench in the order documented in mysql/02_import_data.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
