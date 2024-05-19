import re
import sys


def skip_to(what: str, lines, ln: int):
    """ Skip to the line that matches `what`.
    Returns `ln`.
    """
    pattern = re.compile(what)
    while True:
        match = pattern.match(lines[ln].strip())
        if match is not None:
            break
        ln += 1
        if ln >= len(lines):
            raise RuntimeError(f"Error in parsing. Did not find:\n{what}")

    return ln


def skip_to_re(what: str, lines, ln: int):
    """ Skip to the line that matches `what`.
    Returns `ln`.
    """
    pattern = re.compile(what)
    while True:
        match = pattern.match(lines[ln].strip())
        if match is not None:
            break
        ln += 1
        if ln >= len(lines):
            raise RuntimeError(f"Error in parsing. Did not find:\n{what}")

    return ln, match


def skip_to_empty_line(lines, ln: int):
    """ Skips to an empty line """
    while True:
        if lines[ln].strip() == "":
            break
        ln += 1
        if ln >= len(lines):
            print("Error in parsing eom roots in xncc", file=sys.stderr)
            print("Did not find an empty line", file=sys.stderr)
            break

    return ln


def fortran_float_to_float(frtr: str):
    return float(frtr.replace('D', 'e'))


class ParsingError(Exception):
    pass
