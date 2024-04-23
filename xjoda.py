#!/usr/bin/env python3

import argparse
import sys
import json
import re
from parsers.util import skip_to
from parsers.programs import find_programs
from parsers.text import pretty_introduce_section


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def cool_lines_in_xjoda(xjoda):
    """
    First step on the way of parsing xjoda section of the CFOUR's output.
    """

    if xjoda['name'] != 'xjoda':
        return

    highlights = [
        {'pattern': re.compile(r'\s*CFOUR Control Parameters'),
         'name': 'control parameters',
         'type': 'start',
         },
        {'pattern': re.compile(r'\s*Coordinates used in calculation \(QCOMP\)'),
         'name': 'qcomp',
         'type': 'start',
         },
        {'pattern': re.compile(r'\s*Normal Coordinate Gradient'),
         'name': 'normal coordinate gradient',
         'type': 'start',
         },
        # {'pattern': re.compile(r''),
        #  'name': '',
        #  'type': '',
        #  },
    ]

    catches = list()
    for ln, line in enumerate(xjoda['lines']):
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


def turn_xjoda_catches_into_sections(catches, xjoda):
    lines = xjoda['lines']
    for catch in catches:
        if catch['name'] == 'control parameters':
            THE_LINE = '-' * 67
            start = catch['line']
            if lines[start-1] != lines[start+1] != lines[start+4] != THE_LINE:
                print("Error in parsing the 'CFOUR Control Paramers' section",
                      file=sys.stderr)

            end = skip_to(THE_LINE, lines, start+5)

            cp = {
                'name': 'control parameters',
                'start': xjoda['start'] + start - 1,
                'end': xjoda['start'] + end,
                'lines': lines[start-1: end+1],
                'sections': list(),
                'data': dict(),
            }

            xjoda['sections'] += [cp]

        elif catch['name'] == 'qcomp':
            THE_LINE = '-' * 64
            start = catch['line']
            if lines[start-1] != lines[start+1] != lines[start+4] != THE_LINE:
                print("Error in parsing the QCOMP section of xjoda",
                      file=sys.stderr)

            end = skip_to(THE_LINE, lines, start+5)

            qcomp = {
                'name': 'qcomp',
                'start': xjoda['start'] + start - 1,
                'end': xjoda['start'] + end,
                'lines': lines[start-1: end+1],
                'sections': list(),
                'data': dict(),
            }

            xjoda['sections'] += [qcomp]

        elif catch['name'] == 'normal coordinate gradient':
            name = catch['name']
            THE_LINE = '-' * 71
            start = catch['line']
            if lines[start+1] != lines[start+4] != THE_LINE:
                print(f"Error in parsing the {name} section of xjoda.",
                      file=sys.stderr)

            end = skip_to(THE_LINE, lines, start+5)

            gradient = {
                'name': 'normal coordinate gradient',
                'start': xjoda['start'] + start,
                'end': xjoda['start'] + end,
                'lines': lines[start: end+1],
                'sections': list(),
                'data': dict(),
            }

            xjoda['sections'] += [gradient]


def parse_xjoda_sections(xjoda):
    for section in xjoda['sections']:
        if section['name'] == 'control parameters':
            lines = section['lines'][6:-1]
            data = dict()
            for line in lines:
                external_name = line[0:28].strip()
                internal_name = line[28:34].strip()
                value = line[34:-1].strip()
                data[external_name] = {
                    'internal_name': internal_name,
                    'value': value,
                }
            if 'data' in section:
                section['data'].update(data)
            else:
                section['data'] = data

        if section['name'] == 'qcomp':
            lines = section['lines'][6:-1]
            data = {
                'geometry a.u.': list(),
            }
            for line in lines:
                split_line = line.split()
                zmatrix_symbol = split_line[0]
                atomic_number = int(split_line[1])
                xyz = [float(i) for i in split_line[2:5]]
                data['geometry a.u.'] += [{
                    'Z-matrix Symbol': zmatrix_symbol,
                    'Atomic Number': atomic_number,
                    'Coordinates': xyz,
                }]

            if 'data' in section:
                section['data'].update(data)

            else:
                section['data'] = data

        if section['name'] == 'normal coordinate gradient':
            lines = section['lines'][5:-1]
            data = {
                'Normal Coordinate Gradient': list(),
            }
            for line in lines:
                split_line = line.split()
                mode_no = int(split_line[0])
                frequency = float(split_line[1])
                grad_au = float(split_line[2])
                grad_cm = float(split_line[3])
                grad_eV = float(split_line[4])
                ratio = float(split_line[4])
                data['Normal Coordinate Gradient'] += [{
                    'mode #': mode_no,
                    'omega': frequency,
                    'dE/dQ, a.u.': grad_au,
                    'dE/dQ, cm-1': grad_cm,
                    'dE/dQ, eV': grad_eV,
                    'dE/dQ/omega, relative': ratio,
                }]

            section['data'].update(data)


def parse_xjoda_program(xjoda):

    if 'sections' not in xjoda:
        xjoda['sections'] = []

    catches = cool_lines_in_xjoda(xjoda)
    turn_xjoda_catches_into_sections(catches, xjoda)
    parse_xjoda_sections(xjoda)


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for xjoda in programs:
        if xjoda['name'] != 'xjoda':
            continue

        parse_xjoda_program(xjoda)

        if args.verbose is True:
            pretty_introduce_section(xjoda, 1)

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
