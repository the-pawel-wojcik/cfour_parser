#!/usr/bin/env python3

import argparse
import json
import re
from cfour_parser.util import skip_to_re
from cfour_parser.programs import find_programs
from cfour_parser.text import INT_WS, FLOAT, pretty_introduce_section, print_section


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_output', help='CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true')
    parser.add_argument('-v', '--verbose', default=0, action='count')
    args = parser.parse_args()
    return args


def parse_xvee_program(xvee):
    """
    Parser of the xvee program.
    """
    catches = cool_lines_in_xvee(xvee)
    turn_xvee_catches_into_sections(catches, xvee)


def cool_lines_in_xvee(xvee):
    """
    The lines I would look for while reading the CFOUR's output file.
    """

    if xvee['name'] != 'xvee':
        return

    # HINT: section commented out do not have parsers yet
    highlights = [
        # {'re': r'\s*Summary of active alpha molecular orbitals:',
        #  'name': 'MO listing',
        #  'type': 'start',
        #  },
        # {'re': r'\s*EOMEE-CCSD excitation energies will be evaluated\.',
        #  'name': 'model',
        #  'type': 'oneline',
        #  },
        # {'re': r'\s*Guess vectors transform as symmetry 5\.',
        #  'name': 'irrep symmetry',
        #  'type': 'oneline',
        #  },
        {'re': r'\s*Beginning symmetry block' + INT_WS + r'\.' + INT_WS +
         r'roots requested.',
         'name': 'eom solution',
         'type': 'start',
         },
        # {'re':
        #  r'\s*@TDENS-I, Largest elements of the\s*(\w+)\s*transition density',
        #  'name': 'transition density',
        #  'type': 'start',
        #  },
        {'re': r'\s*Right Transition Moment' + (r'\s+' + FLOAT) * 3,
         'name': 'transition properties',
         'type': 'start',  # this is also an end to the 'eom solution' block
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


def turn_xvee_catches_into_sections(catches, xvee):
    """
    Catches are turned into sections.

    Each section contains the keys: name, start, end, metadata, sections, data
    """
    xvee_section_parsers = {
        # 'MO listing': #TODO,
        'eom solution': parse_xvee_eom_root,
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
            section = parser(catch, xvee)
            xvee['sections'] += [section]


def parse_xvee_eom_root_lines_helper(catch, xvee):
    """
    Finds the 'end' of the 'section' (TODO:) and produces a draft of
    a container for the data 'section'.
    TODO: most of data should be extracted in the next function, this should
    just slice the section

    The catch finds the line:
      Beginning symmetry block   (int).   (int) roots requested.
    """
    catch_line = catch['line']
    lines = xvee['lines']

    data = {}
    data['irrep'] = {
        '#': int(catch['match'].group(1)),
    }
    data['# roots'] = int(catch['match'].group(2))

    # TODO: this is not the end of the section -- it is folled by:
    # - a listing of the converged eigenvector
    # - converged eigenvector normalized to one
    # - info line: Eigenvector is saved on CCRE_4_1
    # Optionally there are also printed:
    # - normalization factor for lhs wavefunction (float)
    # - Largest elements of the (LEFT|RIGHT) transition density
    # - There are also the @SOMENAME lines with a grabage in between e.g.:
    # @RNORM-I, Processing right-hand wavefunction.
    # z is   0.99999999999996825
    # danish F
    # @TDENS-I, Largest elements of the RIGHT transition density
    #
    # It's hard to understand the underlying structure of the whole section.
    eom_end = r'Total (EOMEE-CCSD) electronic energy\s+' + FLOAT + r' a\.u\.'
    ln = catch_line
    last_line, match = skip_to_re(eom_end, lines, ln)
    data['model'] = match.group(1)
    data['energy'] = {
        'total': {
            'au': float(match.group(2)),
        },
    }

    section = {
        'name': catch['name'],
        'start': xvee['start'] + catch_line,
        'end': xvee['start'] + last_line,
        'sections': list(),
        'lines': lines[catch_line:last_line+1],
        'metadata': {
            'ok': True,
        },
        'data': data,
    }

    return section


def parse_xvee_eom_root(catch, xvee):
    """
    TODO: work in progress
    """

    # end = r'Eigenvector is saved on (CC[RL]E_\d_\d)'
    # ln = skip_to(eom_end, xvee['lines'], )
    section = parse_xvee_eom_root_lines_helper(catch, xvee)
    # TODO: if the xvee ever gets well divided into subsections, this is where
    # these subsections are parsed
    return section


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
        'model': total_energy_match.group(1),
        'Right TDM': right_tdm,
        'Left TDM': left_tdm,
        'Dipole strength': dipole_strength,
        'Oscillator strength': oscillator_strength,
        'Norm of oscillator strength': f,
        'energy': energy,
    }

    return section


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
