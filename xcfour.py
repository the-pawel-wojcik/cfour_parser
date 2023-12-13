#!/usr/bin/env python3

import argparse
import json
from parsers.text import pretty_introduce_section
from parsers.programs import find_programs
from parsers.xjoda import parse_xjoda_program
from parsers.xvscf import parse_xvscf_program
from parsers.xdqcscf import parse_xdqcscf_program
from parsers.xncc import parse_xncc_program


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

    for program in programs:
        if program['name'] == 'xjoda':
            parse_xjoda_program(program)

        if program['name'] == 'xvscf':
            parse_xvscf_program(program)

        if program['name'] == 'xdqcscf':
            parse_xdqcscf_program(program)

        if program['name'] == 'xncc':
            parse_xncc_program(program)

    if args.json is True:
        print(json.dumps(programs))

    if args.verbose is True:
        for program in programs:
            pretty_introduce_section(program)

    if args.verbose == 1:
        for program in programs:
            pretty_introduce_section(program)

    if args.verbose == 2:
        for program in programs:
            pretty_introduce_section(program, 2)


if __name__ == "__main__":
    main()
