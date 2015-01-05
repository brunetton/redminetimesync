#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Allows to switch between multiple Hamster dbs

Usage: load_hamster_db.py <db_name>

This script plays with your hamster local DB. You really should make a copy before using the script !

Before using, you have to make your hamster.db to be a symlink to a db file, like :
> ls -l
hamster.db -> test.db
real.db
test.db
'''

from docopt import docopt
import os
import os.path
from pprint import pformat
import sys
import subprocess

DB_DIR = os.path.expanduser('~/.local/share/hamster-applet/')
DEFAULT_DB_NAME = 'hamster.db'


if __name__ == '__main__':
    args = docopt(__doc__)
    db_name = args['<db_name>']
    # Check that DB_DIR exists
    assert os.path.isdir(DB_DIR)
    # Check that given db filename exists
    given_db_filename_without_path = "{}.db".format(db_name)
    given_db_filename = os.path.join(DB_DIR, given_db_filename_without_path)
    if not os.path.exists(given_db_filename):
        print "Error: {} doesn't exists".format(given_db_filename)
        sys.exit(-1)
    # Check that hamster.db is a symlink
    hamster_db_filename = os.path.join(DB_DIR, DEFAULT_DB_NAME)
    if os.path.exists(hamster_db_filename) and not os.path.islink(hamster_db_filename):
        print "Error: {} should be a symlink to use the script. See program help.".format(hamster_db_filename)
        sys.exit(-1)

    # Kill all hamster services (not sure this is a suffisent kill, you should try it by hand before)
    hamster_processes = subprocess.check_output(
        "ps auxf|grep python|grep hamster|grep -v load_hamster_db| cut -d ' ' -f 5 | xargs",
        shell=True
    ).rstrip()
    if hamster_processes:
        print "Killing Hamster processes"
        kill_command = 'kill {}'.format(hamster_processes)
        print kill_command
        subprocess.call(kill_command, shell=True)

    # Change symlink to point at given db
    if os.path.exists(hamster_db_filename):
        os.remove(hamster_db_filename)
    print "Creating symlink {} -> {}".format(DEFAULT_DB_NAME, given_db_filename_without_path)
    os.symlink(given_db_filename_without_path, hamster_db_filename)