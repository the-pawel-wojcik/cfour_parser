#!/usr/bin/env python3

import argparse
import sys
import json
import re
from parsers.text import INT_WS, FLOAT
from parsers.util import skip_to
from parsers.programs import find_programs
from parsers.text import pretty_introduce_section, print_section


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=0, action='count')
    args = parser.parse_args()
    return args


def cool_lines_in_xvee(xvee):
    """
    The lines I would look for while reading the CFOUR's output file.
    """

    if xvee['name'] != 'xvee':
        return

    highlights = [
        {'re': r'\s*Summary of active alpha molecular orbitals:',
         'name': 'MO listing',
         'type': 'start',
         },
        {'re': r'\s*EOMEE-CCSD excitation energies will be evaluated\.',
         'name': 'eom model',
         'type': 'oneline',
         },
        {'re': r'\s*Guess vectors transform as symmetry 5\.',
         'name': 'irrep symmetry',
         'type': 'oneline',
         },
        {'re': r'\s*Beginning symmetry block' + INT_WS + r'\.' + INT_WS +
         r'roots requested.',
         'name': 'eom solution',
         'type': 'start',
         },
        {'re':
         r'\s*@TDENS-I, Largest elements of the\s*(\w+)\s*transition density',
         'name': 'transition density',
         'type': 'start',
         },
        {'re': r'\s*Right Transition Moment' + (r'\s+' + FLOAT) * 3,
         'name': 'transition properties',
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
    for ln, line in enumerate(xvee['lines']):
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


def parse_xvee_transition_properties(catch, xvee):
    catch_line = catch['line']
    lines = xvee['lines']

    right_tdm_match = catch['match']
    right_tdm = {
        'x': float(right_tdm_match.group(1)),
        'y': float(right_tdm_match.group(2)),
        'z': float(right_tdm_match.group(3)),
    }

    left_tdm_pattern = re.compile(
        r'\s*Left Transition Moment' + (r'\s+' + FLOAT) * 3)
    left_tdm_match = left_tdm_pattern.match(lines[catch_line + 1])
    if left_tdm_match is None:
        raise RuntimeError(f"line {xvee['start'] + catch_line + 1}:"
                           "Failed to parse left tdm in xvee.")
    left_tdm = {
        'x': float(left_tdm_match.group(1)),
        'y': float(left_tdm_match.group(2)),
        'z': float(left_tdm_match.group(3)),
    }

    dipole_strength_pattern = re.compile(
        r'\s*Dipole Strength' + (r'\s+' + FLOAT) * 3)
    dipole_strength_match = dipole_strength_pattern.match(lines[catch_line+2])
    if dipole_strength_match is None:
        raise RuntimeError(f"line {xvee['start'] + catch_line + 2}:"
                           "Failed to parse dipole strength in xvee.")
    dipole_strength = {
        'x': float(dipole_strength_match.group(1)),
        'y': float(dipole_strength_match.group(2)),
        'z': float(dipole_strength_match.group(3)),
    }

    oscillator_line = catch_line + 3
    oscillator_strength_pattern = re.compile(
        r'\s*Oscillator Strength' + (r'\s+' + FLOAT) * 3)
    oscillator_strength_match = oscillator_strength_pattern.match(
        lines[oscillator_line])
    if oscillator_strength_match is None:
        raise RuntimeError(f"line {xvee['start'] + oscillator_line}:"
                           "Failed to parse oscillator strength in xvee.")
    oscillator_strength = {
        'x': float(oscillator_strength_match.group(1)),
        'y': float(oscillator_strength_match.group(2)),
        'z': float(oscillator_strength_match.group(3)),
        'line': oscillator_line,
    }

    transition_energy_line = catch_line + 5
    transition_energy_pattern = re.compile(
        r'\s*Transition energy' + r'\s+' + FLOAT + r' eV\s+\(\s+' + FLOAT +
        r'\s+nm;\s+' + FLOAT + r'\s+cm-1\)')
    transition_energy_match = transition_energy_pattern.match(
        lines[transition_energy_line])
    if transition_energy_match is None:
        raise RuntimeError(f"line {xvee['start'] + transition_energy_line}:"
                           "Failed to parse transition energy in xvee.")
    energy = {'transition':
              {'eV': float(transition_energy_match.group(1)),
               'nm': float(transition_energy_match.group(2)),
               'cm-1': float(transition_energy_match.group(3)),
               }
              }

    total_energy_line = catch_line + 6
    total_energy_pattern = re.compile(
        r'\s*Total\s+(EOM..-CCSDT?)\s+electronic energy\s+' +
        FLOAT + r'\s+a\.u\.')
    total_energy_match = total_energy_pattern.match(lines[total_energy_line])
    if total_energy_match is None:
        raise RuntimeError(f"line {xvee['start'] + total_energy_line}:"
                           "Failed to parse total energy in xvee.")
    energy['total'] = {
        'au': float(total_energy_match.group(2)),
    }

    f_line = catch_line + 7
    f_pattern = re.compile(r'\s+Norm of oscillator strength :\s+' + FLOAT)
    f_match = f_pattern.match(lines[f_line])
    if f_match is None:
        raise RuntimeError(f"line {xvee['start'] + f_line}:"
                           "Failed to parse norm of oscillator strength in "
                           "xvee.")
    f = float(f_match.group(1))

    section = {
        'name': catch['name'],
        'start': xvee['start'] + catch_line,
        'end': xvee['start'] + f_line,
        'sections': list(),
        'lines': lines[catch_line:f_line+1],
        'metadata': {
            'ok': True,
        },
    }

    section['data'] = {
        'eom model': total_energy_match.group(1),
        'right tdm': right_tdm,
        'left tdm': left_tdm,
        'dipole strength': dipole_strength,
        'oscillator strength': oscillator_strength,
        'norm of oscillator strength': f,
        'energy': energy,
    }

    xvee['sections'] += [section]
    return


def turn_xvee_catches_into_sections(catches, xvee):
    """
    Catches are turned into sections.

    Each section contains the keys: name, start, end, metadata, sections, data
    """
    xvee_section_parsers = {
        # 'MO listing': #TODO,
        'transition properties': parse_xvee_transition_properties,
    }
    for catch in catches:
        section_name = catch['name']
        if section_name in xvee_section_parsers:
            parser = xvee_section_parsers[section_name]
            # cp = {
            #     'name': section_name,
            #     'start': xvee['start'] + start - 1,
            #     'end': xvee['start'] + end,
            #     'lines': lines[start-1: end+1],
            #     'sections': list(),
            #     'data': dict(),
            #     'metadata': dict(),
            # }
            parser(catch, xvee)


def parse_xvee_program(xvee):
    """
    Parser of the xvee program.
    """
    catches = cool_lines_in_xvee(xvee)
    turn_xvee_catches_into_sections(catches, xvee)


def main():
    args = get_args()
    with open(args.cfour_output, 'r') as cfour_output:
        programs = find_programs(cfour_output)

    for xvee in programs:
        if xvee['name'] != 'xvee':
            continue

        parse_xvee_program(xvee)

        if args.verbose > 0:
            pretty_introduce_section(xvee, 1)
            if args.verbose > 1:
                for section in xvee['sections']:
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
