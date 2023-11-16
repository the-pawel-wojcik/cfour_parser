#!/usr/bin/env python3

import argparse
import sys
from parsers.programs import find_programs


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def find_geometry_lines(xjoda_lines):
    """
    Returns a pair of integers (start, end), see below.
    Finds the line numbers of the computational geometry section of the output.
    i.e.

 ---------------------------------------------------------------- <-- start
         Coordinates used in calculation (QCOMP)
 ----------------------------------------------------------------
 Z-matrix   Atomic            Coordinates (in bohr)
  Symbol    Number           X              Y              Z
 ----------------------------------------------------------------
     X         0        -0.00000000    -0.00000000    -2.37436681
     ...
     H         1         0.70577635    -6.59374698     4.88803335
 ---------------------------------------------------------------- <-- end
    """

    header = 'Coordinates used in calculation (QCOMP)'
    # END = '-' * 65
    END = '----------------------------------------------------------------'

    start = None
    ends = []
    for ln, line in enumerate(xjoda_lines):
        if line.strip().startswith(header):
            if start is None:
                start = ln
            else:
                print("Warning! Multiple QCOMP in a single xjoda.",
                      file=sys.stderr)

            continue

        # Look for the ends of the geometry
        if start is not None and line.strip() == END:
            ends += [ln]

    if start is None:
        return None, None

    # The QCOMP is decorated with '-' * 64 in the line above
    if start == 0:
        print("Warning! QCOMP section of xjoda looks bad...", file=sys.stderr)
        return start, None

    if len(ends) < 3:
        print("Warning! QCOMP section of xjoda looks bad...", file=sys.stderr)
        return start, None

    if ends[0] != start + 1 or ends[1] != start + 4:
        print("Warning! QCOMP section of xjoda looks bad...", file=sys.stderr)
        return start, None

    return (start - 1, ends[2])


def parse_geometry_lines(lines):
    """
    Returns a list of atoms. Each atom is represented by a dictionary with
    keywords:
        - 'atom': The atomic symbol. One or two letters. The first letter is
                  capitalized, the remaining ones are lowercase.
        - 'xyz': a list of three floats [x, y, z], the Cartesian coordinates of
                 the atom.
    """
    if lines is None:
        return []

    skip_header_line = 6
    mol_xyz = []
    for line in lines[skip_header_line:-1]:
        # print(line, end='')

        # Finally some parsing
        line = line.split()
        # I am skipping the second column which contains the atomic
        # charge
        atom = line[0]
        # make the atom formatting look like a man
        # Capitalize only the first letter
        atom = atom[0] + atom[1:].lower()
        mol_xyz += [{'atom': atom,
                     'xyz': [float(i) for i in line[2:]]}]

    return mol_xyz


def distance_AU_to_A(mol_c4):
    au2A = 0.529177  # from Google, TODO: find more authorative version
    mol_xyz = mol_c4
    for atom in mol_xyz:
        atom['xyz'] = [pos * au2A for pos in atom['xyz']]
    return mol_xyz


def add_geometry_to_xjoda_sections(xjoda):
    """
    `xjoda` is a dictionary, with keywords: 'name' set to 'xjoda',
    'lines' being the output of CFOUR (list of strs) that forms the xjoda part.

    This function will add the 'sections' keyword to `xjoda` (if not already
    present) which will be a list of dictionaries.

    Only one dictionary will be added to the 'sections' list. The added
    dictionary will be a json of the 'QCOMP' section. You can find it as it
    will have the 'name' keyword set to 'QCOMP'.

    The parsed geometry will be under 'geometry' and will be a list of dicts
    each entry contaning entries 'atom' and 'xyz'.

    Nothing happens to `xjoda` if no QCOMP section is detected. Warnings
    will be printed.
    """
    if xjoda['name'] != 'xjoda':
        return

    geo_start, geo_end = find_geometry_lines(xjoda['lines'])

    if geo_start is None or geo_end is None:
        print("Warning! Failed to parse QCOMP from xjoda at lines "
              f"{xjoda['start']} -- {xjoda['end']}", file=sys.stderr)
        return

    geometry_lines = xjoda['lines'][geo_start: geo_end + 1]
    geometry = parse_geometry_lines(geometry_lines)

    for section in xjoda['sections']:
        if section['name'] == 'QCOMP':
            print("Error! xjoda contains multiple QCOMP sections.")

    xjoda['sections'] += [{
        'name': 'QCOMP',
        'start line': geo_start + xjoda['start'],
        'end line': geo_end + xjoda['start'],
        'lines': geometry_lines,
        'geometry': geometry,
    }]


def assure_progam_has_sections(program):
    if 'sections' not in program.keys():
        program['sections'] = []


def print_xyz_geometry(qcomp):
    """
    `qcomp` is a section of xjoda
    """

    mol_c4 = qcomp['geometry']
    mol_xyz = distance_AU_to_A(mol_c4)

    # First line of xyz file has to list number of atoms presnt in the moleucle
    print(len(mol_xyz))
    # Second line of xyz filetype is saved for a comment
    print(f"QCOMP from lines {qcomp['start line']} -- {qcomp['end line']}")
    for atom in mol_xyz:
        print(f"{atom['atom']:2s}", end='')
        for i in atom['xyz']:
            print(f" {i:-12.6f}", end='')
        print("")


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for program in programs:
        assure_progam_has_sections(program)
        add_geometry_to_xjoda_sections(program)

    if args.verbose is True:
        for program in programs:
            if program['name'] != 'xjoda':
                continue

            for section in program['sections']:
                if section['name'] != 'QCOMP':
                    continue

                print_xyz_geometry(section)


if __name__ == "__main__":
    main()
