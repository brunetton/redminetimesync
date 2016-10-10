#!/usr/bin/python
# -*- coding: utf-8 -*-

from ConfigParser import RawConfigParser
from requests import ConnectionError
import datetime
import getpass
import sqlite3
import math
import os
from pprint import pformat
import re
import sys

from docopt import docopt    # http://docopt.org/
import moment                # https://pypi.python.org/pypi/moment
from redmine import Redmine  # https://pypi.python.org/pypi/python-redmine
from redmine.exceptions import (
        AuthError,
        ResourceNoFieldsProvidedError,
        ResourceNotFoundError,
        ServerError
    )
import yaml


sys.path.append('.')
from lib import common
from lib.common import print_


ACTIVITIES_CONFIG_FILE = 'activities.config'
CONFIG_FILE = 'redminetimesync.config'
DB_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH:mm:ss'

DOC = '''
Redmine / Hamster times entries synchronization

Usage:
    {self_name} from <start> [(to <stop>)] [options]
    {self_name} <date> [options]
    {self_name} -h | --help

Options:
    -a --auto             Do not ask for manual validation for each day, sync all days in given interval
    -n --no-date-confirm  Do not ask for manual dates interval confirmation at begining

Note: start, stop and date could be :
    - a date: ("12/10", "12/10/15", ...)
      -> check for config file to change dates formats
    - a number of days ago: ("3" means 3 days ago, "1" means yesterday, ...)
      -> 0 means today
'''


def getTimeEntries(date, config):
    '''Reads Sqlite Redmine DB file and return an array of explicit associative array for times entries,
    filtering out entries that do not match issue_id_regexp defined in config file
    Returns:
        - activities_array:
            array of dicts with 'description', 'label', 'issue_id', 'duration', 'comment', 'activity_id' keys
        - total_duration: sum of all activities duration
    '''

    def fetchFromDatabase(db_filename, date):
        '''Fetch data from an SQLITE3 database
        Returns an iterable object with SELECT result'''
        _date = "%{}%".format(date.format('YYYY-MM-DD'))
        connection = sqlite3.connect(os.path.expanduser(db_filename))
        dbCursor = connection.cursor()
        dbCursor.execute("""SELECT
            activities.name,facts.start_time,facts.end_time,facts.description,categories.name
            FROM activities
            JOIN facts ON activities.id = facts.activity_id
            LEFT JOIN categories ON activities.category_id = categories.id
            WHERE facts.start_time LIKE ?
            ORDER BY start_time""", (_date,)
        )
        return dbCursor

    db_filename = config.get('default', 'db')
    time_entries = fetchFromDatabase(db_filename, date)
    if os.path.exists(ACTIVITIES_CONFIG_FILE):
        categories_association = yaml.load(open(ACTIVITIES_CONFIG_FILE, 'r'))
    else:
        categories_association = None
    if config.has_option('default', 'redmine_default_activity_id'):
        default_activity_id = config.get('default', 'redmine_default_activity_id')
    else:
        default_activity_id = None
    activities = []
    total_duration = 0
    for time_entry in time_entries:
        label = time_entry[0]
        if not time_entry[2]:
            print(u'\n** Warning: ignoring "{}": Not completed yet\n'.format(label))
            continue
        duration = (moment.date(time_entry[2], DB_TIMESTAMP_FORMAT) - moment.date(time_entry[1], DB_TIMESTAMP_FORMAT)).seconds / 3600.
        assert duration > 0, "Duration for entry {} is not >0: {}".format(label, duration)
        total_duration += duration
        duration = round(duration, 1)
        comment = time_entry[3]
        # Try to find Redmine issue IDs from label using regexp defined in config file
        match = re.match(config.get('default', 'issue_id_regexp'), label)
        if match:
            issue_id = match.group(1)
        else:
            print u'\n** Warning: ignoring entry "{}" : not able to find issue ID\n'.format(label)
            continue
        print u"* [{duration}h #{id}]: {label}".format(
            duration=round(duration, 1), id=issue_id, label=label
        )
        if comment is not None:
            print u"  {}".format(comment)
        # Try to find activity_id
        category_name = time_entry[4]
        if category_name is not None and categories_association is not None:
            if category_name in categories_association:
                activity_id = categories_association[category_name]
            else:
                print_(u'  * Warning: unmatched category "{}"'.format(category_name))
                if default_activity_id is not None:
                    activity_id = default_activity_id
                    print u'- assignated to default Redmine activity ID : {}'.format(default_activity_id)
                else:
                    activity_id = None
        else:
            if default_activity_id is not None:
                activity_id = default_activity_id
            else:
                activity_id = None

        activities.append({
            'description': label,
            'label': label,
            'issue_id': issue_id,
            'duration': duration,
            'comment': comment,
            'activity_id': activity_id
        })
    if total_duration > 0:
        print "\n\nTotal : {}h".format(round(total_duration, 1))
    return activities, total_duration


