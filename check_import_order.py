#!/usr/bin/env python

"""
Parses python files, checking the ordering of their global imports
in accordances with pep8 specifications. Prints the diff for the
suggested reorder.

See: http://legacy.python.org/dev/peps/pep-0008/#imports
"""

import argparse
from collections import defaultdict
import difflib
import os
import re
import sys


UNIQUE_SYS_PATH = [p for p in set(sys.path)]
EMPTY_OVERRIDE = {'standard': [], 'third_party': [], 'local': []}


def main():
    """Parses python files for their global import lines, calculates their
    appropriate order according to pep8 specifications and prints any
    reccommended reorder. Exits 1 if any files parsed required a reorder,
    otherwise 0.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--standard', default='', metavar='MODULE LIST',
        help='comma-separated list of modules to class as `standard/build-in`')
    parser.add_argument(
        '--third_party', default='', metavar='MODULE LIST',
        help='comma-separated list of modules to class as `third_party`')
    parser.add_argument(
        '--local', default='', metavar='MODULE LIST',
        help='comma-separated list of modules to class as `local`')
    parser.add_argument(
        'files', metavar='FILES', nargs=argparse.ONE_OR_MORE,
        help='the files whose imports are to be parsed')
    clargs = parser.parse_args()

    exit_status = 0

    def _sanitize_cmd_line_opt(cmd_line_opt):
        """Converts command option strings to a list of module names."""
        return [o.strip() for o in cmd_line_opt.split(',')]

    for py_file in clargs.files:
        if not sanity_check(py_file):
            exit_status += 1
            continue

        imports_string, import_lines = get_import_lines(py_file)
        override = {
            'standard': _sanitize_cmd_line_opt(clargs.standard),
            'third_party': _sanitize_cmd_line_opt(clargs.third_party),
            'local': _sanitize_cmd_line_opt(clargs.third_party)
        }
        import_dict = construct_import_dict(import_lines, override=override)

        ordered_imports = get_ordered_imports(import_dict)
        exit_status += verify_imports_order(
            imports_string, ordered_imports, py_file)

    sys.exit(exit_status > 0)


def construct_import_dict(import_lines, override=None):
    """Given a series of import lines, construct a dict of imports grouped
    by module type (standard, third_party or local).
    >>> construct_import_dict(['import os']).items()
    [('standard', ['import os'])]
    >>> construct_import_dict(['import os', 'import cv2']).items()
    [('third_party', ['import cv2']), ('standard', ['import os'])]
    >>> construct_import_dict(['from . import function']).items()
    [('local', ['from . import function'])]
    >>> construct_import_dict(['import os.path']).items()
    [('standard', ['import os.path'])]
    """
    final_imports = defaultdict(list)

    for import_line in import_lines:
        mod_name = get_module_name_from_import(import_line)

        if mod_name == '.':
            final_imports['local'] += [import_line]
        elif is_standard_module(mod_name, override=override):
            final_imports['standard'] += [import_line]
        elif is_third_party_module(mod_name, override=override):
            final_imports['third_party'] += [import_line]
        else:
            final_imports['local'] += [import_line]

    return final_imports


def verify_imports_order(actual, expected, filename='file'):
    r"""Line diff import lines strings, returning 0 if no diff found else 1.
    >>> ac = '\n'.join(['import os', 'import sys'])
    >>> ex = '\n'.join(['import os', 'import sys'])
    >>> assert verify_imports_order(ac, ex) == 0
    >>> ac = '\n'.join(['import os', 'import sys', '', 'import cv2'])
    >>> ex = '\n'.join(['import os', 'import sys', '', 'import cv2'])
    >>> assert verify_imports_order(ac, ex) == 0
    >>> ac = '\n'.join(['import sys', '', 'import os', 'import cv2'])
    >>> ex = '\n'.join(['import os', 'import sys', '', 'import cv2'])
    >>> assert verify_imports_order(ac, ex) == 1
    --- file
    +++ expected
    @@ -1,4 +1,4 @@
    +import os
     import sys
    <BLANKLINE>
    -import os
     import cv2
    """
    actual = [l + '\n' for l in actual.split('\n')]
    expected = [l + '\n' for l in expected.split('\n')]

    ret = 0
    for line in difflib.unified_diff(
            actual, expected, fromfile=filename, tofile='expected'):
        sys.stdout.write(line)
        ret = 1
    return ret


def get_ordered_imports(grouped_imports):
    """Given a dict of 'standard', 'third_party' and 'local' modules, return
    an ordered string of the pep8 complient import lines.
    >>> print get_ordered_imports({'standard': ['import os']})
    import os
    >>> print get_ordered_imports({'third_party': ['import cv2']})
    import cv2
    >>> print get_ordered_imports({
    ...     'local': ['import last'],
    ...     'third_party': ['import z_third_party', 'import a_third_party'],
    ...     'standard': ['import built_in']})
    import built_in
    <BLANKLINE>
    import a_third_party
    import z_third_party
    <BLANKLINE>
    import last
    """
    for key in ('standard', 'third_party', 'local'):
        if key in grouped_imports:
            grouped_imports[key] = '\n'.join(sorted(
                grouped_imports[key], key=lambda k: k.lower().split()[1]))
        else:
            grouped_imports[key] = ''

    return '\n\n'.join(
        grouped_imports[key] for key in ('standard', 'third_party', 'local')
        if grouped_imports[key] != '')


def load_module(module_name):
    """Attempts to load a module and return it, otherwise returns None."""
    module = None
    try:
        module = __import__(module_name)
    except ImportError:
        print "Cannot import '%s'." % module_name
    return module


def is_standard_module(module, override=None):
    """Checks if a given `module` is a standard/built-in module.
    >>> is_standard_module('os')
    True
    >>> is_standard_module('sys')
    True
    >>> is_standard_module('cv2')
    False
    """
    if override is None:
        override = EMPTY_OVERRIDE

    if module in override['standard']:
        return True
    elif module in override['third_party'] or module in override['local']:
        return False

    module_ = load_module(module)
    if module_ is None:
        return False

    module_repr = module_.__repr__()
    return (
        (not 'site-packages' in module_repr) and
        any([path in module_repr
            for path in ('usr/lib/python', 'usr/lib64/python', 'built-in')]))


def is_third_party_module(module, override=None):
    """Checks if given `module` is third party.
    >>> is_third_party_module('cv2')
    True
    >>> is_third_party_module('sys')
    False
    """
    if override is None:
        override = EMPTY_OVERRIDE

    if module in override['third_party']:
        return True
    elif module in override['standard'] or module in override['local']:
        return False

    module_ = load_module(module)
    if module_ is None:
        return False

    module_repr = module_.__repr__()
    return (
        ('site-packages' in module_repr) and
        any([path in module_repr
            for path in ('usr/lib/python', 'usr/lib64/python')]))


def get_import_lines(py_file):
    """Returns raw string and a list of 'import' or 'from * import' lines
    from a file."""
    with open(py_file, 'r') as f_in:
        import_list = []
        sub_list = []
        for line in f_in.readlines():
            if (
                line.startswith('import') or
                line.startswith('from') and not
                line.startswith('from __future__')
            ):
                import_list += sub_list
                sub_list = []
                import_list.append(line.strip())
            elif line == '\n' and import_list:
                sub_list.append('')

    return '\n'.join(import_list), [i for i in import_list if i != '']


def get_module_name_from_import(imprt_line):
    """Returns the name of the module from an 'import' line.
    >>> get_module_name_from_import('import argparse')
    'argparse'
    >>> get_module_name_from_import('from collections import defaultdict')
    'collections'
    >>> get_module_name_from_import('from . import function')
    '.'
    >>> get_module_name_from_import('import module.submodule')
    'module.submodule'
    """
    match = re.search(
        r'^(from|import) (?P<module>[A-Za-z_0-9\.]+).*$', imprt_line)
    if match:
        return match.groupdict()['module']
    else:
        raise ValueError("Couldn't get module name from '%s'." % imprt_line)


def sanity_check(py_file):
    """Check that given file exists."""
    if not os.path.isfile(py_file):
        sys.stderr.write("File '%s' doesn't exist.\n" % py_file)
    return os.path.isfile(py_file)

if __name__ == '__main__':
    main()
