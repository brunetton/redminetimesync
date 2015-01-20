#!/usr/bin/python
# -*- coding: utf-8 -*-

from ConfigParser import RawConfigParser
import os
from requests import ConnectionError
import sys

from docopt import docopt    # http://docopt.org/
import moment                # https://pypi.python.org/pypi/moment
from redmine import Redmine  # https://pypi.python.org/pypi/python-redmine
from redmine.exceptions import AuthError

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import common
from lib.common import print_


CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../redminetimesync.config')

DOC = '''
Tool for mass activities delete

Usage:
    {self_name} from <start> [(to <stop>)] [options]
    {self_name} <date> [options]
    {self_name} -h | --help

Options:
    -u --user [user_id]   Restrict deletions to user_id
    -a --auto             Do not ask for manual validation for each day, sync all days in given interval
'''


if __name__ == '__main__':
    # Read config file
    if not os.path.isfile(CONFIG_FILE):
        print('Can\'t find config file: {}\nYou can copy template conf file and adapt.'.format(CONFIG_FILE))
        sys.exit(-1)

    config = RawConfigParser()
    config.read(CONFIG_FILE)

    # Parse command line parameters
    args = docopt(DOC.format(self_name=os.path.basename(__file__)))
    from_date, to_date, for_date = common.parse_dates_in_args(args, config)
    user_id = None
    if args['--user']:
        assert args['--user'].isdigit()
        user_id = args['--user']
    else:
        print 'WARNING: you didn\'t specified an user id; deleting tasks for ALL users in Redmine !\n'

    # Get prefered date format from config file to display dates
    date_format = config.get('default', 'date_formats')
    if date_format.find(',') != -1:
        # More than one format is defined, take first
        date_format = (date_format.split(',')[0]).strip()

    # print confirmation to user, to check dates
    if from_date:
        if to_date is None:
            # implicitly takes today for to_date
            to_date = moment.now()
            question = "Delete tasks from {} to today (included) ?".format(from_date.format(date_format))
        else:
            question = "Delete tasks from {} to {} (included) ?".format(
                from_date.format(date_format),
                to_date.format(date_format)
            )
    elif for_date:
        if args['<date>'] == '0':
            question = "Delete tasks for today ?"
        elif args['<date>'] == '1':
            question = "Delete tasks for yesterday ({}) ?".format(for_date.format(date_format))
        else:
            question = "Delete tasks for {} ?".format(for_date.format(date_format))
    assert question

    print question
    print_("\nPress ENTER to validate ...")
    try:
        raw_input('')
        print "\n"
    except KeyboardInterrupt:
        print "\n"
        sys.exit()

    # Check that api_key or username (and eventually password) are given in config file
    api_key, login, password = common.get_api_key_or_login_password(config)

    # Connects to Redmine
    if api_key:
        redmine = Redmine(config.get('redmine', 'url'), key=api_key)
    else:
        if not password:
            password = getpass.getpass('{}\'s password: '.format(login))
        redmine = Redmine(config.get('redmine', 'url'), username=login, password=password)
    print_('-> Connecting to Redmine...')

    try:
        redmine.auth()
    except (AuthError, ConnectionError) as e:
        print "\nConnection error: {}".format(e.message)
        sys.exit(-1)
    print_(' OK')
    print "\n"

    if for_date:
        # only one date will be parsed
        from_date = for_date
        to_date = for_date

    # Get time entries from Redmine
    time_entries = redmine.time_entry.filter(user_id=user_id, from_date=from_date.date, to_date=to_date.date)
    if len(time_entries) == 0:
        print "-> No times entries found."
        sys.exit()

    for t in time_entries:
        print "{}   {}   #{}   {}h   {}   {}".format(t.spent_on, t.user, t.issue, t.hours, t.activity, t.project)
        if not args['--auto']:
            print_("Press ENTER to delete this entry ...")
            try:
                raw_input('')
            except KeyboardInterrupt:
                print "\n"
                sys.exit()
        redmine.time_entry.delete(t)
        print
