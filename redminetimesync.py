#!/usr/bin/python
import sqlite3
import datetime
import os
import sys
import ConfigParser
import re
from xml.dom import minidom
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
    _date = ("%"+date+"%", "%"+date+"%") # check that we get just today
    connection = sqlite3.connect(os.path.expanduser(dataFile))
    dbCursor = connection.cursor()
    dbCursor.execute("""SELECT
            activities.name,facts.start_time,facts.end_time,facts.description
            FROM activities
            JOIN facts ON activities.id = facts.activity_id
            WHERE facts.start_time LIKE ?
            AND facts.end_time LIKE ?""", _date)
    return dbCursor

def calDuration(t2,t1):
    '''calculate delta between two timestamps
    Return an INT with the hour value'''
    t1 = t1.split()[1].split(":")
    t2 = t2.split()[1].split(":")
    duration = datetime.timedelta(0,int(t2[2]),0,0,int(t2[1]),int(t2[0])) - datetime.timedelta(0,int(t1[2]),0,0,int(t1[1]),int(t1[0]))
    return round(duration.seconds/3600.0, 1)

def getTimeEntries(time_entries):
    '''Return an array of explicit associative array for times entries, filtering out
    entries that do not match issue_id_regexp defined in config file'''
    array = []
    for time_entry in time_entries:
        label = time_entry[0]
        # Try to find Redmine issue IDs from label using regexp defined in config file
        match = re.match(configProperties.get('default', 'issue_id_regexp'), label)
        if match:
            array.append({
                'label': label,
                'issue_id': match.group(1),
                'duration': calDuration(time_entry[2], time_entry[1]),
                'comment': time_entry[3]})
        else:
            print u'** Warning : ignoring entry "{}" : not able to find issue ID'.format(label)
    return array

def generateXml(time_entries, date):
    '''Takes time entries and generate an xml good for Redmine APIs
    Returns a string with the parsable XML
    Cfr: http://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries'''
    myxml = []
    for time_entry in time_entries:
        if configProperties.get('default', 'redmine_default_activity_id') is not None:
            activity_id = configProperties.get('default', 'redmine_default_activity_id')
        else:
            activity_id = None
        myxml.append('<time_entry><issue_id>{issue_id}</issue_id><spent_on>{date}</spent_on><hours>{duration}</hours><comments>{comment}</comments><activity_id>{activity_id}</activity_id></time_entry>'.format(
                issue_id=time_entry['issue_id'],
                duration=time_entry['duration'],
                comment=time_entry['comment'],
                activity_id=activity_id,
                date=date
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

    # Print entries found for that day :
    for time_entry in time_entries:
        print u"* [{duration}h] #{id} : {label}".format(
            duration=time_entry['duration'], id=time_entry['issue_id'], label=time_entry['label'])

    print "\nPress ENTER to synchronize those tasks ...",
    try:
        raw_input('')
    except KeyboardInterrupt:
        print "\n"
        sys.exit()

    syncToRedmine(time_entries, sync_date)
