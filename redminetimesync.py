#!/usr/bin/python
import sqlite3
import datetime
import os
import sys
import ConfigParser
from xml.dom import minidom
from redmine import Redmine

def getDate():
    '''If there's no CLI parameter, returns date for today formatted in isoformat
    otherwise returns yesterday'''
    date = datetime.date.today()
    if len(sys.argv) == 2 and sys.argv[1] == "yesterday":
        date = date - datetime.timedelta(1)
    return date.isoformat()

def fetchParametersFromFile(configFileName='redminetimesync.config'):
    '''Takes parameters from an INI file passed via configFileName paramenter
    and returns an ordered dictionary with everything into the DEFAULT section'''
    global configProperties
    configPath = os.path.join(os.path.split(os.path.abspath(sys.argv[0]))[0],configFileName)
    config = ConfigParser.RawConfigParser() # fetch parameters from a config file
    config.read(configPath)
    configProperties = config.defaults() # set those parameters as the actual programs to run
    return configProperties

def fetchFromDatabase(dataFile, date):
    '''Following http://docs.python.org/library/sqlite3.html
    Fetch data from an SQLITE3 database
    Returns an iterable object with SELECT result'''
    _date = ("%"+getDate()+"%", "%"+getDate()+"%") # check that we get just today
    connection = sqlite3.connect(dataFile)
    dbCursor = connection.cursor()
    dbCursor.execute("""SELECT
            activities.name,facts.start_time,facts.end_time,facts.description
            FROM activities
            JOIN facts ON activities.id = facts.activity_id
            WHERE facts.start_time LIKE ?
            AND facts.end_time LIKE ?""", _date)
    return dbCursor

def filterNotNumericIssues(iterable):
    '''Takes an iterable and scans for not numeric
    data in the first column, via numericOnly() call'''
    numericOnly = []
    for issue in iterable:
        try:
            int(issue[0])
        except:
            print "Filtering time entry named '%s'" % issue[0]
        else:
            numericOnly.append(issue)
    return numericOnly

def calDuration(t2,t1):
    '''calculate delta between two timestamps
    Return an INT with the hour value'''
    t1 = t1.split()[1].split(":")
    t2 = t2.split()[1].split(":")
    duration = datetime.timedelta(0,int(t2[2]),0,0,int(t2[1]),int(t2[0])) - datetime.timedelta(0,int(t1[2]),0,0,int(t1[1]),int(t1[0]))
    return round(duration.seconds/3600.0, 1)

def generateXml(refinedIssues):
    '''Takes time entries and generate an xml good for Redmine APIs
    Returns a string with the parsable XML'''
    myxml = []
    for issue in refinedIssues:
        comment = ""
        if issue[3]: comment = issue[3] 
        myxml.append('<time_entry><issue_id>%s</issue_id><hours>%s</hours><comments>%s</comments></time_entry>' % (issue[0], calDuration(issue[2],issue[1]), comment))
    return myxml

def syncToRedmine():
    '''Gathers issues in XML format and push them to Redmine instance'''
    configProperties = fetchParametersFromFile()
    xml = generateXml(filterNotNumericIssues(fetchFromDatabase(configProperties['db'], getDate())))
    if xml:
        try:
            myredmine = Redmine(configProperties['url'], configProperties['key'])
        except:
            print("Something wrong, check out credentials or connectivity")
        else:
            for issue in xml:
                xmlDocument = minidom.parseString(issue)
                myredmine.post("time_entries.xml", xmlDocument)
            print("Sync to %s [OK]" % configProperties['url'])
    else: print("Today no time entries to send... have you been lazy?")

if __name__ == '__main__':
    syncToRedmine()
