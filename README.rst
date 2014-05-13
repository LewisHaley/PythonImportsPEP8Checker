========================
PythonImportsPEP8Checker
========================

--------------------------------------------------------------------------
Check Python scripts for `import` order with respect to the PEP8 standard.
--------------------------------------------------------------------------

:Copyright: Copyright (C) 2014 Lewis Haley
:Licence: GPL v3.0 or (at your option) any later version (see LICENSE file in
         the source distrubtion for details)
:Version: 0.1

SYNOPSIS
========

Parses Python scripts looking at their global `import` lines. Upon calculating
the appropriate PEP8 compliant order for these imports, the script will report
back to the user, in the form of a line diff, if the currect state of the
imports requires changing for compliance.

DESCRIPTION
===========

PEP8 states that the order of global imports in a python file should adhere to
this format::

    Imports should be grouped in the following order:
        1. standard library imports
        2. related third party imports
        3. local application/library specific imports

See the pep8_ specification for more details. The `check_import_order.py`
script attempts to categorise global imports (module-level `import` lines)
into the three categories of `standard`, `third_party` and `local`.

.. _pep8: http://legacy.python.org/dev/peps/pep-0008/#imports

OPTIONS
=======

For various reasons, it is sometimes desirable to give explicit instructions
on which category to group a module with. For example, you may have locally
build/installed third party module, which because it hasn't been installed
"traditionally", e.g., with a package manager, isn't located in the same
directory as other third party modules, and so on and so forth.

To this end, there are command line options to `check_import_order.py` which
allow the user to specify which category a module should be grouped in. This
is invoked on the command line as such:::

    check_import_order.py --system=os,datetime my_script.py
    check_import_order.py --system="os, datetime" my_script.py

Note that the module names are comma-separated and any leading or trailing
whitespace is stripped.

If the script finds that the imports are already in the correct order, it will
return success (`exit(0)`), otherwise the suggested diff is printed and the
script will return failure (`exit(1)`). Multiple scripts can be given on the
command line, each being parsed in turn with the same overrides as specified.
In such cases, if any script was found to have incorrectly ordered imports,
`check_import_order.py` will exit failure.
