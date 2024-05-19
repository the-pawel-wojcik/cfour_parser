#!/usr/bin/env python3

import argparse
import sys
import json
import re
from cfour_parser.util import skip_to, skip_to_re, skip_to_empty_line
from cfour_parser.programs import find_programs
from cfour_parser.text import FLOAT, INT, FLOAT_WS, INT_WS, \
    pretty_introduce_section


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
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

    highlights = [
        {'pattern': re.compile(
            'Simulation and memory analysis took' + FLOAT_WS + 'seconds'),
            'name': 'mem',
            'type': 'end',
         },
        {'pattern': re.compile(r'MP2 correlation energy:' + FLOAT_WS),
            'name': 'mp2',
            'type': 'start',
         },
        {'pattern': re.compile(r'Total MP2 energy:' + FLOAT_WS),
         'name': 'mp2',
         'type': 'end',
         },
        {'pattern': re.compile(
            r'Beginning iterative solution of (CCSD|CCSDT|CCSDTQ) equations:'),
         'name': 'cc',
         'type': 'start',
         },
        {'pattern': re.compile(r'Total CC(?:SD|SDT|SDTQ) energy:' + FLOAT_WS),
         'name': 'cc',
         'type': 'end',
         },
        {'pattern': re.compile(r'Formation of H took' + FLOAT_WS + 'seconds at'
                               + FLOAT_WS + 'Gflops/sec'),

         'name': 'eom',
         'type': 'start',
         },
        # {'pattern': re.compile(r''),
        #  'name': '',
        #  'type': '',
        #  },
    ]

    catches = list()
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


def get_cc_lines_from_xncc(xncc, catches):
    """
    This function should be generalized to extract lines of all catches
    """
    last_end = None  # Line where the last catch of the 'end' 'type' appears
    cc_start_ln = None
    cc_end_ln = None
    data = dict()
    for catch in catches:
        line = catch['line']

        # keep track of the last ending of a section
        if catch['type'] == 'end':
            if last_end is None or last_end < line:
                last_end = line

        # fish for CC
        if catch['name'] == 'cc':
            if catch['type'] == 'start':
                cc_start_ln = line
                data['CC level'] = catch['match'].group(1)
                continue
            elif catch['type'] == 'end':
                cc_end_ln = line
                data['energy'] = {
                    'total': {
                        'au': float(catch['match'].group(1)),
                    },
                }
                continue
            print("Warrning unrecognized CC header in xncc\n"
                  f"{catch=}", file=sys.stderr)

    if cc_start_ln is None:
        print("Warning! No beginning of the CC section found in xncc",
              file=sys.stderr)
        return

    if cc_end_ln is None:
        print("Error! Problem in parsing CC of xncc.", file=sys.stderr)
        pass

    cc_section = {
        'name': 'cc',
        'start': xncc['start'] + cc_start_ln,
        'end':  xncc['start'] + cc_end_ln,
        'lines': xncc['lines'][cc_start_ln:cc_end_ln+1],
        'sections': list(),
        'data': data,
    }

    return cc_section


def parse_xncc_cc(xncc_cc):
    """ The CC section of the xncc program. """

    lines = xncc_cc['lines']
    # from text import print_section
    # print_section(xncc_cc)

    # TODO: this is the tokenizer of the CC section of the xncc program.
    iterations_start = None
    iterations_end = None
    it_start_pattern = re.compile(
        r'\s*Beginning iterative solution of '
        r'(CCSD|CCSDT|CCSDTQ) equations:')
    it_end_pattern = re.compile(
        r'CC(?:SD|SDT|SDTQ) iterations converged in' +
        INT_WS + r'cycles and' + FLOAT_WS + r'seconds \(' +
        FLOAT_WS + r's/it.\) at' + FLOAT_WS + r'Gflops/sec')

    data = dict()

    for ln, line in enumerate(lines):
        it_start_match = it_start_pattern.match(line)
        if it_start_match is not None:
            iterations_start = ln
            data['CC model'] = it_start_match.group(1)
            continue
        it_end_match = it_end_pattern.match(line)
        if it_end_match is not None:
            iterations_end = ln
            data['# iterations'] = int(it_end_match.group(1))
            data['time, sec'] = float(it_end_match.group(2))
            data['Gflops/s'] = float(it_end_match.group(4))
            continue

    if iterations_start is None:
        print("Error in parsing CC section of xncc.\n\t"
              "No beginning of the CC iterations found.", file=sys.stderr)
        return

    if iterations_end is None:
        print("Error in parsing CC section of xncc.\n\t"
              "No end of the CC iterations found.", file=sys.stderr)
        return

    xncc_cc['sections'] += [{
        'name': 'iterations',
        'start': xncc_cc['start'] + iterations_start,
        'end': xncc_cc['start'] + iterations_end,
        'lines': lines[iterations_start: iterations_end + 1],
        'sections': list(),
        'data': data,
    }]

    # TODO: Parse iterations section


