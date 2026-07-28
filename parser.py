"""
QE output file parser for MCP server.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from regex import (
    PROGRAM_VERSION, GIT_REVISION, CALCULATION, NAT, NTYP, NBND, NELEC,
    ECUTWFC, ECUTRHO, XC, FFT_GRID, SMOOTH_GRID, LATTICE_PARAMETER,
    UNIT_CELL_VOLUME, TOTAL_ENERGY, FERMI_ENERGY, TOTAL_FORCE, FORCE_LINE,
    TOTAL_STRESS, STRESS_BLOCK, ATOMIC_POSITIONS, CELL_PARAMETERS,
    JOB_DONE, PWSCF_CPU, TOTAL_MAGNETIZATION, ABS_MAGNETIZATION,
    ATOM_MAGNETIZATION_DETAILED
)


class QEParser:
    def __init__(self):
        self.text = ""       # ファイル全体
        self.lines = []      # 行ごとのリスト
        self.data: dict[str, Any] = {
            "program": {},
            "input": {},
            "structure_initial": {},
            "ionic_steps": [],
            "structure_final": {},
            "timing": {},
        }

    def parse(self, filename: str | Path) -> dict[str, Any]:
        """Parse QE output file."""
        self._load(filename)
        self._parse_program()
        self._parse_system()
        self._parse_structure_initial()
        self._parse_ionic_steps()
        self._parse_structure_final()
        self._parse_timing()
        return self.data

    def _load(self, filename: str | Path) -> None:
        """Load file content."""
        with open(filename, "r", encoding="utf-8") as f:
            self.text = f.read()
        self.lines = self.text.split("\n")

    def _parse_program(self) -> None:
        """Parse program information."""
        program = {}
        
        # Program version
        match = PROGRAM_VERSION.search(self.text)
        if match:
            program["version"] = match.group(1)
        
        # Git revision
        match = GIT_REVISION.search(self.text)
        if match:
            program["git_revision"] = match.group(1).strip()
        
        # Calculation type
        match = CALCULATION.search(self.text)
        if match:
            program["calculation"] = match.group(1)
        
        # Job completion status
        if JOB_DONE.search(self.text):
            program["completed"] = True
        else:
            program["completed"] = False
        
        self.data["program"] = program

    def _parse_system(self) -> None:
        """Parse system parameters."""
        input_data = {}
        
        # Number of atoms
        match = NAT.search(self.text)
        if match:
            input_data["nat"] = int(match.group(1))
        
        # Number of atom types
        match = NTYP.search(self.text)
        if match:
            input_data["ntyp"] = int(match.group(1))
        
        # Number of Kohn-Sham states
        match = NBND.search(self.text)
        if match:
            input_data["nbnd"] = int(match.group(1))
        
        # Number of electrons
        match = NELEC.search(self.text)
        if match:
            input_data["nelec"] = float(match.group(1))
        
        # Cutoff for wave functions
        match = ECUTWFC.search(self.text)
        if match:
            input_data["ecutwfc_ry"] = float(match.group(1))
        
        # Cutoff for charge density
        match = ECUTRHO.search(self.text)
        if match:
            input_data["ecutrho_ry"] = float(match.group(1))
        
        # Exchange-correlation functional
        match = XC.search(self.text)
        if match:
            input_data["xc"] = match.group(1).strip()
        
        # FFT grids
        match = FFT_GRID.search(self.text)
        if match:
            input_data["fft_grid"] = [int(match.group(1)), int(match.group(2)), int(match.group(3))]
        
        match = SMOOTH_GRID.search(self.text)
        if match:
            input_data["smooth_grid"] = [int(match.group(1)), int(match.group(2)), int(match.group(3))]
        
        self.data["input"] = input_data

    def _parse_structure_initial(self) -> None:
        """Parse initial structure."""
        structure = {}
        
        # Extract initial lattice parameters and cell
        for i, line in enumerate(self.lines):
            if "lattice parameter (alat)" in line:
                match = LATTICE_PARAMETER.search(line)
                if match:
                    structure["alat_bohr"] = float(match.group(1))
                break
        
        match = UNIT_CELL_VOLUME.search(self.text)
        if match:
            structure["volume_bohr3"] = float(match.group(1))
        
        # Extract cell parameters
        cell_match = CELL_PARAMETERS.search(self.text)
        if cell_match:
            structure["cell_parameters"] = self._parse_cell_parameters(cell_match.group(2))
        
        # Extract atomic positions (first occurrence)
        pos_match = ATOMIC_POSITIONS.search(self.text)
        if pos_match:
            structure["atomic_positions"] = self._parse_atomic_positions(pos_match.group(2))
        
        # Extract initial magnetization data
        mag_matches = list(TOTAL_MAGNETIZATION.finditer(self.text))
        abs_mag_matches = list(ABS_MAGNETIZATION.finditer(self.text))
        
        if mag_matches:
            mag_match = mag_matches[0]
            structure["magnetization"] = {
                "x": float(mag_match.group(1)),
                "y": float(mag_match.group(2)),
                "z": float(mag_match.group(3)),
            }
        
        if abs_mag_matches:
            abs_mag_match = abs_mag_matches[0]
            structure["abs_magnetization"] = float(abs_mag_match.group(1))
        
        # Extract per-atom magnetization for initial structure (first nat atoms)
        all_atom_mags = list(ATOM_MAGNETIZATION_DETAILED.finditer(self.text))
        nat = self.data["input"].get("nat", 6)
        
        if all_atom_mags:
            atomic_magnetizations = {}
            for atom_mag in all_atom_mags[:nat]:
                atom_num = int(atom_mag.group(1))
                atomic_magnetizations[atom_num] = {
                    "position": [
                        float(atom_mag.group(2)),
                        float(atom_mag.group(3)),
                        float(atom_mag.group(4)),
                    ],
                    "charge": float(atom_mag.group(5)),
                    "magnetization": {
                        "x": float(atom_mag.group(6)),
                        "y": float(atom_mag.group(7)),
                        "z": float(atom_mag.group(8)),
                    },
                    "magnetization_per_charge": {
                        "x": float(atom_mag.group(9)),
                        "y": float(atom_mag.group(10)),
                        "z": float(atom_mag.group(11)),
                    },
                }
            if atomic_magnetizations:
                structure["atomic_magnetizations"] = atomic_magnetizations
        
        self.data["structure_initial"] = structure

    def _parse_structure_final(self) -> None:
        """Parse final structure."""
        structure = {}
        
        # Find the last occurrence of cell parameters and atomic positions
        cell_matches = list(CELL_PARAMETERS.finditer(self.text))
        pos_matches = list(ATOMIC_POSITIONS.finditer(self.text))
        
        if cell_matches:
            structure["cell_parameters"] = self._parse_cell_parameters(cell_matches[-1].group(2))
        
        if pos_matches:
            structure["atomic_positions"] = self._parse_atomic_positions(pos_matches[-1].group(2))
        
        # Extract final magnetization data
        mag_matches = list(TOTAL_MAGNETIZATION.finditer(self.text))
        abs_mag_matches = list(ABS_MAGNETIZATION.finditer(self.text))
        
        if mag_matches:
            mag_match = mag_matches[-1]
            structure["magnetization"] = {
                "x": float(mag_match.group(1)),
                "y": float(mag_match.group(2)),
                "z": float(mag_match.group(3)),
            }
        
        if abs_mag_matches:
            abs_mag_match = abs_mag_matches[-1]
            structure["abs_magnetization"] = float(abs_mag_match.group(1))
        
        # Extract per-atom magnetization for final structure (last nat atoms)
        all_atom_mags = list(ATOM_MAGNETIZATION_DETAILED.finditer(self.text))
        nat = self.data["input"].get("nat", 6)
        
        if all_atom_mags:
            atomic_magnetizations = {}
            for atom_mag in all_atom_mags[-nat:]:  # Last nat atoms
                atom_num = int(atom_mag.group(1))
                atomic_magnetizations[atom_num] = {
                    "position": [
                        float(atom_mag.group(2)),
                        float(atom_mag.group(3)),
                        float(atom_mag.group(4)),
                    ],
                    "charge": float(atom_mag.group(5)),
                    "magnetization": {
                        "x": float(atom_mag.group(6)),
                        "y": float(atom_mag.group(7)),
                        "z": float(atom_mag.group(8)),
                    },
                    "magnetization_per_charge": {
                        "x": float(atom_mag.group(9)),
                        "y": float(atom_mag.group(10)),
                        "z": float(atom_mag.group(11)),
                    },
                }
            if atomic_magnetizations:
                structure["atomic_magnetizations"] = atomic_magnetizations
        
        self.data["structure_final"] = structure

    def _parse_cell_parameters(self, cell_str: str) -> list[list[float]]:
        """Parse cell parameters block."""
        cell = []
        for line in cell_str.strip().split("\n"):
            if line.strip():
                values = [float(x) for x in line.split()]
                if len(values) >= 3:
                    cell.append(values[:3])
        return cell

    def _parse_atomic_positions(self, pos_str: str) -> list[dict[str, Any]]:
        """Parse atomic positions block."""
        positions = []
        for line in pos_str.strip().split("\n"):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    positions.append({
                        "species": parts[0],
                        "x": float(parts[1]),
                        "y": float(parts[2]),
                        "z": float(parts[3]),
                    })
        return positions

    def _parse_ionic_steps(self) -> None:
        """Parse ionic steps data with atomic details."""
        ionic_steps = []
        
        # Extract energy for each step
        energy_matches = list(TOTAL_ENERGY.finditer(self.text))
        
        # Extract magnetization for each step
        mag_matches = list(TOTAL_MAGNETIZATION.finditer(self.text))
        abs_mag_matches = list(ABS_MAGNETIZATION.finditer(self.text))
        
        # Extract all atomic magnetization data
        all_atom_mags = list(ATOM_MAGNETIZATION_DETAILED.finditer(self.text))
        
        # Group atomic magnetizations by step (assume NAT atoms per step)
        nat = self.data["input"].get("nat", 6)
        atom_mags_by_step = {}
        
        for atom_idx, atom_mag in enumerate(all_atom_mags):
            step_idx = atom_idx // nat
            atom_num = int(atom_mag.group(1))
            
            if step_idx not in atom_mags_by_step:
                atom_mags_by_step[step_idx] = {}
            
            atom_mags_by_step[step_idx][atom_num] = {
                "position": [
                    float(atom_mag.group(2)),
                    float(atom_mag.group(3)),
                    float(atom_mag.group(4)),
                ],
                "charge": float(atom_mag.group(5)),
                "magnetization": {
                    "x": float(atom_mag.group(6)),
                    "y": float(atom_mag.group(7)),
                    "z": float(atom_mag.group(8)),
                },
                "magnetization_per_charge": {
                    "x": float(atom_mag.group(9)),
                    "y": float(atom_mag.group(10)),
                    "z": float(atom_mag.group(11)),
                },
            }
        
        for step_idx, energy_match in enumerate(energy_matches):
            step_start = energy_match.start()
            step_end = energy_matches[step_idx + 1].start() if step_idx + 1 < len(energy_matches) else len(self.text)
            step_text = self.text[step_start:step_end]
            
            step_data = {
                "index": step_idx,
                "energy_ry": float(energy_match.group(1)),
            }
            
            # Find forces for this step
            text_before = self.text[:step_start]
            force_matches = list(FORCE_LINE.finditer(text_before))
            forces = {}
            for force_match in force_matches[-9999:]:
                atom_idx = int(force_match.group(1))
                fx = float(force_match.group(2))
                fy = float(force_match.group(3))
                fz = float(force_match.group(4))
                forces[atom_idx] = [fx, fy, fz]
            
            if forces:
                step_data["forces"] = forces
            
            # Find total force
            total_force_match = TOTAL_FORCE.search(step_text)
            if total_force_match:
                step_data["total_force"] = float(total_force_match.group(1))
            
            # Find magnetization data for this step
            if step_idx < len(mag_matches):
                mag_match = mag_matches[step_idx]
                step_data["magnetization"] = {
                    "x": float(mag_match.group(1)),
                    "y": float(mag_match.group(2)),
                    "z": float(mag_match.group(3)),
                }
            
            if step_idx < len(abs_mag_matches):
                abs_mag_match = abs_mag_matches[step_idx]
                step_data["abs_magnetization"] = float(abs_mag_match.group(1))
            
            # Add atomic magnetizations if available
            if step_idx in atom_mags_by_step:
                step_data["atomic_magnetizations"] = atom_mags_by_step[step_idx]
            
            ionic_steps.append(step_data)
        
        self.data["ionic_steps"] = ionic_steps

    def _parse_timing(self) -> None:
        """Parse timing information."""
        timing = {}
        
        match = PWSCF_CPU.search(self.text)
        if match:
            timing["cpu_wall"] = match.group(1).strip()
        
        self.data["timing"] = timing

    def to_json(self, indent: int = 2) -> str:
        """Convert parsed data to JSON string."""
        return json.dumps(self.data, indent=indent)

    def save_json(self, output_file: str | Path, indent: int = 2) -> None:
        """Save parsed data to JSON file."""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=indent)
        print(f"✓ JSON saved to {output_file}")
