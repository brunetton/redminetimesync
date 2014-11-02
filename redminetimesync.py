#!/usr/bin/python
import ConfigParser
import datetime
import sqlite3
import math
import moment
import os
import re
import sys
from xml.dom import minidom
import yaml

from redmine import Redmine

DB_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH:mm:ss'


def print_(string):
    '''Print the string without end line break'''
    print(string),  # Here the end-line coma is intended
    sys.stdout.flush()

def fetchParametersFromFile(configFileName='redminetimesync.config'):
    '''Takes parameters from an INI file passed via configFileName paramenter
    and returns an ordered dictionary with everything into the custom section'''
    global configProperties
    configPath = os.path.join(os.path.split(os.path.abspath(sys.argv[0]))[0],configFileName)
    config = ConfigParser.ConfigParser() # fetch parameters from a config file
    config.read(configPath)
    configProperties = config
    return configProperties

def fetchFromDatabase(dataFile, date):
    '''Following http://docs.python.org/library/sqlite3.html
    Fetch data from an SQLITE3 database
    Returns an iterable object with SELECT result'''
    _date = "%{}%".format(date)
    connection = sqlite3.connect(os.path.expanduser(dataFile))
    dbCursor = connection.cursor()
    dbCursor.execute("""SELECT
            activities.name,facts.start_time,facts.end_time,facts.description,categories.name
            FROM activities
            JOIN facts ON activities.id = facts.activity_id
            LEFT JOIN categories ON activities.category_id = categories.id
            WHERE facts.start_time LIKE ?
            ORDER BY start_time""", (_date,))
    return dbCursor

def getTimeEntries(time_entries, verbose=True):
    '''Return an array of explicit associative array for times entries, filtering out
    entries that do not match issue_id_regexp defined in config file'''
    categories_association = yaml.load(open("activities.config", 'r'))
    if configProperties.has_option('default', 'redmine_default_activity_id'):
        default_activity_id = configProperties.get('default', 'redmine_default_activity_id')
    else:
        default_activity_id = None
    array = []
    total_duration = 0
    for time_entry in time_entries:
        label = time_entry[0]
        duration = (moment.date(time_entry[2], DB_TIMESTAMP_FORMAT) - moment.date(time_entry[1], DB_TIMESTAMP_FORMAT)).seconds / 3600.
        assert duration > 0, "Duration for entry {} is not >0: {}".format(label, duration)
        total_duration += duration
        duration = round(duration, 1)
        comment = time_entry[3]
        # Try to find Redmine issue IDs from label using regexp defined in config file
        match = re.match(configProperties.get('default', 'issue_id_regexp'), label)
        if match:
            issue_id = match.group(1)
        else:
            print u'** Warning : ignoring entry "{}" : not able to find issue ID'.format(label)
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
                print_(u'** Warning : unmatched category "{}"'.format(category_name))
                if default_activity_id is not None:
                    activity_id = default_activity_id
                    print u', assignated to default Redmine activity ID : {}'.format(default_activity_id)
                else:
                    activity_id = None
                print '\n'
        else:
            if default_activity_id is not None:
                activity_id = default_activity_id
            else:
                activity_id = None

        array.append({
            'description': label,
            'label': label,
            'issue_id': issue_id,
            'duration': duration,
            'comment': comment,
            'activity_id': activity_id
            })
    if total_duration > 0:
        print "\nTotal : {}h".format(round(total_duration, 1))
    return array, total_duration

def generateXml(time_entries, date):
    '''Takes time entries and generate an xml good for Redmine APIs
    Returns a string with the parsable XML
    Cfr: http://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries'''

    def empty_if_none(string):
        return string if string is not None else ''

    myxml = []
    for time_entry in time_entries:
        myxml.append('<time_entry><issue_id>{issue_id}</issue_id><spent_on>{date}</spent_on><hours>{duration}</hours><comments>{comment}</comments><activity_id>{activity_id}</activity_id></time_entry>'.format(
                date=date,
                issue_id=time_entry['issue_id'],
                duration=time_entry['duration'],
                comment=empty_if_none(time_entry['comment']).encode("utf-8"),
                activity_id=empty_if_none(time_entry['activity_id'])
            )
        )
    return myxml

def syncToRedmine(time_entries, sync_date, raise_exceptions=False):
    '''Gathers issues in XML format and push them to Redmine instance'''
    # Synch starts
    xml_list = generateXml(time_entries, sync_date)
    print_('-> Connecting to Redmine...')
    try:
        redmine_url = configProperties.get('redmine', 'url')
        myredmine = Redmine(redmine_url, configProperties.get('redmine', 'key'))
    except:
        msg = "\nCannot connect to Redmine, check out credentials or connectivity"
        print msg
        if raise_exceptions:
            raise msg
        return
    else:
        print('[OK]')
        print_("-> Sending entries")
        for entry in xml_list:
            xmlDocument = minidom.parseString(entry)
            myredmine.post("time_entries.xml", xmlDocument)
            print_('.')


if __name__ == '__main__':
    # if len(sys.argv) > 1:
    #     if len(sys.argv) == 2:
    #         sync_date = datetime.date.today() - datetime.timedelta(int(sys.argv[1]))
    #         print "List of {} activities :\n".format(sync_date.strftime("%A %Y-%m-%d"))
    #     else:
    #         print "Usage : {} [days ahead]".format(sys.argv[0])
    #         sys.exit()
    # else:
    #     sync_date = datetime.date.today()
    #     print "List of today activities :"

    # sync_date = sync_date.isoformat()
    configProperties = fetchParametersFromFile()
    db_filename = configProperties.get('default', 'db')
    # time_entries = getTimeEntries(fetchFromDatabase(db_filename, sync_date))

    # if not time_entries:
    #     print("\nNo time entries to send... have you been lazy?")
    #     sys.exit()

    # print_("\nPress ENTER to synchronize those tasks ...")
    # try:
    #     raw_input('')
    # except KeyboardInterrupt:
    #     print "\n"
    #     sys.exit()
    #
    # syncToRedmine(time_entries, sync_date)

    boom
    start_date = moment.date('2014-10-01')
    end_date = moment.date('2014-10-30')
    date = moment.date(start_date).date
    total_time = 0
    total_sent_time = 0
    while date <= end_date:
        formatted_date = date.format('YYYY-MM-DD')
        print '*' * 30
        print formatted_date
        print '*' * 30
        time_entries, day_total = getTimeEntries(fetchFromDatabase(db_filename, formatted_date))
        total_time += day_total
        if time_entries:
            syncToRedmine(time_entries, formatted_date, raise_exceptions=True)
            sent_time = math.fsum(d['duration'] for d in time_entries)
            total_sent_time += sent_time
        date = date.add(days=1)
        print
    print
    print
    print "---> TOTAL: {}h found in Hamster - {}h sent to Redmine".format(round(total_time, 1), total_sent_time)
