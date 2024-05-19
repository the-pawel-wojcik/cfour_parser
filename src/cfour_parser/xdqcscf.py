#!/usr/bin/env python3

import argparse
import json
import re
from cfour_parser.programs import find_programs
from cfour_parser.text import FLOAT, pretty_introduce_section
from cfour_parser.xvscf import parse_MOs_listing


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def cool_lines_in_xdqcscf(xdqcscf):
    """
    First step on the way of parsing this section of the CFOUR's output.
    """

    if xdqcscf['name'] != 'xdqcscf':
        return

    highlights = [
        {
            'pattern': re.compile(r'\s*E\(SCF\) =\s+' + FLOAT),
            'name': 'energy',
            'type': 'oneline',
        },
        # WARNING: This is almost the same as in xvscf EXCPET that the last few
        # digists of the 1H are different!
        {
            'pattern': re.compile(
                r'\s*ORBITAL EIGENVALUES \(ALPHA\)  \(1H = 27.2113834 eV\)'
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
    for ln, line in enumerate(xdqcscf['lines']):
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


def turn_xdqcscf_catches_into_sections_and_data(catches, xdqcscf):

    lines = xdqcscf['lines']
    for catch in catches:
        if catch['name'] == 'MOs':
            mos = parse_MOs_listing(catch, lines, xdqcscf['start'])
            xdqcscf['sections'] += [mos]

    data = dict()
    for catch in catches:
        if catch['type'] != 'oneline':
            continue

        if catch['name'] == 'energy':
            data['energy'] = {
                'au': float(catch['match'].group(1)),
            }

    xdqcscf['data'].update(data)


def parse_xdqcscf_program(xdqcscf):

    catches = cool_lines_in_xdqcscf(xdqcscf)
    turn_xdqcscf_catches_into_sections_and_data(catches, xdqcscf)

    # TODO: catches should be turned into sections. Each section should
    # contain the keys: name, start, end, lines, sections, data.
    # The sections should be looped over and parsed if a parser is
    # available


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for program in programs:
        if program['name'] == 'xdqcscf':

            parse_xdqcscf_program(program)

            if args.verbose is True:
                pretty_introduce_section(program)

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
