#!/usr/bin/env python3

import argparse
import json
import re
from parsers.programs import find_programs
from parsers.util import fortran_float_to_float
from parsers.text import FLOAT, INT, FLOAT_WS, INT_WS, FRTRN_FLOAT, \
    pretty_introduce_section


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
        {'pattern': re.compile(r'\s*E\(SCF\)=\s+' + FLOAT
                               + r'\s+' + FRTRN_FLOAT),
            'name': 'energy',
            'type': 'oneline',
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


def parse_xvscf_program(xvscf, args):

    if args.verbose is True:
        pretty_introduce_section(xvscf)

    if 'sections' not in xvscf:
        xvscf['sections'] = []

    catches = cool_lines_in_xvscf(xvscf)

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

    for xvscf in programs:
        if xvscf['name'] != 'xvscf':
            continue

        parse_xvscf_program(xvscf, args)

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
