#!/usr/bin/env python3

import argparse
import json
from cfour_parser.text import pretty_introduce_section
from cfour_parser.programs import find_programs
from cfour_parser.xjoda import parse_xjoda_program
from cfour_parser.xvscf import parse_xvscf_program
from cfour_parser.xdqcscf import parse_xdqcscf_program
from cfour_parser.xncc import parse_xncc_program
from cfour_parser.xvee import parse_xvee_program


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=0, action='count')
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    parsers = {
        'xjoda': parse_xjoda_program,
        'xvscf': parse_xvscf_program,
        'xdqcscf': parse_xdqcscf_program,
        'xncc': parse_xncc_program,
        'xvee': parse_xvee_program,
    }

    for program in programs:
        if program['name'] in parsers:
            parse_program = parsers[program['name']]
            parse_program(program)

    if args.json is True:
        print(json.dumps(programs))

    if args.verbose is True:
        for program in programs:
            pretty_introduce_section(program)

    if args.verbose > 0:
        for program in programs:
            pretty_introduce_section(program, args.verbose)


if __name__ == "__main__":
    main()
