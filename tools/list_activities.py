#!/usr/bin/python
import sqlite3
import os
import sys
import ConfigParser
import urllib2

sys.path.append('..')
from redmine import Redmine


def fetchParametersFromFile(configFileName='redminetimesync.config'):
    '''Takes parameters from an INI file passed via configFileName paramenter
    and returns an ordered dictionary with everything into the custom section'''
    global configProperties
    configPath = os.path.join(os.path.split(os.path.abspath(sys.argv[0]))[0], '..', configFileName)
    config = ConfigParser.ConfigParser() # fetch parameters from a config file
    config.read(configPath)
    configProperties = config
    return configProperties


if __name__ == '__main__':
    configProperties = fetchParametersFromFile()
    redmine_url = configProperties.get('redmine', 'url')
    print('-> Connecting to Redmine...'),
    sys.stdout.flush()
    try:
        redmine_url = configProperties.get('redmine', 'url')
        myredmine = Redmine(redmine_url, configProperties.get('redmine', 'key'))
    except:
        print("\nCannot connect to Redmine, check out credentials or connectivity")
        sys.exit()

    print('[OK]')
    print("-> Sending request"),
    sys.stdout.flush()
    try:
        res=myredmine.get("/enumerations/time_entry_activities.xml")
    except urllib2.HTTPError, e:
        print
        if e.code==404:
            print '[404] Error !'
            print 'Make sure your version of Redmine is >= 2.2.'

    #TODO