def get_eom_lines_from_xncc(xncc, catches):
    """
    This function should be generalized to extract lines of all catches
    """
    last_end = None  # Line where the last catch of the 'end' 'type' appears
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
            print("Warrning unrecognized eom header in xncc", file=sys.stderr)

    if eom_start_ln is None:
        print("Warning! No xncc EOM section", file=sys.stderr)
        return

    if eom_end_ln is None:
        # most likely eom is the last section
        if last_end < eom_start_ln:
            eom_end_ln = len(xncc['lines']) - 1
        else:
            # TODO:
            print("Error! Problem in parsing eom of xncc.", file=sys.stderr)
            pass

    eom_section = {
        'name': 'eom',
        'start': eom_start_ln + xncc['start'],
        'end': eom_end_ln + xncc['start'],
        'lines': xncc['lines'][eom_start_ln:eom_end_ln+1]
    }
    return eom_section


def parse_singles_of_converged_root(lines, ln, lines_offset):
    singles = []
    singles_pattern = re.compile(r'\s+' + INT + r'\s+' + INT + r'\s+' + FLOAT)
    while True:
        ln += 1
        if ln >= len(lines):
            print("Warning error in processing converged root"
                  f"\n line {ln + lines_offset}",
                  file=sys.stderr)
            return
        matchlist = singles_pattern.findall(lines[ln])

        # an empty lines means ends the listing
        if len(matchlist) == 0:
            break

        for match in matchlist:
            singles += [{
                "A": int(match[0]),
                "I": int(match[1]),
                "amplitude": float(match[2]),
            }]
    singles.sort(key=lambda x: abs(x['amplitude']), reverse=True)
    return ln, singles


def parse_doubles_of_converged_root(lines, ln, lines_offset):
    doubles = []
    doubles_pattern = re.compile((r'\s+' + INT) * 4 + r'\s+' + FLOAT)
    while True:
        ln += 1
        if ln >= len(lines):
            print("Warning error in processing converged root"
                  f"\n line {ln + lines_offset}",
                  file=sys.stderr)
            return
        matchlist = doubles_pattern.findall(lines[ln])

        # an empty line means the end of listing
        if len(matchlist) == 0:
            break

        for match in matchlist:
            doubles += [{
                "A": int(match[0]),
                "B": int(match[1]),
                "I": int(match[2]),
                "J": int(match[3]),
                "amplitude": float(match[4]),
            }]
    doubles.sort(key=lambda x: abs(x['amplitude']), reverse=True)
    return ln, doubles


