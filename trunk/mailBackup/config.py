"""
mailBackup configuration
"""

MAILDIR_ROOT_DIR = '/Users/mohan/Projects/mailStore/mailSpool'

POP_PROXY = [['mail.asix.com.my',110,8110]]
SMTP_PROXY = [['mail.asix.com.my',25,8025]]

"""
Due to the fact that the system allows for maildirs for users to be created on the fly, it uses the following
configuration settings to deterine the relevant maildir the outgoing (SMTP) or the incoming (POP3) email will go. 

For the USER_FORMAT:

For SMTP it uses the mail from entry being passed to the SMTP server
For POP3 it uses the username being used to login into the POP server

For the DOMAIN FORMAT it basically uses the server that is being proxied address

The following variables below determines the maildir paths of your incoming and outgoing emails

    >>> import mailDir
    >>> print mailDir.getMaildirPath('mail.asix.com.my','mohan@asix.com.my','proxyHostnameSubDomain','userNamePreDomain')
    ('asix.com.my', 'mohan')
    >>> print mailDir.getMaildirPath('mail.asix.com.my','mohan@asix.com.my.dodo','userNameSubDomain','userName')
    ('asix.com.my.dodo', 'mohan@asix.com.my.dodo')
    >>> print mailDir.getMaildirPath('asix.com.my','mohan','proxyHostnameSubDomain','userNamePreDomain')
    ('com.my', 'mohan')
    >>> print mailDir.getMaildirPath('asix.com.my','mohan','userNameSubDomain','userNamePreDomain')
    ('mohan', 'mohan')
"""

POP_MAILDIR_DOMAIN_FORMAT='proxyHostname' #options include proxyHostname,proxyHostnameSubDomain,userNameSubDomain

POP_MAILDIR_USER_FORMAT='userName' #options include userNamePreDomain,userName

SMTP_MAILDIR_DOMAIN_FORMAT='proxyHostname' #options include proxyHostname,proxyHostnameSubDomain,userNameSubDomain

SMTP_MAILDIR_USER_FORMAT='userName' #options include userNamePreDomain,userName

"""
Logging information - not implemented yet
"""
#This is a basic log that is useful for debugging. It will store all the exceptions which are not dealt with explicitly
#useful for tracking cases for particular emails which are not stored for whatever reason
#LOG= #yes,no
#LOG_FILE= #must be writable by the proxy processes

#This log will store all incoming and outgoing email from the proxy
#DETAILED_LOG=#yes,no
#DETAILED_LOG_FILE=#must be writable by the proxy processes
