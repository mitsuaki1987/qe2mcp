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
import re
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


def load_cell_transform_matrix(input_path: Path) -> list[list[float]] | None:
    """Load the unit-cell → supercell transform matrix for a QE output file.

    Reads the 'cell_transform_matrix' file in the same directory as the
    input file. The file contains 9 comma-separated values (row-major 3x3).

    Returns:
        3x3 matrix as a nested list, or None if the file is not found
        or cannot be parsed.
    """
    matrix_file = input_path.resolve().parent / "cell_transform_matrix"
    if not matrix_file.exists():
        return None

    try:
        values = [
            float(v) if "." in v or "e" in v.lower() else int(v)
            for v in matrix_file.read_text().replace("\n", ",").split(",")
            if v.strip()
        ]
    except ValueError:
        return None

    if len(values) != 9:
        return None

    return [values[0:3], values[3:6], values[6:9]]


def load_atom_energies(input_path: Path) -> dict[str, float] | None:
    """Load isolated-atom energies (Ry) for a QE output file.

    Searches for 'atom_energy_Ry.dat' in the input file's directory and
    its parent directories. The file contains 'Symbol,energy' lines.

    Returns:
        Mapping of element symbol to isolated-atom energy in Ry,
        or None if the file is not found or cannot be parsed.
    """
    directory = input_path.resolve().parent
    for candidate_dir in [directory, *directory.parents]:
        energy_file = candidate_dir / "atom_energy_Ry.dat"
        if energy_file.exists():
            break
    else:
        return None

    energies: dict[str, float] = {}
    try:
        for line in energy_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            symbol, value = line.split(",")
            energies[symbol.strip()] = float(value)
    except ValueError:
        return None

    return energies if energies else None


def attach_formation_energies(
    data: dict,
    atom_energies: dict[str, float],
) -> bool:
    """Attach formation energy alongside every 'energy_ry' in the data.

    Definition: (total energy) - (sum of isolated-atom energies),
    also reported per atom. Each ionic step with 'energy_ry' gets a
    'formation_energy' entry, and the final step's value is also stored
    at the top level as data['formation_energy'].

    Returns:
        True if at least one formation energy was attached, False if the
        required data (sites, an atom energy, or any energy) is missing.
    """
    sites = data.get("sites") or {}
    if not sites:
        return False

    symbols = list(sites.values())
    if any(s not in atom_energies for s in symbols):
        return False

    isolated_sum = sum(atom_energies[s] for s in symbols)
    nat = len(symbols)

    attached = False
    for step in data.get("ionic_steps") or []:
        if "energy_ry" not in step:
            continue
        formation_total = step["energy_ry"] - isolated_sum
        step["formation_energy"] = {
            "total_ry": formation_total,
            "per_atom_ry": formation_total / nat,
        }
        attached = True

    if attached:
        data["formation_energy"] = data["ionic_steps"][-1]["formation_energy"]

    return attached


# Checked in order; the first match wins. In a pw.x vc-relax run these
# outcomes are mutually exclusive, so ordering only matters as a safeguard.
_TERMINATION_PATTERNS = [
    ("bfgs_converged", re.compile(r"bfgs converged in\s+\d+ scf cycles and\s+\d+ bfgs steps")),
    ("bfgs_failed", re.compile(r"bfgs failed after\s+\d+ scf cycles")),
    ("max_steps_reached", re.compile(r"The maximum number of steps has been reached")),
    ("scf_not_converged", re.compile(r"convergence NOT achieved after\s+\d+ iterations: stopping")),
    ("error", re.compile(r"Error in routine .+ \(\d+\)")),
]


def determine_termination_status(input_path: Path) -> dict:
    """Classify how a QE run terminated by scanning its output file.

    Returns:
        Dict with:
        - 'status': one of 'bfgs_converged', 'bfgs_failed',
          'max_steps_reached', 'scf_not_converged', 'error',
          'incomplete' (no marker and no JOB DONE, e.g. killed mid-run),
          or 'unknown' (JOB DONE present but no recognized marker).
        - 'message': the matched line from the output, or None.
        - 'job_done': whether the run printed 'JOB DONE.'.
    """
    text = input_path.read_text(errors="replace")
    job_done = "JOB DONE" in text

    for status, pattern in _TERMINATION_PATTERNS:
        match = pattern.search(text)
        if match:
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            return {
                "status": status,
                "message": text[line_start:line_end].strip(),
                "job_done": job_done,
            }

    return {
        "status": "unknown" if job_done else "incomplete",
        "message": None,
        "job_done": job_done,
    }


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

        # Classify how the run terminated (BFGS/SCF convergence, error, ...)
        data["termination"] = determine_termination_status(input_path)

        # Attach unit-cell → supercell transform matrix if available
        matrix = load_cell_transform_matrix(input_path)
        if matrix is not None:
            data["cell_transform_matrix"] = matrix
        elif verbose:
            print(f"⚠️  cell_transform_matrix not found for {input_path}")

        # Attach formation energies relative to isolated atoms if available
        atom_energies = load_atom_energies(input_path)
        attached = (
            attach_formation_energies(data, atom_energies)
            if atom_energies is not None
            else False
        )
        if not attached and verbose:
            print(f"⚠️  formation energy not computed for {input_path}")

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
