#!/usr/bin/python
import ConfigParser
import datetime
import os
import sys
import time
from xml.dom import minidom

sys.path.append('..')
from redmine import Redmine


def print_(string):
    '''Print the string without end line break'''
    print(string),  # Here the end-line coma is intended
    sys.stdout.flush()


def fetchParametersFromFile(configFileName='redminetimesync.config'):
    '''Takes parameters from an INI file passed via configFileName paramenter
    and returns an ordered dictionary with everything into the custom section'''
    global configProperties
    configPath = os.path.join(os.path.split(os.path.abspath(sys.argv[0]))[0], '..', configFileName)
    config = ConfigParser.ConfigParser() # fetch parameters from a config file
    config.read(configPath)
    configProperties = config
    return configProperties


def generateXml(issue_id, activity_id):
    return '<time_entry><issue_id>{issue_id}</issue_id><spent_on>{date}</spent_on><hours>{duration}</hours><comments>{comment}</comments><activity_id>{activity_id}</activity_id></time_entry>'.format(
            issue_id=issue_id,
            activity_id=activity_id,
            date=datetime.date.today().isoformat(),
            duration=1,
            comment="activity_id : {}".format(activity_id)
        )


if __name__ == '__main__':
    first_activity_id = 1
    last_activity_id = 50

    if len(sys.argv) == 2:
        issue_id=int(sys.argv[1])
    else:
        print "Usage : {} test_issue_id".format(sys.argv[0])
        print
        print "The purpose of this tool is to guess Redmine activities IDs when used Redmine version is <= 2.2"
        print "(/enumerations/time_entry_activities.xml in Rest API is implemented in v2.2)"
        print "The script will attempt to add {n} time entries (from {first} to {last}) in Redmine #test_issue_id,".format(n=last_activity_id-first_activity_id+1, first=first_activity_id, last=last_activity_id)
        print "with for each entry the sent activity id on comment argument."
        print "This will make you then possible to go to that issue page and look on spend time to get activities IDs."
        sys.exit()

    configProperties = fetchParametersFromFile()
    print_('-> Connecting to Redmine...')
    try:
        redmine_url = configProperties.get('redmine', 'url')
        myredmine = Redmine(redmine_url, configProperties.get('redmine', 'key'))
    except:
        print("\nCannot connect to Redmine, check out credentials or connectivity")
        sys.exit()
    print('[OK]')

    for activity_id in range(first_activity_id, last_activity_id + 1):
        print_("{} ".format(activity_id))
        xml = generateXml(issue_id, activity_id)
        myredmine.post("time_entries.xml", minidom.parseString(xml))
        time.sleep(1)
