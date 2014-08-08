# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import json
import pprint
import re
import tarfile
from argparse import RawDescriptionHelpFormatter
from locale import getpreferredencoding
from os.path import abspath, expanduser, split, join, exists
from os import makedirs

from conda.compat import PY3
from conda.cli.main import args_func

from conda_build.convert import (has_cext, tar_update, get_pure_py_file_map,
                                 has_nonpy_entry_points)


epilog = """

For now, it is just a tool to convert pure Python packages to other platforms.

Packages are automatically organized in subdirectories according to platform,
e.g.,

osx-64/
  package-1.0-py33.tar.bz2
win-32/
  package-1.0-py33.tar.bz2

Examples:

Convert a package built with conda build to Windows 64-bit, and place the
resulting package in the current directory (supposing a default Anaconda
install on Mac OS X):

$ conda convert ~/anaconda/conda-bld/osx-64/package-1.0-py33.tar.bz2 -o . -p win-64
"""


def main():
    p = argparse.ArgumentParser(
        description='various tools to convert conda packages',
        epilog=epilog,
        formatter_class=RawDescriptionHelpFormatter,
    )

    # TODO: Factor this into a subcommand, since it's python package specific
    p.add_argument(
        'package_files',
        metavar='package-files',
        action="store",
        nargs='+',
        help="package files to convert"
    )
    p.add_argument(
        '-p', "--platform",
        dest='platforms',
        action="append",
        choices=['osx-64', 'linux-32', 'linux-64', 'win-32', 'win-64', 'all'],
        required=True,
        help="Platform to convert the packages to"
    )
    p.add_argument(
        '--show-imports',
        action='store_true',
        default=False,
        help="Show Python imports for compiled parts of the package",
    )
    p.add_argument(
        '-f', "--force",
        action="store_true",
        help="Force convert, even when a package has compiled C extensions",
    )
    p.add_argument(
        '-o', '--output-dir',
        default='.',
        help="""Directory to write the output files. The packages will be
        organized in platform/ subdirectories, e.g.,
        win-32/package-1.0-py27_0.tar.bz2"""
    )
    p.add_argument(
        '-v', '--verbose',
        default=False,
        action='store_true',
        help="Print verbose output"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="only display what would have been done",
    )

    p.set_defaults(func=execute)

    args = p.parse_args()
    args_func(args, p)


path_mapping = [# (unix, windows)
                ('lib/python{pyver}', 'Lib'),
                ('bin', 'Scripts')]

pyver_re = re.compile(r'python\s+(\d.\d)')


def execute(args, parser):
    files = args.package_files

    for file in files:
        # Don't use byte literals for paths in Python 2
        if not PY3:
            file = file.decode(getpreferredencoding())

        if not file.endswith('.tar.bz2'):
            raise RuntimeError("%s does not appear to be a conda package"
                               % file)

        file = abspath(expanduser(file))
        with tarfile.open(file) as t:
            if not args.force and has_cext(t, show=args.show_imports):
                print("WARNING: Package %s has C extensions, skipping. Use -f to "
                      "force conversion." % file)
                continue

            output_dir = args.output_dir
            if not PY3:
                output_dir = output_dir.decode(getpreferredencoding())
            file_dir, fn = split(file)

            info = json.loads(t.extractfile('info/index.json')
                              .read().decode('utf-8'))
            source_type = 'unix' if info['platform'] in {'osx', 'linux'} else 'win'

            nonpy_unix = False
            nonpy_win = False

            if 'all' in args.platforms:
                args.platforms = ['osx-64', 'linux-32', 'linux-64', 'win-32', 'win-64']
            for platform in args.platforms:
                if not PY3:
                    platform = platform.decode('utf-8')
                dest_plat = platform.split('-')[0]
                dest_type = 'unix' if dest_plat in {'osx', 'linux'} else 'win'


                if source_type == 'unix' and dest_type == 'win':
                    nonpy_unix = nonpy_unix or has_nonpy_entry_points(t,
                                                                      unix_to_win=True,
                                                                      show=args.verbose)
                if source_type == 'win' and dest_type == 'unix':
                    nonpy_win = nonpy_win or has_nonpy_entry_points(t,
                                                                    unix_to_win=False,
                                                                    show=args.verbose)

                if nonpy_unix and not args.force:
                    print(("WARNING: Package %s has non-Python entry points, "
                           "skipping %s to %s conversion. Use -f to force.") %
                          (file, info['platform'], platform))
                    continue

                if nonpy_win and not args.force:
                    print(("WARNING: Package %s has entry points, which are not "
                           "supported yet. Skipping %s to %s conversion. Use -f to force.") %
                          (file, info['platform'], platform))
                    continue

                file_map = get_pure_py_file_map(t, platform)

                if args.dry_run:
                    print("Would convert %s from %s to %s" %
                          (file, info['platform'], dest_plat))
                    if args.verbose:
                        pprint.pprint(file_map)
                    continue
                else:
                    print("Converting %s from %s to %s" %

                          (file, info['platform'], platform))

                if not exists(join(output_dir, platform)):
                    makedirs(join(output_dir, platform))
                tar_update(t, join(output_dir, platform, fn), file_map, verbose=args.verbose)


if __name__ == '__main__':
    main()
