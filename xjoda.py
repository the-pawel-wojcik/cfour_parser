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


def parse_xjoda_program(xjoda, args):

    if args.verbose is True:
        pretty_introduce_section(xjoda)

    if 'sections' not in xjoda:
        xjoda['sections'] = []

    catches = cool_lines_in_xjoda(xjoda)

    # TODO: catches should be turned into sections. Each section should
    # contain the keys: name, start, end, lines, sections, data.
    # The sections should be looped over and parsed if a parser is
    # available

    turn_xjoda_catches_into_sections(catches, xjoda)
    parse_xjoda_sections(xjoda)


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for xjoda in programs:
        if xjoda['name'] != 'xjoda':
            continue

        parse_xjoda_program(xjoda, args)

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
