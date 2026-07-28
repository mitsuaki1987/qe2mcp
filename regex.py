"""
Regular expressions used by qe2mcp.

Currently supports Quantum ESPRESSO pw.x (v7.x) vc-relax output.

All regexes are compiled.
"""

from __future__ import annotations

import re

FLOAT = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[DEde][+-]?\d+)?"

# ------------------------------------------------------------
# Program
# ------------------------------------------------------------

PROGRAM_VERSION = re.compile(
    r"Program\s+PWSCF\s+v\.?\s*([0-9.]+)"
)

GIT_REVISION = re.compile(
    r"git revision\s+([^\n]+)"
)

CALCULATION = re.compile(
    r"calculation\s*=\s*'([^']+)'"
)

# ------------------------------------------------------------
# System
# ------------------------------------------------------------

NAT = re.compile(
    r"number of atoms/cell\s*=\s*(\d+)"
)

NTYP = re.compile(
    r"number of atomic types\s*=\s*(\d+)"
)

NBND = re.compile(
    r"number of Kohn-Sham states\s*=\s*(\d+)"
)

NELEC = re.compile(
    r"number of electrons\s*=\s*(" + FLOAT + ")"
)

ECUTWFC = re.compile(
    r"kinetic-energy cutoff\s*=\s*(" + FLOAT + r")\s+Ry"
)

ECUTRHO = re.compile(
    r"charge density cutoff\s*=\s*(" + FLOAT + r")\s+Ry"
)

XC = re.compile(
    r"Exchange-correlation\s*=\s*(.+)"
)

# ------------------------------------------------------------
# FFT
# ------------------------------------------------------------

FFT_GRID = re.compile(
    r"Dense\s+grid:\s*\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)"
)

SMOOTH_GRID = re.compile(
    r"Smooth\s+grid:\s*\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)"
)

# ------------------------------------------------------------
# Lattice
# ------------------------------------------------------------

LATTICE_PARAMETER = re.compile(
    r"lattice parameter \(alat\)\s*=\s*(" + FLOAT + r")"
)

UNIT_CELL_VOLUME = re.compile(
    r"unit-cell volume\s*=\s*(" + FLOAT + r")"
)

# ------------------------------------------------------------
# Energies
# ------------------------------------------------------------

TOTAL_ENERGY = re.compile(
    r"!\s+total energy\s+=\s*(" + FLOAT + r")\s+Ry"
)

ESTIMATED_ACCURACY = re.compile(
    r"estimated scf accuracy\s*<\s*(" + FLOAT + r")\s+Ry"
)

FERMI_ENERGY = re.compile(
    r"the Fermi energy is\s*(" + FLOAT + r")\s+ev",
    re.IGNORECASE,
)

# ------------------------------------------------------------
# Magnetization
# ------------------------------------------------------------

TOTAL_MAGNETIZATION = re.compile(
    r"total magnetization\s*=\s*(" + FLOAT + r")"
)

ABS_MAGNETIZATION = re.compile(
    r"absolute magnetization\s*=\s*(" + FLOAT + r")"
)

ATOMIC_MAGNETIZATION = re.compile(
    r"atom:\s*(\d+)\s+charge:\s*("
    + FLOAT
    + r")\s+magn:\s*("
    + FLOAT
    + r")"
)

# ------------------------------------------------------------
# Forces
# ------------------------------------------------------------

TOTAL_FORCE = re.compile(
    r"Total force\s*=\s*(" + FLOAT + r")"
)

FORCE_LINE = re.compile(
    r"atom\s+(\d+)\s+type\s+\d+\s+force\s*=\s*"
    r"\(\s*("
    + FLOAT
    + r")\s+("
    + FLOAT
    + r")\s+("
    + FLOAT
    + r")\s*\)"
)

# ------------------------------------------------------------
# Stress
# ------------------------------------------------------------

TOTAL_STRESS = re.compile(
    r"total\s+stress.*?P=\s*("
    + FLOAT
    + r")"
)

# ------------------------------------------------------------
# Timing
# ------------------------------------------------------------

PWSCF_CPU = re.compile(
    r"PWSCF\s*:\s*.*CPU\s*(.*WALL)"
)

JOB_DONE = re.compile(
    r"JOB DONE"
)

# ------------------------------------------------------------
# Blocks
# ------------------------------------------------------------

CELL_PARAMETERS = re.compile(
    r"CELL_PARAMETERS\s*\(([^)]*)\)\n"
    r"((?:[^\n]+\n){3})"
)

ATOMIC_POSITIONS = re.compile(
    r"ATOMIC_POSITIONS\s*\(([^)]*)\)\n"
    r"((?:.+\n)+?)"
    r"(?=\n[A-Z_]+|\n!|\nEnd final coordinates|\Z)",
    re.MULTILINE,
)

FORCES_BLOCK = re.compile(
    r"Forces acting on atoms(.*?)Total force",
    re.DOTALL,
)

STRESS_BLOCK = re.compile(
    r"total\s+stress.*?\n"
    r"((?:.*\n){3})",
    re.DOTALL,
)

KPOINT_BLOCK = re.compile(
    r"number of k points=.*?\n(.*?)\n\s*\n",
    re.DOTALL,
)
