#!/usr/bin/env python3
"""
Main script to convert Quantum ESPRESSO output to MCP-friendly JSON.

Supports single or multiple input files with batch processing.

Usage:
    python main.py AgAl-1.out
    python main.py AgAl-1.out CuSn-2.out
    python main.py *.out
    python main.py AgAl-1.out -o output.json
    python main.py *.out -o output_dir/
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from parser import QEParser


def expand_input_files(patterns: list[str]) -> list[Path]:
    """Expand glob patterns and return list of input files."""
    input_files = []
    
    for pattern in patterns:
        # Try glob expansion first
        matches = glob.glob(pattern)
        
        if matches:
            for match in sorted(matches):
                input_files.append(Path(match))
        else:
            # If no glob matches, treat as a single file
            input_files.append(Path(pattern))
    
    return input_files


def process_single_file(
    input_path: Path,
    output_path: Path | None,
    verbose: bool = False,
) -> bool:
    """Process a single QE output file.
    
    Returns:
        True if successful, False otherwise
    """
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return False

    # Determine output filename
    if output_path is None:
        final_output_path = input_path.with_suffix(".json")
    elif output_path.is_dir():
        # If output is a directory, use input filename with .json extension
        final_output_path = output_path / input_path.with_suffix(".json").name
    else:
        final_output_path = output_path

    if verbose:
        print(f"📖 Reading: {input_path}")

    try:
        # Parse QE output
        qe_parser = QEParser()
        data = qe_parser.parse(input_path)

        # Create output directory if needed
        final_output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to JSON (suppress output if not verbose, we'll print our own summary)
        qe_parser.save_json(final_output_path, verbose=verbose)

        if verbose:
            print(f"✅ Successfully parsed: {input_path}")
            print(f"   - Program: {data['program'].get('version', 'N/A')}")
            print(f"   - Atoms: {data['input'].get('nat', 'N/A')}")
            print(f"   - Ionic steps: {len(data['ionic_steps'])}")
            print(f"   - Completed: {data['program'].get('completed', False)}")
        else:
            print(f"✓ {input_path.name} → {final_output_path.name}")

        return True

    except FileNotFoundError as e:
        print(f"❌ Error: File not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: Failed to parse file {input_path}: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Quantum ESPRESSO pw.x output to MCP-friendly JSON (batch processing)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py calculation.out\n"
            "  python main.py AgAl-1.out CuSn-2.out\n"
            "  python main.py *.out\n"
            "  python main.py *.out -o json_output/\n"
            "  python main.py AgAl-1.out -o result.json\n"
        ),
    )

    parser.add_argument(
        "input",
        type=str,
        nargs="+",
        help="Input QE output file(s) or glob pattern (e.g., *.out)",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output JSON file or directory (default: same as input with .json extension)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Expand input patterns
    input_files = expand_input_files(args.input)

    if not input_files:
        print("❌ Error: No input files found")
        return 1

    # Determine output path
    output_path = Path(args.output) if args.output else None

    # Check if output is a directory
    if output_path is not None and output_path.exists() and output_path.is_dir():
        output_dir = output_path
    elif output_path is not None and len(input_files) > 1:
        # Multiple inputs → treat output as a directory
        output_dir = output_path
    else:
        output_dir = None

    if output_dir is not None and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # Process files
    if args.verbose:
        print(f"Processing {len(input_files)} file(s)...\n")

    success_count = 0
    failed_count = 0

    for input_file in input_files:
        # Determine output for this file
        if output_dir is not None:
            file_output = output_dir / input_file.with_suffix(".json").name
        elif len(input_files) == 1 and output_path is not None:
            file_output = output_path
        else:
            file_output = None

        if process_single_file(input_file, file_output, args.verbose):
            success_count += 1
        else:
            failed_count += 1

    # Summary
    if len(input_files) > 1:
        print(f"\n📊 Summary: {success_count}/{len(input_files)} files processed successfully")
        if failed_count > 0:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
