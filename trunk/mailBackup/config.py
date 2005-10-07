"""
Email BackupProxy configuration
"""

MAILDIR_ROOT_DIR = '/Users/mohan/Projects/mailStore/mailSpool'

DB_PATH='/Users/mohan/Projects/mailStore/db'

POP_PROXY = [['mail.asix.com.my',110,8110]]
SMTP_PROXY = [['mail.asix.com.my',25,8025]]

"""
The following variables below determines the maildir paths of your incoming and outgoing emails
"""

POP_MAILDIR_DOMAIN_FORMAT='proxyHostname' #options include proxyHostname,proxyHostnameSubDomain,userNameSubDomain

POP_MAILDIR_USER_FORMAT='userName' #options include userNamePreDomain,userName

SMTP_MAILDIR_DOMAIN_FORMAT='proxyHostname' #options include proxyHostname,proxyHostnameSubDomain,userNameSubDomain

SMTP_MAILDIR_USER_FORMAT='userName' #options include userNamePreDomain,userName

"""
Logging information
"""
#This is a basic log that is useful for debugging. It will store all the exceptions which are not dealt with explicitly
#useful for tracking cases for particular emails which are not stored for whatever reason
#LOG= #yes,no
#LOG_FILE= #must be writable by the proxy processes

#This log will store all incoming and outgoing email from the proxy
#DETAILED_LOG=#yes,no
#DETAILED_LOG_FILE=#must be writable by the proxy processes