def parse_xncc_eom_converged_root(converged_root):
    if converged_root['name'] != 'converged root':
        return

    # Aplitudes will be stored under the 'data' keyword
    if 'data' not in converged_root.keys():
        converged_root['data'] = {}

    root_start_ln = converged_root['start']
    lines = converged_root['lines']
    ln = 0

    # Singles
    ln = skip_to(r'\s*-+\s+', lines, ln)
    singles_header = re.compile(r'(\s*A\s+I){3}')
    if singles_header.match(lines[ln-1]) is None:
        print("Warning unable to process converged root"
              f"\n line {ln + root_start_ln - 1}", file=sys.stderr)
        return
    ln, singles = parse_singles_of_converged_root(lines, ln, root_start_ln)
    converged_root['data']['singles'] = singles

    # Doubles
    ln = skip_to(r'\s*-+', lines, ln)
    doubles_header = re.compile(r'(?:\s+A\s+B\s+I\s+J){,2}')
    if doubles_header.match(lines[ln-1]) is None:
        print("Warning unable to process converged root at line "
              f"{root_start_ln + ln - 1}", file=sys.stderr)
        return
    ln, doubles = parse_doubles_of_converged_root(lines, ln, root_start_ln)
    converged_root['data']['doubles'] = doubles


def parse_xncc_eom_root_sections(sections):
    for section in sections:
        # TODO: there are more sections availabe for parsing. If needed one
        # needs to wire their parsers
        if section['name'] == 'converged root':
            parse_xncc_eom_converged_root(section)
            continue


def parse_xncc_eom_root(lines, line_offset):
    """
    Parses an xncc's eom's irrep's root.
    """
    sections = []
    # The guess vector listing starts at the third line
    ln = 2
    ln = skip_to_empty_line(lines, ln)
    sections += [{
        'name': 'guess vector',
        'start': 2 + line_offset,
        'end': ln + line_offset,
        'lines': lines[2:ln],
    }]

    ln, match = skip_to_re(
        r"Beginning iterative solution of (EOMEE-CCSDT?Q?) equations",
        lines, ln
    )
    iterative_start = ln
    model = match.group(1)
    ln = skip_to(f"{model} iterations converged in" + r'\s*\d+\s*' +
                 'cycles and' + FLOAT_WS + r'seconds \(' + FLOAT_WS
                 + r's/it.\) at ' + FLOAT_WS + r'Gflops/sec', lines, ln)
    iterative_end = ln
    iterative_solution = lines[iterative_start:iterative_end+1]

    sections += [{
        'name': 'iterative solution',
        'start': iterative_start + line_offset,
        'end': iterative_end + line_offset,
        'lines': iterative_solution,
    }]

    ln += 2
    eom_exc_pattern = re.compile(f'{model}' + r' excitation energy:'
                                 + FLOAT_WS + r'\(' + FLOAT_WS + r'eV\)')
    eom_exc_match = eom_exc_pattern.match(lines[ln].strip())
    if eom_exc_match is None:
        print("Error in parsing eom roots in xncc", file=sys.stderr)
        print(f"Expected EOM excitation energies in line{line_offset + ln}",
              file=sys.stderr)

    ln += 1
    eom_total_pattern = re.compile(f'Total {model} energy:' + FLOAT_WS)
    eom_total_match = eom_total_pattern.match(lines[ln].strip())
    if eom_total_match is None:
        print("Error in parsing eom roots in xncc", file=sys.stderr)
        print(f"Expected EOM total energy in line{line_offset + ln}",
              file=sys.stderr)

    sections += [{
        'name': 'EOM energy',
        'start': ln - 1 + line_offset,
        'end': ln + line_offset,
        'lines': lines[ln - 1: ln + 1],
        'data': {
            'excitation': {
                'au': float(eom_exc_match.group(1)),
                'eV': float(eom_exc_match.group(2)),
            },
            'total': {
                'au': float(eom_total_match.group(1)),
            },
        },
    }]

    ln = skip_to("Converged root:", lines, ln)
    converged_root_start = ln
    for _ in range(3):
        ln = skip_to_empty_line(lines, ln)
        ln += 1  # go past the empty line
    converged_root_end = ln
    sections += [{
        'name': 'converged root',
        'start': converged_root_start + line_offset,
        'end': converged_root_end + line_offset,
        'lines': lines[converged_root_start:converged_root_end],
    }]

    parse_xncc_eom_root_sections(sections)

    root = {
        'name': 'eom root',
        'start': line_offset,
        'end': line_offset + len(lines),
        'lines': lines,
        'sections': sections,
        'data': {
            'model': model,
        }
    }

    return root


