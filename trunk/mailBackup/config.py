"""
MailStore :: mailBackup configuration
"""


DEFAULT=20
DETAILED=10
VERY_DETAILED=5


"""
The following directory determines the root of all the maildirs that the system will generate. 
E.g. if the value is /var/spool/mailbackup, directories will be created from that point in the form of
/var/spool/mailbackup/domain/user. 

Note: Please make sure that the directory is writable by the python process running the proxy i.e.
the user you start the proxies as.

"""

MAILDIR_ROOT_DIR = '/Path/to/backup'

"""
The following two variables  determines the different POP/SMTP proxies that can be setup. 

To set them up use the following convention :  

POP_PROXY =[['mail1.pop3.com',serverport,localport], ['mail2.pop3.com',serverport,localport]] 
SMTP_PROXY = [['mail.smtp.com',serverport,localport], ['mail2.pop3.com',serverport,localport]]

The 'serverport' value determins the port of the service on the server to be proxied. The 'localport' detrmines the 
port that the service will be proxied on the local machine.

Note: Please make sure that the port values you choose as your 'locaalport' are within the range of bind-able ports for the user you choose to run
the proxies in.

"""

POP_PROXY =[['mail1.pop3.com',serverport,localport], ['mail2.pop3.com',serverport,localport]] 
SMTP_PROXY = [['mail.smtp.com',serverport,localport], ['mail2.pop3.com',serverport,localport]]
"""
The following variables below determines the maildir paths of your incoming and outgoing emails

Due to the fact that the system allows for maildirs for users and their relevant domains to be created on the fly, it uses the following
configuration settings to deterine the relevant maildir the outgoing (SMTP) or the incoming (POP3) email will go. 

It does this by processing the information it retrieves during the process of interaction with the email client.

For POP3 proxy it uses the hostname of the server that is being proxied, as well as the username being passed to the  POP3 server.
For the SMTP proxy it also uses the hostname of the server that is being proxied, as well as MAIL FROM value that is passed to the SMTP server.

Options for the  POP3_MAILDIR_DOMAIN_FORMAT,SMTP_MAILDIR_DOMAIN_FORMAT:

proxyHostname - It uses the complete proxied server hostname as the domain directory name. E.g. if your POP3 server is mail.pop3.com, the domain will be
                /path/to/maildir/root/dir/mail.pop3.com/user
                
proxyHostnameSubDomain-It uses the complete proxied server hostname as the domain directory name. E.g. if your POP3 server is mail.pop3.com, the domain will be
                       /path/to/maildir/root/dir/pop3.com/user
                       
userNameSubDomain-It uses the either the POP3 username or MAIL FROM parameter, chops of the portion before the domain. E.g. if your POP3 username/MAIL FROM value is  jake@pop3.com, the domain will be
                  /path/to/maildir/root/dir/pop3.com/user

Options for the  POP_MAILDIR_USER_FORMAT,SMTP_MAILDIR_USER_FORMAT:

userNamePreDomain-It uses the either thecomplete POP3 username or MAIL FROM parameter. E.g. if your POP3 username/MAIL FROM value is  jake@pop3.com, the domain will be
                 /path/to/maildir/root/dir/pop3.com/jake

userName-It uses the either the complete POP3 username or MAIL FROM parameter. E.g. if your POP3 username/MAIL FROM value is  jake@pop3.com, the domain will be
        /path/to/maildir/root/dir/pop3.com/jake

Note: The goal is to ensure that both the pop3_proxy and smtp_domain, based on the configurations settings here store 
the incoming and outgoing email for a particular user into the same maildir. 

E.g. lets say your incoming email was 'pop3.mail.com' and outgoing email domain name was 'smtp.mail.com', you probably might wanna set 
both the  POP3_MAILDIR_DOMAIN_FORMAT,SMTP_MAILDIR_DOMAIN_FORMAT to proxyHostnameSubDomain to ensure that you get the maildirs as '/maildirroot/mail.com/user'

If you need help setting this up please email me at mohangk at gmail.com
   
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
LOG_FILE='/tmp/test.log' #must be writable by the proxy processes

#This log will details of all incoming and outgoing email information from the proxy
LOG_LEVEL=VERY_DETAILED

#experimental stuff

SMTP_USERNAME='smtplogin'
SMTP_PASSWORD='smtppassword'

