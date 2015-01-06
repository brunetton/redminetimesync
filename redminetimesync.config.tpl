[redmine]
url: https://your.redmine.url
key: <your_redmine_api_key_here>

[default]
# Default Hamster local SQLite file
db: ~/.local/share/hamster-applet/hamster.db

# Coma-separated date formats for command line date parsing
date_formats: DD/MM/YY, DD/MM  ; first format is also used for dates display

# Regex used to parse Hamster time entry to find out issue ID
issue_id_regexp: .*# ?(\d+)

# Activity id sent to each time entry (uncomment this if you have an error due to no default activity defined in Redmine)
# See activities.config file for an enhanced control upon activities
#redmine_default_activity_id: 9  ; development
