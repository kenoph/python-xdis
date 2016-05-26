#!/usr/bin/env python
# emacs-mode: -*-python-*-
"""
test_pyenvlib -- uncompyle and verify Python libraries

Usage-Examples:

  test_pyenvlib.py --all		# disassemble all tests across all pyenv libraries
  test_pyenvlib.py --all --verify	# disassemble all tests and verify results
  test_pyenvlib.py --test		# disassemble only the testsuite
  test_pyenvlib.py --2.7.11 --verify	# disassemble and verify python lib 2.7.11

Adding own test-trees:

Step 1) Edit this file and add a new entry to 'test_options', eg.
          test_options['mylib'] = ('/usr/lib/mylib', PYOC, 'mylib')
Step 2: Run the test:
	  test_pyenvlib --mylib	  # disassemble 'mylib'
	  test_pyenvlib --mylib --verify # disassemble verify 'mylib'
"""

#----- configure this for your needs

TEST_VERSIONS=('2.4.6', '2.5.6',  '2.6.9', '2.7.6',
               '2.7.8', '2.7.10', '2.7.11',
               '3.2.6', '3.3.5',  '3.4.2', '3.5.1')

PYPY_TEST_VERSIONS=(('pypy-2.6.1', '2.7'), ('pypy-5.0.1', '2.7'))

#-----


import os, py_compile, time, shutil, sys
from fnmatch import fnmatch

from xdis import main, PYTHON3, PYTHON_VERSION
from xdis.verify import verify_file

LONG_PYTHON_VERSION = ("%s.%s.%s" %
                       (sys.version_info[0],
                        sys.version_info[1],
                        sys.version_info[2]))

target_base = '/tmp/py-dis/'
lib_prefix = os.path.dirname(os.path.join.__code__.co_filename)

PY = ('*.py', )
PYC = ('*.pyc', )
PYO = ('*.pyo', )
PYOC = ('*.pyc', '*.pyo')

my_dir = os.path.dirname(__file__)
test_options = {
    'simple': (os.path.join(my_dir, 'simple_source'),
               PY, 'simple-source')
    }

for vers in TEST_VERSIONS:
    short_vers = vers[:3]
    test_options[vers] = (lib_prefix, PYC, 'python-lib'+short_vers)

for vers, short_vers in PYPY_TEST_VERSIONS:
    test_options[vers] = (os.path.join(lib_prefix, vers, 'lib-python', short_vers),
                          PYC, 'python'+short_vers)



def do_tests(src_dir, patterns, target_dir, start_with=None,
                 do_verify=False, max_files=800, do_compile=False,
                 verbose=False):

    def visitor(files, dirname, names):
        files.extend(
            [os.path.normpath(os.path.join(dirname, n))
                 for n in names
                    for pat in patterns
                        if fnmatch(n, pat)])

    def file_matches(files, root, basenames, patterns):
        files.extend(
            [os.path.normpath(os.path.join(root, n))
                 for n in basenames
                    for pat in patterns
                        if fnmatch(n, pat)])

    files = []
    if do_compile:
        for root, dirs, basenames in os.walk(src_dir):
            file_matches(files, root, basenames, PY)
            for sfile in files:
                py_compile.compile(sfile)
                pass
            pass
        files = []
        pass

    cwd = os.getcwd()
    os.chdir(src_dir)
    if PYTHON3:
        for root, dirname, names in os.walk(os.curdir):
            files.extend(
                [os.path.normpath(os.path.join(root, n))
                     for n in names
                        for pat in patterns
                            if fnmatch(n, pat)])
            pass
        pass
    else:
        os.path.walk(os.curdir, visitor, files)
    files.sort()

    if start_with:
        try:
            start_with = files.index(start_with)
            files = files[start_with:]
            print('>>> starting with file', files[0])
        except ValueError:
            pass

    if len(files) > max_files:
        files = [file for file in files if not 'site-packages' in file]
        files = [file for file in files if not 'test' in file]
        if len(files) > max_files:
            files = files[:max_files]
            pass
    elif len(files) == 0:
        print("No files found\n")
        os.chdir(cwd)
        return

    output = open(os.devnull,"w")
    # output = sys.stdout
    start_time = time.time()
    print(time.ctime())
    for i, bc_file in enumerate(files):
        if verbose:
            print(os.path.join(src_dir, bc_file))
        bc_filename, co, version, ts, magic = main.disassemble_file(bc_file, output)
        if do_verify:
            file = co.co_filename
            if 'TRAVIS' in os.environ and os.environ['TRAVIS']:
                verify_file(file, bc_filename)
        if i % 100 == 0 and i > 0:
            print("Processed %d files" % (i))
    print("Processed %d files, total" % (i+1))
    print(time.ctime())
    elapsed_time = time.time() - start_time
    print("%g seconds" % elapsed_time)
    os.chdir(cwd)

if __name__ == '__main__':
    import getopt

    do_verify = False
    do_compile = False
    test_dirs = []
    start_with = None
    max_files = 800
    test_version = None

    if len(sys.argv) == 1:
        sys.argv[1] == '--simple'

    test_options_keys = list(test_options.keys())
    test_options_keys.sort()
    opts, args = getopt.getopt(sys.argv[1:], '',
                               ['start-with=',
                                'max-files=',
                                'compile',
                                'verify', ] \
                               + test_options_keys )
    for opt, val in opts:
        if opt == '--verify':
            do_verify = True
        elif opt == '--compile':
            do_compile = True
        elif opt == '--start-with':
            start_with = val
        elif opt == '--max-files':
            max_files = int(val)
        elif opt[2:] in test_options_keys:
            test_version = opt[2:]
            test_dirs.append(test_options[test_version])
            pass
        pass

    if test_version == 'simple':
        if PYTHON_VERSION > 2.6:
            test_dirs.append((os.path.join(my_dir, 'simple_2.7'),
                             PY, 'simple-source'))
            pass
        pass
    if do_verify:
        if test_version is None:
            test_dirs.append(test_options[LONG_PYTHON_VERSION])
        elif test_version != 'simple':
            if LONG_PYTHON_VERSION != test_version:
                sys.stderr.write("When --verify is used, the running version %s\n"
                                 "has to be the same as the version you want to test %s\n"
                                 % (LONG_PYTHON_VERSION, test_version))
                sys.exit(1)
            pass
        pass

    for src_dir, pattern, target_dir in test_dirs:
        if os.path.exists(src_dir):
            target_dir = os.path.join(target_base, target_dir)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=1)
            do_tests(src_dir, pattern, target_dir, start_with,
                         do_verify=do_verify,
                         max_files=max_files, do_compile=do_compile)
        else:
            print("### Path %s doesn't exist; skipping" % src_dir)
