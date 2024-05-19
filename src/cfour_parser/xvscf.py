#!/usr/bin/env python3

import argparse
import json
import re
import sys
from cfour_parser.util import skip_to, skip_to_empty_line
from cfour_parser.programs import find_programs
from cfour_parser.util import fortran_float_to_float, ParsingError
from cfour_parser.text import FLOAT, INT, FRTRN_FLOAT, pretty_introduce_section


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def cool_lines_in_xvscf(xvscf):
    """
    First step on the way of parsing xvscf section of the CFOUR's output.
    """

    if xvscf['name'] != 'xvscf':
        return

    highlights = [
        {
            'pattern': re.compile(r'\s*E\(SCF\)=\s+' + FLOAT
                                  + r'\s+' + FRTRN_FLOAT),
            'name': 'energy',
            'type': 'oneline',
        },
        {
            'pattern': re.compile(
                r'\s*ORBITAL EIGENVALUES \(ALPHA\)  \(1H = 27.2113819 eV\)'
            ),
            'name': 'MOs',
            'type': 'start',
        },
        # {'pattern': re.compile(r''),
        #  'name': '',
        #  'type': '',
        #  },
    ]

    catches = list()
    for ln, line in enumerate(xvscf['lines']):
        for highlight in highlights:
            pattern = highlight['pattern']
            match = pattern.match(line)
            if match is None:
                continue
            data = {
                'line': ln,
                'match': match,
            }
            data.update(highlight)
            catches += [data]
            break

    return catches


def parse_MO_line(line):

    # CFOUR outputs graphically -- things can be missing or merging together
    # but at least their position should be the same
    split_no = 57
    numbers = line[0:split_no]
    symmetries = line[split_no:-1]

    mo_pattern = re.compile(r'\s*' + INT + r'\s+' +
                            INT + r'\s+' + FLOAT + r'\s+' + FLOAT)
    mo_match = mo_pattern.match(numbers)
    if mo_match is None:
        raise ParsingError(f"Listing of MOs contains an invalid line:\n{line}")

    ids = {
        'energy #': int(mo_match.group(1)),
        '#': int(mo_match.group(2)),
    }

    eigenvalues = {
        'au': float(mo_match.group(3)),
        'eV': float(mo_match.group(4)),
    }

    fullsymm = symmetries[0:8].strip()
    # comp symmetry
    irrep_name = symmetries[8:19].strip()
    irrep_no = symmetries[19:]

    irrep = {
        'name': irrep_name,
        '#': int(irrep_no[1:-1]),
    }

    mo = {
        'ids': ids,
        'E': eigenvalues,
        'compsymm': irrep,
        'fullsymm': fullsymm,
    }

    return mo


def parse_MOs_listing(catch, lines, lines_offset):
    start = catch['line']

    oll_korrect = True
    header_pattern = re.compile(
        r'\s*MO\s*#\s*E\(hartree\)\s*E\(eV\)\s*FULLSYM\s*COMPSYM')

    header_match = header_pattern.match(lines[start+2])
    if header_match is None:
        raise RuntimeError(
            "Error! The MOs listing in SCF is missing a header."
        )
        oll_korrect = False

    MO_TYPE_SEPARATOR = r'\+' * 77
    occupied_start = start + 4
    occupied_end = skip_to(MO_TYPE_SEPARATOR, lines, start + 4)

    occupied = []
    for line in lines[occupied_start:occupied_end]:
        mo = parse_MO_line(line)
        occupied += [mo]

    virtual_end = skip_to_empty_line(lines, occupied_end)

    virtual = []
    for line in lines[occupied_end+1:virtual_end]:
        try:
            mo = parse_MO_line(line)
        except ParsingError as pe:
            print(pe, file=sys.stderr)
            oll_korrect = False
            continue

        virtual += [mo]

    mos = {
        'name': 'MOs',
        'start': lines_offset + start,
        'end': lines_offset + virtual_end - 1,
        'lines': lines[start: virtual_end],
        'sections': list(),
        'metadata': {
            'ok': oll_korrect,
            },
        'data': {
            'occupied': occupied,
            'virtual': virtual,
        }
    }

    return mos


def turn_xvscf_catches_into_sections(catches, xvscf):
    lines = xvscf['lines']
    for catch in catches:
        if catch['name'] == 'MOs':
            mos = parse_MOs_listing(catch, lines, xvscf['start'])
            xvscf['sections'] += [mos]


def parse_xvscf_program(xvscf):

    if 'sections' not in xvscf:
        xvscf['sections'] = list()

    catches = cool_lines_in_xvscf(xvscf)
    turn_xvscf_catches_into_sections(catches, xvscf)

    # TODO: catches should be turned into sections. Each section should
    # contain the keys: name, start, end, lines, sections, data.
    # The sections should be looped over and parsed if a parser is
    # available

    data = dict()
    for catch in catches:
        if catch['type'] != 'oneline':
            continue

        if catch['name'] == 'energy':
            data['energy'] = {
                'au': float(catch['match'].group(1)),
            }
            e_std = fortran_float_to_float(catch['match'].group(2))
            data['energy convergence'] = e_std

    if 'data' not in xvscf:
        xvscf['data'] = data
    else:
        xvscf['data'].update(data)


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for program in programs:
        if program['name'] == 'xvscf':
            parse_xvscf_program(program)

            if args.verbose is True:
                pretty_introduce_section(program, 1)

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
