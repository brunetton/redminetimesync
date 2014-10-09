WHAT IS THIS?
-------------

This is meant to help people (like me) that use both [Hamster applet][1] (Gnome Time Tracker) and [Redmine][2] to keep trace of activities done.


PREREQUISITES
-------------

* Redmine >= v1.1
* Redmine API Key (see below)
* Python installed your local machine


INSTALLATION
------------

1. Clone the repository

2. Copy `redminetimesync.config.tpl` to `redminetimesync.config` : it's an INI-like file that needs two parameters:

 - url: your Redmine public url
 - key: your Redmine API key

  nb: you can find your API key on your Redmine account page (/my/account) when logged in, on the right-hand pane of the default layout.
  You'll have to enable Redmine REST API in Administration -> Settings -> Authentication


USAGE
-----
1. Log some activities in Hamster, precising Redmine issues IDs. Valid formats are :
 - **#134: Adding some interesting stuff**
 - **Fix #243**
 - **Adding logging output (#132)**

2. run the python script: **redminetimesync.py**
 - with no parameter, it will sync time entries for today
 - if you want to sync past days, add an integer as parameter (e.g. "*redminetimesync.py 1*" for yesteday, "*redminetimesync.py 3*" for 3 days ago, etc)


ADVANCED CONFIGURATION
----------------------

### Activities

Activities are defined in `activities.config` file. You can copy sample file `activities.config.tpl` (and rename it)
and adjust it for your needs.

#### Default activity

When adding times in Redmine, default activity is associated with time entry, if a default activity is defined. If there is no default activity defined in Redmine, the script will raise an error (because you're trying to add a new time entry with no activity associated). There are two workarounds :

 - define a default one in Redmine by editing it and make it default (see [Redmine wiki][3])
 - define a default one in **redminetimesync.config** file. Example :
   `redmine_default_activity_id: 9  # Development`
   (see paragraph below)

#### Getting Redmine activities Ids
By default, two activities are created when installing Redmine :

  - development
  - design

Development id is 9. You can add custom ones.

  - from Redmine v2.2, it's possible to use Redmine Rest API to get activities list. You can use list_activities.py located in the tools folder to get that list.
  - before Redmine v2.2, to get an activity ID, you can check that page on your redmine install : **/redmine/enumerations** if you have admin rights (activities IDs are in the urls of edit links); or use guess_redmine_activities_ids.py located in the tools folder.

#### Link Hamster's categories to Redmine activities

If you need to report on Redmine more than one activity, you can edit **activities.config** file and associate Hamster categories names to Redmine activities IDs.
For example :

    # Development (default in all Redmine installations)
    Dev: 9
    # Custom activities
    Project management: 13
    # Project managment
    Phone: 14
    Customer email: 14

With this conf, if the script encounter a Hamster time entry named "**#123 : adding API key to make redminetimesync usable**" associated with **Phone** category in Hamster, a new time entry for task #123 with activity number 14 will be created.

#### Hints

  - in Hamster, you can precise category directly while entering activity description. For example :
    `Answering the phone (#34) @phone`
    Will associate that entry to the "phone" category in Hamster


[1]: https://extensions.gnome.org/extension/425/project-hamster-extension/
[2]: http://www.redmine.org/
[3]: http://www.redmine.org/projects/redmine/wiki/RedmineEnumerations
