#!/usr/bin/env python3

import argparse
from parsers.programs import find_programs
import sys
import re


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def cool_lines_in_xncc(xncc):
    """
    First step on the way of parsing xncc section of the CFOUR's output.
    This function lists the recognized parts of the xncc section.
    """
    if xncc['name'] != 'xncc':
        return

    double = r'\s*-?\d+\.\d+\s*'
    highlights = [
        {'pattern': re.compile(
            r'Simulation and memory analysis took \d+\.\d+ seconds'),
            'name': 'mem',
            'type': 'end',
         },
        {'pattern': re.compile(r'MP2 correlation energy:' + double),
            'name': 'mp2',
            'type': 'start',
         },
        {'pattern': re.compile(r'Total MP2 energy:' + double),
         'name': 'mp2',
         'type': 'end',
         },
        {'pattern': re.compile(
            r'Beginning iterative solution of CCSD equations:'),
         'name': 'ccsd',
         'type': 'start',
         },
        {'pattern': re.compile(r'Total CCSD energy:' + double),
         'name': 'ccsd',
         'type': 'end',
         },
        {'pattern': re.compile(r'Formation of H took' + double + 'seconds at'
                               + double + 'Gflops/sec'),

         'name': 'eom',
         'type': 'start',
         },
        # {'pattern': re.compile(r''),
        #  'name': '',
        #  },
    ]
    catches = []
    for ln, line in enumerate(xncc['lines']):
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


def get_eom_lines_from_xncc(xncc, catches):
    last_end = None
    eom_start_ln = None
    eom_end_ln = None
    for catch in catches:
        line = catch['line']

        # keep track of the last ending of a section
        if catch['type'] == 'end':
            if last_end is None or last_end < line:
                last_end = line

        # fish for EOM
        if catch['name'] == 'eom':
            if catch['type'] == 'start':
                eom_start_ln = line
                continue
            elif catch['type'] == 'end':
                eom_end_ln = line
                continue
            print("Warrning unrecognized eom header in xncc", file=sys.errstr)

    if eom_start_ln is None:
        print("Warning! No xncc EOM section", file=sys.errstr)
        return

    if eom_end_ln is None:
        # most likely eom is the last section
        if last_end < eom_start_ln:
            eom_end_ln = len(xncc['lines']) - 1
        else:
            # TODO:
            pass

    eom_section = {
        'name': 'eom',
        'start': eom_start_ln + xncc['start'],
        'end': eom_end_ln + xncc['start'],
        'lines': xncc['lines'][eom_start_ln:eom_end_ln+1]
    }
    return eom_section


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for program in programs:
        if program['name'] != 'xncc':
            continue
        catches = cool_lines_in_xncc(program)
        eom_section = get_eom_lines_from_xncc(program, catches)
        eom_start = eom_section['start']
        for ln, line in enumerate(eom_section['lines']):
            print(f"{ln + eom_start:5d}: {line[:-1]}")


if __name__ == "__main__":
    main()
