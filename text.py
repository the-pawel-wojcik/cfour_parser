"""
A collection of helper functions.
"""

# regular expression for matching floats
FLOAT = r'([+-]?\d+\.\d+)'
INT = r'([+-]?\d+)'

FLOAT_WS = r'\s*([+-]?\d+\.\d+)\s*'
INT_WS = r'\s*([+-]?\d+)\s*'

FRTRN_FLOAT = r'([+-]?\d+\.\d+D-?\d+)'


def str_eom_state(state):
    """
    Return a string.
    """
    pretty = f"{state['#']:2d}: {state['model']} state "
    pretty += f"in irrep #{state['irrep']['#']} "
    if 'energy #' in state['irrep'].keys() and 'name' in state['irrep'].keys():
        pretty += "("
        if state['irrep']['energy #'] > 1:
            pretty += f"{state['irrep']['energy #']}"
        pretty += f"{state['irrep']['name']}) "
    elif 'name' in state['irrep'].keys():
        pretty += f"({state['irrep']['name']}) "

    if 'transition' in state['energy'].keys():
        energy = state['energy']['transition']['eV']
        pretty += f"of transition energy {energy:.3f} eV."
    else:
        energy = state['energy']['total']['au']
        pretty += f"with total energy {energy:-10.5f} au."

    return pretty


def pretty_introduce_section(section, level: int = 0):
    """
    A common storage data type I use is a section.
    It is a dictionary with keys:
        'name'
        'start'
        'end'
        'lines'
        'sections'
        'data'
    """
    introduction = f"{section['start']:4d} - {section['end']:4d}: "
    introduction += f"{section['name']}"
    if level > 0:
        if 'sections' in section.keys():
            introduction += " =>"
            for subsec in section['sections']:
                introduction += f" {subsec['name']},"
            introduction = introduction[:-1]

        if 'data' in section.keys():
            introduction += " => "
            for data in section['data']:
                if type(data) is dict:
                    if 'name' in data.keys():
                        introduction += f" {data['name']}"
                    else:
                        introduction += f" {data=}"
                else:
                    introduction += f" {data=}"

    print(introduction)


def print_section(section):
    """ Prints section to the standard output. """
    print(f"\nPrinting section: {section['name']}\n")
    start = section['start']
    for ln, line in enumerate(section['lines']):
        print(f"{start + ln:6d}: {line[:-1]}")
