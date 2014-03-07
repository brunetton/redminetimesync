import urllib
import urllib2
from xml.dom import minidom, getDOMImplementation

		

class Redmine:
	'''Class to interoperate with a Redmine installation using the REST web services.
	instance = Redmine(url, [key=strKey], [username=strName, password=strPass] )
	
	url is the base url of the Redmine install ( http://my.server/redmine )
	
	key is the user API key found on the My Account page for the logged in user
		All interactions will take place as if that user were performing them, and only
		data that that user can see will be seen

	If a key is not defined then a username and password can be used
	If neither are defined, then only publicly visible items will be retreived	
	'''
	
	def __init__(self, url, key=None, username=None, password=None ):
		self.__url = url
		self.__key = key
		self.projects = {}
		self.projectsID = {}
		self.projectsXML = {}
		
		self.issuesID = {}
		self.issuesXML = {}
		
		# Status ID from a default install
		self.ISSUE_STATUS_ID_NEW = 1
		self.ISSUE_STATUS_ID_RESOLVED = 3
		self.ISSUE_STATUS_ID_CLOSED = 5
		
		self.__opener = None
		
		if not username:
			username = key
			self.__key = None
			
		if not password:
			password = '12345'  #the same combination on my luggage!  (dummy value)
		
		if( username and password ):
			#realm = 'Redmine API'
			# create a password manager
			password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

			password_mgr.add_password(None, url, username, password )
			handler = urllib2.HTTPBasicAuthHandler( password_mgr )

			# create "opener" (OpenerDirector instance)
			self.__opener = urllib2.build_opener( handler )

			# set the opener when we fetch the URL
			self.__opener.open( url )

			# Install the opener.
			urllib2.install_opener( self.__opener )
			
		else:
			if not key:
				pass
				#raise TypeError('Must pass a key or username and password')
		
	class Project:
		'''Object returned by Redmine getProject calls
		   redmine is the redmine object.
		   objXML is the xml object containing the object data'''
		
		def __init__(self, redmine, objXML ):
			self.__redmine = redmine
			
			self.objXML = objXML
			
			self.data = self.__redmine.parseProject( objXML )
			self.number = self.data[ 'id' ]
			self.id = self.data[ 'identifier' ]

		def newIssue(self, subject, description='', priorityID=None, trackerID=None, assigned_to_id=None, Xdata=None ):
			'''Create a new issue for this project.  Unfortunately, there is no easy way to 
			   discover the valid values for priorityID and trackerID'''
			   
			if Xdata:
				data = Xdata.copy()
			else:
				data = {}
				
			data[ 'project_id' ] = self.number
			data[ 'subject' ] = subject
			data[ 'description' ] = description
			if priorityID:
				data[ 'priority_id' ] = priorityID
			if trackerID:
				data[ 'tracker' ] = trackerID
			if assigned_to_id:
				data[ 'assigned_to_id' ] = assigned_to_id
			
			return self.__redmine.newIssueFromDict( data )
			
		def getIssues(self ):
			pass
			#todo: finish

	# extend the request to handle PUT command
	class PUT_Request(urllib2.Request):
		def get_method(self):
			return 'PUT'

	# extend the request to handle DELETE command
	class DELETE_Request(urllib2.Request):
		def get_method(self):
			return 'DELETE'

	def open(self, page, parms=None, objXML=None, HTTPrequest=None ):
		'''Opens a page from the server with optional XML.  Returns an XML object'''
		if not parms:
			parms={}
			
		# if we're using a key, add it to the parms array
		if self.__key:
			parms['key'] = self.__key
		
		# encode any data
		urldata = ''
		if parms:
			urldata = '?' + urllib.urlencode( parms )
		
		
		fullUrl = self.__url + '/' + page
		
		# register this url to be used with the opener
		if self.__opener:
			self.__opener.open( fullUrl )
			
		#debug
		#print fullUrl + urldata
		
		# Set up the request
		if HTTPrequest:
			request = HTTPrequest( fullUrl + urldata )
		else:
			request = urllib2.Request( fullUrl + urldata )
		# get the data and return XML object
		try:
			if objXML:
				request.add_header('Content-Type', 'text/xml')
				response = urllib2.urlopen( request, objXML.toxml().encode("utf-8"))
			else:
				response = urllib2.urlopen( request )
		except urllib2.HTTPError, error:
			print "\n\n----------------\nServer error {} : {}".format(error.code, error.read())
			print "Request : POST on {}".format(fullUrl)
			if objXML:
				print "Datas :\n{}".format(objXML.toprettyxml())
			print "----------------"
		else:
			try:
				return minidom.parse( response )
			except:
				return response.read()

	def get(self, page, parms=None ):
		'''Gets an XML object from the server - used to read Redmine items.'''
		return self.open( page, parms )
	
	def post(self, page, objXML, parms=None ):
		'''Posts an XML object to the server - used to make new Redmine items.  Returns an XML object.'''
		return self.open( page, parms, objXML )
	
	def put(self, page, objXML, parms=None ):
		'''Puts an XML object on the server - used to update Redmine items.  Returns nothing useful.'''
		return self.open( page, parms, objXML, HTTPrequest=self.PUT_Request )
	
	def delete(self, page ):
		'''Deletes a given object on the server - used to remove items from Redmine.  Use carefully!'''
		return self.open( page, HTTPrequest=self.DELETE_Request )
	
	def parseRedmineXML(self, objXML, container ):
		'''parses the Redmine XML into a python dict.  Returns data within the first container found.'''
		#todo: correctly parse nested child nodes
		
		d = {}
		pXML = objXML.getElementsByTagName(container)[0]
		for child in pXML.childNodes:
			if child.hasChildNodes():
				d[child.nodeName] = child.firstChild.nodeValue
				
		return d
		
	def XMLaddkeyval(self, xmlDoc, xmlNode, key, value):
		'''adds a key/value pair to a given XMLDoc at the xmlNode location'''
		xmlChild = xmlDoc.createElement( str(key) )
		xmlChild.appendChild( xmlDoc.createTextNode( str(value) ) )
		xmlNode.appendChild( xmlChild )

	def XMLcreatedoc(self, tag ):
		'''returns a new XML document with the given tag as the outermost container '''
		return getDOMImplementation().createDocument(None, tag, None)
	
	def dict2XML(self, tag, dict ):
		'''returns a new XML document with the given tag and the dict encoded within '''
		xml = self.XMLcreatedoc( tag )
		for key in dict:
			self.XMLaddkeyval( xml, xml.firstChild, key, dict[key] )
			
		return xml
	
	def parseProject(self, objXML ):
		'''parses project data from an XML object'''
		projectDict = self.parseRedmineXML( objXML, 'project' )
		
		self.projects[ projectDict['identifier'] ] = projectDict
		self.projectsID[ projectDict['id'] ] = projectDict
		#self.projectsXML[ project ] = objXML
		
		return projectDict
	
	def parseIssue(self, objXML ):
		'''parses issue data from an XML object'''
		issue = self.parseRedmineXML( objXML, 'issue' )
		
		self.issuesID[ issue['id'] ] = issue
		#self.issuesXML[ issue ] = objXML
		return issue
		
	def getProject(self, projectIdent ):
		'''returns a dictionary for the given project name'''
		#return self.parseProject( self.get('projects/'+projectIdent+'.xml') )
		return self.Project( self, self.get('projects/'+projectIdent+'.xml') )
		
	def getIssue(self, issueID ):
		'''returns a dictionary for the given issue'''
		return self.parseIssue( self.get('issues/'+str(issueID)+'.xml') )
		
	def newIssueFromDict(self, dict ):
		'''creates a new issue using fields from the passed dictionary'''
		xml = self.dict2XML( 'issue', dict )
		return self.parseIssue( self.post( 'issues.xml', xml ) )
	
	def updateIssueFromDict(self, ID, dict ):
		'''updates an issue with the given ID using fields from the passed dictionary'''
		xml = self.dict2XML( 'issue', dict )
		return self.put( 'issues/'+str(ID)+'.xml', xml )

	def deleteIssue(self, ID ):
		'''delete an issue with the given ID.  This can't be undone - use carefully!
		Note that the proper method of finishing an issue is to update it to a closed state.'''
		return self.delete( 'issues/'+str(ID)+'.xml' )
		
	def closeIssue(self, ID ):
		'''close an issue by setting the status to self.ISSUE_STATUS_ID_CLOSED'''
		return self.updateIssueFromDict( ID, {'status_id':self.ISSUE_STATUS_ID_CLOSED} )
		
	def resolveIssue(self, ID ):
		'''close an issue by setting the status to self.ISSUE_STATUS_ID_RESOLVED'''
		return self.updateIssueFromDict( ID, {'status_id':self.ISSUE_STATUS_ID_RESOLVED} )
