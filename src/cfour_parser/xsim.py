#!/usr/bin/env python3

import argparse
import json
import sys


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('xsim_output', help="xsim's output.")
    parser.add_argument('-j', '--json', default=False, action='store_true',
                        help='Print colleted data in JSON.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    args = parser.parse_args()
    return args


def extract_raw_xsim_spectrum(lines):
    spectrum_delimiters = []
    for line_n, line in enumerate(lines):
        if "-" * 72 + "\n" == line:
            spectrum_delimiters += [line_n]

    if len(spectrum_delimiters) != 3:
        print("Error. Not exactly three delimiting lines.")
        sys.exit(1)

    return lines[spectrum_delimiters[1] + 1: spectrum_delimiters[2] - 1]


def extract_input_file(lines):
    START = "Input file used for run reproduced below"
    AFTER_END = "Dataset number"
    start_line = None
    end_line = None
    for line_n, line in enumerate(lines):

        if start_line is None and line.strip() == START:
            start_line = line_n
            continue

        if start_line is not None and line.strip().startswith(AFTER_END):
            end_line = line_n - 1
            break

    if start_line is None or end_line is None:
        print("Error parsing xsim. Input file not detected")
        sys.exit(1)

    return lines[start_line + 1: end_line]


def extract_xsim_line_under(lines, focus):
    """
    Extract the data under the line "focus"
    """
    focus_line = -1
    for n, line in enumerate(lines):
        if line.startswith(focus):
            focus_line = n+1
            break

    if focus_line == -1:
        print(f"Error: did not find '{focus}' in the xsim output.")
        return None

    return lines[focus_line].strip()


def parse_raw_xsim_spectrum(raw_spectrum):
    spectrum = []
    for raw_line in raw_spectrum:
        line_floats = raw_line.split()
        if line_floats[-1] == '********':
            print("Warning: xsim's relative intensity out of bound for line:\n"
                  f"{raw_line}\n", file=sys.stderr)
            line_floats[-1] = 10

        split_line = [float(value) for value in line_floats]
        line = {'Energy (eV)': split_line[0],
                'Energy (cm-1)': split_line[1],
                'Offset (cm-1)': split_line[2],
                'Relative intensity': split_line[3]}
        spectrum += [line]

    return spectrum


def extract_xsim_basis_functions(lines):
    basis_line = -1
    for n, line in enumerate(lines):
        if line.startswith("Basis Functions"):
            basis_line = n+1
            break

    if basis_line == -1:
        print("Error: did not find 'Basis Functions' in the xsim output.")
        return None

    basis = lines[basis_line].strip()
    return basis


def parse_xsim_output(xsim_file):
    """
    Returns a dictionary.

    The 'spectrum_data' entry is a list. Each item of the list looks like this
    {
        'Energy (eV)': float,
        'Energy (cm-1)': float,
        'Offset (cm-1)': float,
        'Relative intensity': float,
    }
    """

    lines = xsim_file.readlines()

    input_file = extract_input_file(lines)

    basis = extract_xsim_line_under(input_file, "Basis Functions")
    lanczos = extract_xsim_line_under(input_file, "Lanczos")

    raw_xsim_spectrum = extract_raw_xsim_spectrum(lines)
    spectrum_data = parse_raw_xsim_spectrum(raw_xsim_spectrum)

    xsim_data = {
        "spectrum_data": spectrum_data,
        "input_file": input_file,
        "basis": basis,
        "Lanczos": lanczos,
    }

    return xsim_data


def main():
    args = get_args()
    with open(args.xsim_output, 'r') as xsim_output:
        xsim_data = parse_xsim_output(xsim_output)

    if args.verbose is True:
        print(xsim_data)

    if args.json is True:
        print(json.dumps(xsim_data))


if __name__ == "__main__":
    main()
