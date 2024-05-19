#!/usr/bin/env python3

import argparse
import sys
import json
import re
from cfour_parser.util import skip_to
from cfour_parser.programs import find_programs
from cfour_parser.text import pretty_introduce_section


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
        {'pattern': re.compile(r'\s*Normal Coordinates'),
         'name': 'normal coordinates',
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


def xjoda_catch2sec_control_pars(catch, lines, start_offset):
    """
    Turn catch 'control parameters' of xjoda into a section template.
    """
    oll_korrect = True
    THE_LINE = '-' * 67
    start = catch['line']
    if lines[start-1] != lines[start+1] != lines[start+4] != THE_LINE:
        oll_korrect = False
        print(f"Error in parsing the '{catch['name']}' section of xjoda",
              file=sys.stderr)

    end = skip_to(THE_LINE, lines, start+5)

    cp = {
            'name': catch['name'],
            'start': start_offset + start - 1,
            'end': start_offset + end,
            'lines': lines[start-1: end+1],
            'sections': list(),
            'metadata': {
                'ok': oll_korrect,
                },
            'data': dict(),
            }

    return cp


def xjoda_catch2sec_qcomp(catch, lines, start_offset):
    oll_korrect = True
    THE_LINE = '-' * 64
    start = catch['line']
    if lines[start-1] != lines[start+1] != lines[start+4] != THE_LINE:
        oll_korrect = False
        print(f"Error in parsing the '{catch['name']}' section of xjoda.",
              file=sys.stderr)

    end = skip_to(THE_LINE, lines, start+5)

    qcomp = {
        'name': catch['name'],
        'start': start_offset + start - 1,
        'end': start_offset + end,
        'lines': lines[start-1: end+1],
        'sections': list(),
        'metadata': {
            'ok': oll_korrect,
        },
        'data': dict(),
    }

    return qcomp


def xjoda_catch2sec_normal_coordinate_gradient(catch, lines, start_offset):
    oll_korrect = True
    THE_LINE = '-' * 71
    start = catch['line']
    if lines[start+1] != lines[start+4] != THE_LINE:
        oll_korrect = False
        print(f"Error in parsing the {catch['name']} section of xjoda.",
              file=sys.stderr)

    end = skip_to(THE_LINE, lines, start+5)

    gradient = {
        'name': catch['name'],
        'start': start_offset + start,
        'end': start_offset + end,
        'lines': lines[start: end+1],
        'sections': list(),
        'metadata': {
            'ok': oll_korrect,
        },
        'data': dict(),
    }

    return gradient


def xjoda_catch2sec_normal_coordinates(catch, lines, start_offset):
    oll_korrect = True
    THE_LINE = '-' * 74
    start = catch['line']
    end = skip_to(THE_LINE, lines, start)

    section = {
        'name': catch['name'],
        'start': start_offset + start,
        'end': start_offset + end,
        'lines': lines[start: end+1],
        'sections': list(),
        'metadata': {
            'ok': oll_korrect,
        },
        'data': dict(),
    }

    return section


def turn_xjoda_catches_into_sections(catches, xjoda):
    """
    The main job of functions in this funcion is to find the end line of each
    section. Additionally, the funcitons in this function can do some error
    checking.
    """
    lines = xjoda['lines']
    start_offset = xjoda['start']
    turners = {
        'control parameters': xjoda_catch2sec_control_pars,
        'qcomp': xjoda_catch2sec_qcomp,
        'normal coordinate gradient': xjoda_catch2sec_normal_coordinate_gradient,
        'normal coordinates': xjoda_catch2sec_normal_coordinates,
    }

    for catch in catches:
        if catch['name'] in turners:
            turner = turners[catch['name']]
            section = turner(catch, lines, start_offset)
            xjoda['sections'] += [section]


def parse_control_parameters(section):
    """
    Parser of the "Control Parameters" section of xjoda.

    Example lines:
BOX_POTENT           IPIAB          OFF         [  0]    ***
BREIT                IBREIT         OFF         [  0]    ***
BRUCK_CONV           IBRTOL          10D-  4             ***
BRUECKNER            IBRKNR         OFF         [  0]    ***
BUFFERSIZE           IBUFFS              4096            ***
CACHE_RECS           ICHREC             10               ***

    """
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
    section['data'].update(data)


def parse_qcomp(section):
    """
    Parser of the "QCOMP" section of xjoda.

    Example of the "QCOMP" section:
```
 ----------------------------------------------------------------
         Coordinates used in calculation (QCOMP) 
 ----------------------------------------------------------------
 Z-matrix   Atomic            Coordinates (in bohr)
  Symbol    Number           X              Y              Z
 ----------------------------------------------------------------
     X         0        -0.00000000    -1.88972729    -3.33567616
     X         0        -0.00000000     0.00000000    -3.33567616
     C         6        -0.00000000     0.00000000    -0.63076502
     C         6         2.29166702     0.00000000    -2.00037448
     C         6         2.28377565     0.00000000    -4.64994320
     C         6         0.00000000     0.00000000    -6.00133672
     X         0        -0.00000000     1.88972729    -3.33567616
     C         6        -2.29166702     0.00000000    -2.00037448
     C         6        -2.28377565     0.00000000    -4.64994320
     O         8        -0.00000000     0.00000000     1.89970059
     CA       20        -0.00000000    -0.00000000     5.76233465
     H         1         4.07179557     0.00000000    -0.95103406
     H         1         4.08301453     0.00000000    -5.66810960
     H         1         0.00000000     0.00000000    -8.06553342
     H         1        -4.07179557     0.00000000    -0.95103406
     H         1        -4.08301453     0.00000000    -5.66810960
 ----------------------------------------------------------------
```
    """
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

    section['data'].update(data)


def parse_normal_coordinate_gradient(section):
    """
    TODO: add an example of the "Normal coordinate gradient" section.
    """
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


def parse_normal_coordinates(section):
    """
    Example of the "Normal Coordinates" section
```
                                   Normal Coordinates

                B1                        B2                        B2
                65.70                     77.11                    253.59
             VIBRATION                 VIBRATION                 VIBRATION
 C      0.293-0.0000 -0.0000    0.0000  0.3498 -0.0000    0.0000  0.0865  0.0000
 C      0.168-0.0000 -0.2056    0.0000  0.2157 -0.0000   -0.0000  0.4059 -0.0000
 C     -0.081 0.0000 -0.2073   -0.0000 -0.1495 -0.0000   -0.0000  0.0372 -0.0000
 C     -0.204 0.0000 -0.0000   -0.0000 -0.3603 -0.0000   -0.0000 -0.3745 -0.0000
 C      0.168-0.0000  0.2056    0.0000  0.2157  0.0000   -0.0000  0.4059  0.0000
 C     -0.081 0.0000  0.2073   -0.0000 -0.1495  0.0000   -0.0000  0.0372  0.0000
 O      0.561-0.0000 -0.0000    0.0000  0.5995 -0.0000    0.0000 -0.6370  0.0000
 CA    -0.489 0.0000 -0.0000   -0.0000 -0.4226 -0.0000    0.0000  0.0649 -0.0000
 H      0.076-0.0000 -0.1070    0.0000  0.1041 -0.0000    0.0000  0.1558 -0.0000
 H     -0.051 0.0000 -0.1087   -0.0000 -0.0819 -0.0000   -0.0000  0.0007 -0.0000
 H     -0.113 0.0000 -0.0000   -0.0000 -0.1924 -0.0000   -0.0000 -0.2481 -0.0000
 H      0.076-0.0000  0.1070    0.0000  0.1041  0.0000    0.0000  0.1558  0.0000
 H     -0.051 0.0000  0.1087   -0.0000 -0.0819  0.0000   -0.0000  0.0007  0.0000

                A1                        A2                        B1
               307.13                    419.49                    448.53
             VIBRATION                 VIBRATION                 VIBRATION
 C      0.000 0.0000  0.0585    0.0000  0.0000  0.0000    0.3231  0.0000 -0.0000
 C      0.056 0.0000  0.2250    0.0000  0.4312  0.0000    0.3381 -0.0000 -0.0545
 C      0.045 0.0000  0.2577   -0.0000 -0.4239 -0.0000   -0.0551  0.0000 -0.1377
 C     -0.000 0.0000  0.3294   -0.0000  0.0000  0.0000   -0.1374  0.0000 -0.0000
 C     -0.056 0.0000  0.2250    0.0000 -0.4312 -0.0000    0.3381  0.0000  0.0545
 C     -0.045 0.0000  0.2577   -0.0000  0.4239  0.0000   -0.0551 -0.0000  0.1377
 O     -0.000-0.0000 -0.0390   -0.0000  0.0000  0.0000   -0.7083 -0.0000 -0.0000
 CA     0.000 0.0000 -0.7802   -0.0000 -0.0000  0.0000    0.0158  0.0000  0.0000
 H     -0.001-0.0000  0.0941    0.0000  0.2509 -0.0000    0.1495 -0.0000 -0.1008
 H      0.002-0.0000  0.0573   -0.0000 -0.2672 -0.0000   -0.0508 -0.0000 -0.1032
 H     -0.000-0.0000  0.0956   -0.0000 -0.0000  0.0000   -0.0687 -0.0000 -0.0000
 H      0.001-0.0000  0.0941    0.0000 -0.2509 -0.0000    0.1495  0.0000  0.1008
 H     -0.002-0.0000  0.0573   -0.0000  0.2672  0.0000   -0.0508 -0.0000  0.1032

...

                A1                        B1                        A1
              3201.18                   3204.27                   3219.44
             VIBRATION                 VIBRATION                 VIBRATION
 C     -0.000 0.0000  0.0161    0.0121 -0.0000  0.0000   -0.0000  0.0000  0.0064
 C      0.147-0.0000  0.0850   -0.1328  0.0000 -0.0843    0.0503  0.0000  0.0354
 C      0.043 0.0000 -0.0379   -0.1171 -0.0000  0.0741    0.1081  0.0000 -0.0532
 C     -0.000 0.0000  0.1402    0.0122  0.0000  0.0000   -0.0000 -0.0000 -0.2330
 C     -0.147 0.0000  0.0850   -0.1328  0.0000  0.0843   -0.0503 -0.0000  0.0354
 C     -0.043-0.0000 -0.0379   -0.1171  0.0000 -0.0741   -0.1081 -0.0000 -0.0532
 O      0.000-0.0000 -0.0044   -0.0004  0.0000 -0.0000   -0.0000 -0.0000 -0.0020
 CA     0.000 0.0000  0.0001   -0.0001 -0.0000  0.0000    0.0000  0.0000  0.0002
 H     -0.482 0.0000 -0.2810    0.4378 -0.0000  0.2579   -0.1654  0.0000 -0.0986
 H     -0.158 0.0000  0.0937    0.3859  0.0000 -0.2210   -0.3246 -0.0000  0.1808
 H      0.000-0.0000 -0.4731   -0.0041 -0.0000 -0.0000    0.0000  0.0000  0.7475
 H      0.482-0.0000 -0.2810    0.4378  0.0000 -0.2579    0.1654  0.0000 -0.0986
 H      0.158-0.0000  0.0937    0.3859 -0.0000  0.2210    0.3246  0.0000  0.1808
--------------------------------------------------------------------------
```
    """
    # slice by empty lines
    lines = section['lines'][2:-1]

    slices = []
    slice = []
    for line in lines:
        if line.strip() == "":
            slices += [slice]
            slice = []
        else:
            slice += [line]
    # Add the last slice
    slices += [slice]

    normal_coordinates = []
    for slice in slices:
        mode_symm = slice[0].split()
        mode_freq = [float(omega) for omega in slice[1].split()]
        mode_kind = slice[2].split()

        new_modes = []
        for symm, freq, kind in zip(mode_symm, mode_freq, mode_kind):
            new_modes += [{
                'symmetry': symm,
                'frequency, cm-1': freq,
                'kind': kind,
                'coordinate': [],
            }]

        for line in slice[3:]:
            atomic_symbol = line[0:7].strip()
            # CFOUR does not know to to print
            coordinates = line[7:13] + " " + line[13:]
            coordinates = [float(xyz) for xyz in coordinates.split()]
            for id, mode in enumerate(new_modes):
                mode['coordinate'] += [{
                    'atomic symbol': atomic_symbol,
                    'x': coordinates[3*id + 0],
                    'y': coordinates[3*id + 1],
                    'z': coordinates[3*id + 2],
                }]

        normal_coordinates += new_modes

    section['data'].update({
        'normal coordinates': normal_coordinates,
        })


def parse_xjoda_sections(xjoda):
    parsers = {
        'control parameters': parse_control_parameters,
        'qcomp': parse_qcomp,
        'normal coordinate gradient': parse_normal_coordinate_gradient,
        'normal coordinates': parse_normal_coordinates,
    }
    for section in xjoda['sections']:
        name = section['name']
        if name in parsers:
            parse = parsers[name]
            parse(section)


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
