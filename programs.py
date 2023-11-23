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
            }
            stack.append(node)
        elif line.strip().startswith(sec_end):
            node = {
                'type': 'end',
                'line': ln,
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
            continue

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
              " failed.")
        return {}

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
        limit.update(finish_line_data)

    return stack


def get_start_ends(lines):
    """
    Returns a list of dictionaries with two eneries:
        'start', and 'end'
    These numbers are line numbers where a program starts or ends.
    The first line has the number 0.
    """

    stack = get_stack_of_program_limits(lines)
    add_names_of_program_starts(stack, lines)
    add_names_of_program_ends(stack, lines)

    # Match program starts with program ends
    programs_limits = []
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
            print("Error in parsing starts and ends of program sections.")
            print("A missmatch between started and completed programs.")
            print("The resulted partition is not reliable.")
            looks_good = False

        # Check that the program names are also alright
        if node['name'] != match['name']:
            print("Error in parsing starts and ends of executables.")
            print(f"The opening of executable {node['name']} is matched with "
                  f"{match['name']}.")
            print("The resulted partition is not reliable.")
            looks_good = False

        program_limits = {
            'start': node['line'],
            'end': match['line'],
            'all good': looks_good,
        }
        programs_limits += [program_limits]

    # TODO: parsing of a program that has finished only parts of the jobs 
    # should be allowed
    if len(active) != 0:
        print("Error in parsing starts and ends of program sections.",
              file=sys.stderr)
        print("Best guess: some programs did not finish.", file=sys.stderr)

    # List programs in chronological execution order
    programs_limits = programs_limits[::-1]
    return programs_limits


def find_programs(cfour):
    """
    Input is an open file with CFOUR's output.
    Output is a list of collected programs.
    Each program is represented by a dictionary with:
        'name': program name.
        'exit status':
        'walltime, sec': Reported execution time
        'start': line number (first line of output is numbered 1)
        'end': line number (first line of output is numbered 1)
        'lines': a list, each entry is one line of the program's output.
    """
    lines = cfour.readlines()
    programs_start_ends = get_start_ends(lines)

    for program in programs_start_ends:
        start = program['start']
        end = program['end']
        program_info = parse_executable_finish_line(lines[end])
        if program_info is None:
            program['name'] = '???'
            program['exit status'] = '???'
            program['walltime, sec'] = '???'
        else:
            program.update(program_info)

        program['lines'] = lines[start:end+1]
        # Editors usually list the first line as number 1 not number 0.
        program['start'] += 1
        program['end'] += 1

    return programs_start_ends


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    if args.verbose is True:
        for program in programs:
            start = program['start']
            end = program['end']
            name = program['name']
            ext = program['exit status']
            time = program['walltime, sec']
            msg = f"{start:5d} -- {end:5d}: {name:12s} took"
            msg += f"{time}".rjust(10) + " sec"
            if ext != 0:
                msg += f" and returned {ext}."
            else:
                msg += "."
            print(msg)


if __name__ == "__main__":
    main()
