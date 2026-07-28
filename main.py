#!/usr/bin/env python3
"""
Main script to convert Quantum ESPRESSO output to MCP-friendly JSON.

Usage:
    python main.py AgAl-1.out
    python main.py AgAl-1.out -o output.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from parser import QEParser


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Quantum ESPRESSO pw.x output to MCP-friendly JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py calculation.out\n"
            "  python main.py AgAl-1.out -o output.json\n"
        ),
    )

    parser.add_argument(
        "input",
        type=str,
        help="Input QE output file (e.g., AgAl-1.out)",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output JSON file (default: input_name.json)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    # Check if input file exists
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return 1

    # Determine output filename
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".json")

    if args.verbose:
        print(f"📖 Reading: {input_path}")

    try:
        # Parse QE output
        qe_parser = QEParser()
        data = qe_parser.parse(input_path)

        # Save to JSON
        qe_parser.save_json(output_path)

        if args.verbose:
            print(f"✅ Successfully parsed: {input_path}")
            print(f"   - Program: {data['program'].get('version', 'N/A')}")
            print(f"   - Atoms: {data['input'].get('nat', 'N/A')}")
            print(f"   - Ionic steps: {len(data['ionic_steps'])}")
            print(f"   - Completed: {data['program'].get('completed', False)}")

        return 0

    except FileNotFoundError as e:
        print(f"❌ Error: File not found: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: Failed to parse file: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