def syncToRedmine(time_entries, date, redmine):
    '''Push all given time_entries to Redmine'''
    def issue_exists(id, redmine):
        assert id
        issue_exists = True
        try:
            redmine.issue.get(id)
        except ResourceNotFoundError:
            issue_exists = False
        return issue_exists

    print_("-> Sending entries")
    try:
        time_entry = None
        for time_entry_infos in time_entries:
            print_('.')
            issue_id = time_entry_infos['issue_id']
            time_entry_to_send = {
                'spent_on': date.date.date(),  # converts Moment date to Date
                'issue_id': issue_id,
                'hours': time_entry_infos['duration'],
                'activity_id': time_entry_infos['activity_id'],
                'comments': time_entry_infos['comment']
            }
            try:
                # Send this activity to Redmine
                redmine.time_entry.create(**time_entry_to_send)
            except ServerError:
                # Error 500
                # Check that issue id exists (may be a cause of 500 error on some Redmine versions)
                print
                if not issue_exists(issue_id, redmine):
                    print "** ERROR ** Internal server error received from Redmine. "\
                        "This is probably because issue id {} doesn't exists ?".format(issue_id)
                else:
                    print "** ERROR ** Internal server error received from Redmine !"
                print "\nLast time entry was:\n{}".format(pformat(time_entry_to_send))
                sys.exit(-1)
    except ConnectionError as e:
        print "Connection Error: {}".format(e.message)
    print "\n"


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
            question = "Sync tasks from {} to today (included) ?".format(from_date.format(date_format))
        else:
            question = "Sync tasks from {} to {} (included) ?".format(
                from_date.format(date_format),
                to_date.format(date_format)
            )
    elif for_date:
        if args['<date>'] == '0':
            question = "Sync tasks for today ?"
        elif args['<date>'] == '1':
            question = "Sync tasks for yesterday ({}) ?".format(for_date.format(date_format))
        else:
            question = "Sync tasks for {} ?".format(for_date.format(date_format))
    assert question

    if not args['--no-date-confirm']:
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
    total_time = 0
    total_sent_time = 0
    date = from_date.clone()
    while date <= to_date:
        if not for_date:
            print "{s} {formatted_date} {s}".format(s='*' * 20, formatted_date=date.format(date_format))
        # Get time entries from local DB
        time_entries, day_total = getTimeEntries(date, config)
        if not time_entries:
            print("\nNo time entries to send... have you been lazy ?\n\n\n")
            date = date.add(days=1)
            continue
        # Wait for user validation
        if not args['--auto']:
            print "\nPress ENTER to synchronize those tasks ...",
            try:
                raw_input('')
            except KeyboardInterrupt:
                print "\n"
                sys.exit()
        total_time += day_total
        syncToRedmine(time_entries, date, redmine)
        sent_time = math.fsum(d['duration'] for d in time_entries)
        total_sent_time += sent_time
        date = date.add(days=1)
        print
    print "\n---> TOTAL: {}h found in Hamster - {}h sent to Redmine".format(round(total_time, 1), total_sent_time)
