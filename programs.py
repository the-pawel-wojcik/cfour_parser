#!/usr/bin/env python3

import os.path
import argparse
import re
import sys


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def get_stack_of_program_limits(lines):
    """
    Finds lines that mark the beginning or the end of a program execution.
    Returns a list of dictionaries which have the entry 'type' marking
    either a start or an end of a program; and the entry 'line' marking the
    output line (first line being numbered zero).
    """
    sec_head = "--invoking executable--"
    sec_end = "--executable"
    stack = []

    # Collect key points
    for ln, line in enumerate(lines):
        if line.strip().startswith(sec_head):
            node = {
                'type': 'head',
                'line': ln,
                'data': {
                    'ok': True,
                },
            }
            stack.append(node)
        elif line.strip().startswith(sec_end):
            node = {
                'type': 'end',
                'line': ln,
                'data': {
                    'ok': True,
                },
            }
            stack.append(node)

    return stack


def add_names_of_program_starts(stack, lines):
    """
    Parses the line after '--invoking executable' to tell the name of the
    program and adds this information to the stack's dictionary under the key
    'name'.
    """
    for limit in stack:
        if limit['type'] != 'head':
            continue

        head_line = limit['line']

        # if the header is the last line of the file no name of the file
        # can be parsed
        if len(lines) == head_line + 1:
            print(f"Unexpected end of output at line {head_line}",
                  file=sys.stderr)
            limit['data']['ok'] = False

        name_line = lines[head_line + 1]
        program = os.path.basename(name_line.strip())
        limit['name'] = program

    return stack


def parse_executable_finish_line(line):
    """
    Parses the line that marks executable finish, i.e. the line starting with
    `--executable <name> finished with status`
    Returns {'name', 'exit status', 'walltime, sec'}
    If failed returns None.
    """
    pattern = re.compile(r'--executable (\w+) finished with status\s+(\d+)'
                         r' in\s+(\d+\.\d+)')

    match = pattern.match(line)
    if match is None:
        print("Warning! Parsing of the '--executable <name> finished ...' line"
              " failed.", file=sys.stderr)
        return None

    score = {
        'name': match.group(1),
        'exit status': int(match.group(2)),
        'walltime, sec': float(match.group(3)),
    }
    return score


def add_names_of_program_ends(stack, lines):
    """
    An end version of `add_names_of_program_starts`.
    """
    for limit in stack:
        if limit['type'] != 'end':
            continue

        end_line = limit['line']
        finish_line_data = parse_executable_finish_line(lines[end_line])

        if finish_line_data is None:
            limit['data']['ok'] = False
            continue

        limit['name'] = finish_line_data['name']
        del finish_line_data['name']
        limit['data'].update(finish_line_data)

    return stack


def find_programs(cfour):
    """
    Input is an open file with CFOUR's output.
    Output is a list of collected programs.
    Each program is represented by a dictionary with:
        'name': program name.
        'start': line number (first line of output is numbered 1)
        'end': line number (first line of output is numbered 1)
        'lines': a list, each entry is one line of the program's output.
        'sections': list()
        'data': {
            'ok': bool,  # True if didn't detect parsing nor program errors
            'exit status': int(),
            'walltime, sec': Reported execution time
        }
    """

    lines = cfour.readlines()
    stack = get_stack_of_program_limits(lines)
    add_names_of_program_starts(stack, lines)
    add_names_of_program_ends(stack, lines)

    # Match program starts with program ends
    programs = list()
    active = []
    while len(stack) != 0:
        node = stack.pop()
        if len(active) == 0:
            active.append(node)
            continue

        # Ends go on stack and wait to match with a start
        if node['type'] == 'end':
            active.append(node)
            continue

        # There is a match
        match = active.pop()
        looks_good = True

        # TODO: the document might be incorrectly formatted -- but the compiler
        # should still finish its job
        if node['type'] != 'head' or match['type'] != 'end':
            print("Error in parsing starts and ends of program sections.",
                  file=sys.stderr)
            print("A missmatch between started and completed programs.",
                  file=sys.stderr)
            print("The resulted partition is not reliable.",
                  file=sys.stderr)
            looks_good = False

        # Check that the program names are also alright
        if node['name'] != match['name']:
            print("Error in parsing starts and ends of executables.",
                  file=sys.stderr)
            print(f"The opening of executable {node['name']} is matched with "
                  f"{match['name']}.",
                  file=sys.stderr)
            print("The resulted partition is not reliable.",
                  file=sys.stderr)
            looks_good = False

        if node['data']['ok'] is False or match['data']['ok'] is False:
            looks_good = False

        start_line = node['line']
        end_line = match['line']
        program = {
            # Editors list the first line as number 1 not number 0.
            'start': start_line + 1,
            'end': end_line + 1,
            'lines': lines[start_line:end_line+1]
        }
        if 'name' in match:
            program['name'] = match['name']
        program_data = node['data']
        program_data.update(match['data'])
        program['data'] = program_data
        if looks_good is False:
            program['data']['ok'] = False
        program['sections'] = list()

        programs += [program]

    # TODO: parsing of a program that has finished only parts of the jobs
    # should be allowed
    if len(active) != 0:
        print("Error in parsing starts and ends of program sections.",
              file=sys.stderr)
        print("Best guess: some programs did not finish.", file=sys.stderr)

    bad = [program for program in programs if program['data']['ok'] is False]
    if len(bad) > 0:
        print("Warning! Programs with errors detected in xcfour.",
              file=sys.stderr)

    programs = [program for program in programs if
                program['data']['ok'] is True]

    # List programs in chronological execution order
    programs = programs[::-1]
    return programs


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    if args.verbose is True:
        for program in programs:
            start = program['start']
            end = program['end']
            name = program['name']
            ext = program['data']['exit status']
            time = program['data']['walltime, sec']
            msg = f"{start:5d} -- {end:5d}: {name:12s} took"
            msg += f"{time:.2f}".rjust(10) + " sec"
            if ext != 0:
                msg += f" and returned {ext}."
            else:
                msg += "."
            print(msg)


if __name__ == "__main__":
    main()
