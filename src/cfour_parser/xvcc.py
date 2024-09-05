#!/usr/bin/env python3

import argparse
import json
import re
from cfour_parser.programs import find_programs
from cfour_parser.text import INT_WS, FLOAT, FLOAT_WS, pretty_introduce_section, print_section


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=0, action='count')
    args = parser.parse_args()
    return args


def parse_xvcc_program(xvcc):
    """
    Parser of the xvcc program.
    """
    catches = cool_lines_in_xvcc(xvcc)
    turn_xvcc_catches_into_sections(catches, xvcc)


def cool_lines_in_xvcc(xvcc):
    """
    The lines I would look for while reading the CFOUR's output file.
    """

    if xvcc['name'] != 'xvcc':
        return

    highlights = [
        {'re': r'\s*A miracle has come to pass\. '
         r'The CC iterations have converged\.',
         'name': 'A miracle',
         'type': 'start',
         },
        # {'pattern': re.compile(r''),
        #  'name': '',
        #  'type': '',
        #  },
    ]
    for highlight in highlights:
        highlight['pattern'] = re.compile(highlight['re'])

    catches = list()
    for ln, line in enumerate(xvcc['lines']):
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


def turn_xvcc_catches_into_sections(catches, xvcc):
    """
    Catches are turned into sections.
    """
    xvcc_section_parsers = {
        'A miracle': parse_xvcc_miracle,
    }
    for catch in catches:
        section_name = catch['name']
        if section_name in xvcc_section_parsers:
            parser = xvcc_section_parsers[section_name]
            # cp = {
            #     'name': section_name,
            #     'start': xvee['start'] + start - 1,
            #     'end': xvee['start'] + end,
            #     'lines': lines[start-1: end+1],
            #     'sections': list(),
            #     'data': dict(),
            #     'metadata': dict(),
            # }
            section = parser(catch, xvcc)
            xvcc['sections'] += [section]


def parse_xvcc_miracle(catch, xvcc):
    """
    Example imput 
    ```cfour
      A miracle has come to pass. The CC iterations have converged.
      The reference energy is      -262.78442212586253 a.u.
      The correlation energy is      -1.13191391716710 a.u.
      The total energy is          -263.91633604302962 a.u.
    ```
    """

    oll_korrect = True
    catch_line = catch['line']
    lines = xvcc['lines']

    data = {}
    energy = {}
    last_line = catch_line + 3

    ref_energy_re = r'\s*The reference energy is' + FLOAT_WS + r'a\.u\.'
    ref_match = re.match(ref_energy_re, lines[catch_line + 1])
    if ref_match is None:
        oll_korrect = False
    else:
        energy['Reference'] = {
            'au': float(ref_match.group(1)),
        }

    correlation_re = r'\s*The correlation energy is' + FLOAT_WS + r'a\.u\.'
    correlation_match = re.match(correlation_re, lines[catch_line + 2])
    if correlation_match is None:
        oll_korrect = False
    else:
        energy['correlation'] = {
            'au': float(correlation_match.group(1)),
        }

    total_re = r'\s*The total energy is' + FLOAT_WS + r'a\.u\.'
    total_match = re.match(total_re, lines[catch_line + 3])
    if total_match is None:
        oll_korrect = False
    else:
        energy['total'] = {
            'au': float(total_match.group(1)),
        }

    data['energy'] = energy

    section = {
        'name': catch['name'],
        'start': xvcc['start'] + catch_line,
        'end': xvcc['start'] + last_line,
        'sections': list(),
        'lines': lines[catch_line:last_line+1],
        'metadata': {
            'ok': oll_korrect,
        },
        'data': data,
    }
    return section


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for xvcc in programs:
        if xvcc['name'] != 'xvcc':
            continue

        parse_xvcc_program(xvcc)

        if args.verbose > 0:
            pretty_introduce_section(xvcc, 1)
            if args.verbose > 1:
                for section in xvcc['sections']:
                    pretty_introduce_section(section, 1)
                    print_section(section)
                    if args.verbose > 2:
                        for data in section['data']:
                            print(f"{data=}")
                            print(section['data'][data])

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
