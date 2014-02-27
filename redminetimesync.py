#!/usr/bin/python
import sqlite3
import datetime
import os
import sys
import ConfigParser
import re
from xml.dom import minidom
import yaml

from redmine import Redmine


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
    _date = "%{}%".format(date)  # check that we get just today
    connection = sqlite3.connect(os.path.expanduser(dataFile))
    dbCursor = connection.cursor()
    dbCursor.execute("""SELECT
            activities.name,facts.start_time,facts.end_time,facts.description,categories.name
            FROM activities
            JOIN facts ON activities.id = facts.activity_id
            LEFT JOIN categories ON activities.category_id = categories.id
            WHERE facts.start_time LIKE ?
            AND facts.end_time LIKE ?""", (_date, _date))
    return dbCursor

def calDuration(t2,t1):
    '''calculate delta between two timestamps
    Return an INT with the hour value'''
    t1 = t1.split()[1].split(":")
    t2 = t2.split()[1].split(":")
    duration = datetime.timedelta(0,int(t2[2]),0,0,int(t2[1]),int(t2[0])) - datetime.timedelta(0,int(t1[2]),0,0,int(t1[1]),int(t1[0]))
    return round(duration.seconds/3600.0, 1)

def getTimeEntries(time_entries, verbose=True):
    '''Return an array of explicit associative array for times entries, filtering out
    entries that do not match issue_id_regexp defined in config file'''
    categories_association = yaml.load(open("/home/bruno/dev/redminetimesync/activities.config", 'r'))
    if configProperties.has_option('default', 'redmine_default_activity_id'):
        default_activity_id = configProperties.get('default', 'redmine_default_activity_id')
    else:
        default_activity_id = None
    array = []
    for time_entry in time_entries:
        label = time_entry[0]
        duration = calDuration(time_entry[2], time_entry[1])
        # Try to find Redmine issue IDs from label using regexp defined in config file
        match = re.match(configProperties.get('default', 'issue_id_regexp'), label)
        if match:
            issue_id = match.group(1)
        else:
            print u'** Warning : ignoring entry "{}" : not able to find issue ID'.format(label)
            continue
        print u"* [{duration}h] #{id} : {label}".format(
            duration=duration, id=issue_id, label=label
        )
        # Try to find activity_id
        category_name = time_entry[4]
        if category_name is not None and categories_association is not None:
            if category_name in categories_association:
                activity_id = categories_association[category_name]
            else:
                print_(u'** Warning : unmatched category "{}"'.format(category_name))
                if default_activity_id is not None:
                    print u', assignated to default Redmine activity ID : {}'.format(activity_id)
                    activity_id = default_activity_id
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
            'comment': time_entry[3],
            'activity_id': activity_id
            })
    return array

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
                comment=empty_if_none(time_entry['comment']),
                activity_id=empty_if_none(time_entry['activity_id'])
            )
        )
    return myxml

def syncToRedmine(time_entries, sync_date):
    '''Gathers issues in XML format and push them to Redmine instance'''
    # Synch starts
    xml_list = generateXml(time_entries, sync_date)
    print_('-> Connecting to Redmine...')
    try:
        redmine_url = configProperties.get('redmine', 'url')
        myredmine = Redmine(redmine_url, configProperties.get('redmine', 'key'))
    except:
        print("\nCannot connect to Redmine, check out credentials or connectivity")
        return
    else:
        print('[OK]')
        print_("-> Sending entries")
        for entry in xml_list:
            xmlDocument = minidom.parseString(entry)
            myredmine.post("time_entries.xml", xmlDocument)
            print_('.')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if len(sys.argv) == 2:
            sync_date = datetime.date.today() - datetime.timedelta(int(sys.argv[1]))
            print "List of {} activities :\n".format(sync_date.strftime("%A %Y-%m-%d"))
        else:
            print "Usage : {} [days ahead]".format(sys.argv[0])
            sys.exit()
    else:
        sync_date = datetime.date.today()
        print "List of today activities :"

    sync_date = sync_date.isoformat()
    configProperties = fetchParametersFromFile()
    db_filename = configProperties.get('default', 'db')
    time_entries = getTimeEntries(fetchFromDatabase(db_filename, sync_date))

    if not time_entries:
        print("\nNo time entries to send... have you been lazy?")
        sys.exit()

    print "\nPress ENTER to synchronize those tasks ...",
    try:
        raw_input('')
    except KeyboardInterrupt:
        print "\n"
        sys.exit()

    syncToRedmine(time_entries, sync_date)