def parse_xncc_eom_irrep(xncc_eom, irrep_start, end_line):
    """
    Parses the EOM part of XNCC, but only a single irrep part of it.
    The irrep is parsed as a series of roots.

    `xncc_eom` is the eom section of xncc
    `start` is the {'line': number of line where the new irrep starts,
                    'match': 'Searching for (2) roots in irrep (7)' }
    `end_line` is where the next irrep starts/or where the eom section ends
    """

    no_states = int(irrep_start['match'].group(1))
    irrep_no = int(irrep_start['match'].group(2))

    # Split irrep into roots
    # Each EOM root output starts with a listing of the guess root
    irrep_start_line = irrep_start['line']
    irrep_lines = xncc_eom['lines'][irrep_start_line:end_line]

    # Watch out: EOMEE-CCSDT uses the EOMEE-CCSD guess vector!
    guess_pattern = re.compile(r'(EOMEE-CCSDT?) guess vector:')
    detected_roots = []
    for ln, line in enumerate(irrep_lines):
        guess_match = guess_pattern.match(line.strip())
        if guess_match is None:
            continue
        detected_roots += [{
            'line': ln,
        }]

    # Parse roots
    roots = []
    for n, root_start in enumerate(detected_roots):
        if n + 1 == len(detected_roots):
            end_line = len(irrep_lines)
        else:
            end_line = detected_roots[n + 1]['line']

        root_start_line = root_start['line']
        line_offset = xncc_eom['start'] + irrep_start_line + root_start_line
        roots += [parse_xncc_eom_root(irrep_lines[root_start_line:end_line],
                                      line_offset)]

    if len(roots) != no_states:
        print("Warning, not all roots of the irrep"
              f" #{irrep_no} were parsed in xncc",
              file=sys.stderr)
        print(f"Expected {no_states=} got {len(roots)=}", file=sys.stderr)

    irrep = {
        'name': 'irrep',
        'start': irrep_start_line + xncc_eom['start'],
        'end': end_line + xncc_eom['start'],
        'lines': irrep_lines,
        'sections': roots,
        'data': {
            '#': irrep_no,
            '# of roots': no_states,
        },
    }
    return irrep


def parse_xncc_eom(xncc_eom):
    """ The EOM section splits into subsections, one for each irrep """
    xncc_eom['sections'] = []
    lines = xncc_eom['lines']

    # 1. Find these subsections
    detected_irreps = []
    irrep_pattern = re.compile(r'Searching for' + INT_WS
                               + 'roots in irrep' + INT_WS)
    for ln, line in enumerate(lines):
        irrep_match = irrep_pattern.match(line.strip())
        if irrep_match is None:
            continue
        detected_irreps += [{
            'line': ln,
            'match': irrep_match,
        },]

    # Parse every irrep's subsection
    for n, irrep_start in enumerate(detected_irreps):
        if n + 1 == len(detected_irreps):
            end_line = len(lines)
        else:
            end_line = detected_irreps[n + 1]['line']

        eom_irrep_states = parse_xncc_eom_irrep(xncc_eom, irrep_start,
                                                end_line)
        xncc_eom['sections'] += [eom_irrep_states]


def parse_xncc_program(xncc):

    catches = cool_lines_in_xncc(xncc)

    # TODO: catches should be turned into sections. Each section should
    # contain the keys: name, start, end, lines, sections, data.
    # The sections should be looped over and parsed if a parser is
    # available

    cc_section = get_cc_lines_from_xncc(xncc, catches)
    parse_xncc_cc(cc_section)
    xncc['sections'] += [cc_section]

    eom_section = get_eom_lines_from_xncc(xncc, catches)
    parse_xncc_eom(eom_section)
    xncc['sections'] += [eom_section]


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for program in programs:
        if program['name'] != 'xncc':
            continue

        parse_xncc_program(program)

        if args.verbose is True:
            pretty_introduce_section(program, 1)

    if args.json is True:
        print(json.dumps(programs))


if __name__ == "__main__":
    main()
