"""
An attempt at writing a python module for handling the storage of mailDir styled emails
"""
import os.path
import time,socket,md5
from threading import Lock


""""
def initializeMaildir(dir):
    if not os.path.isdir(dir):
        os.mkdir(dir, 0700)
        for subdir in ['new', 'cur', 'tmp', '.Trash']:
            os.mkdir(os.path.join(dir, subdir), 0700)
        for subdir in ['new', 'cur', 'tmp']:
            os.mkdir(os.path.join(dir, '.Trash', subdir), 0700)
        # touch
        open(os.path.join(dir, '.Trash', 'maildirfolder'), 'w').close()
"""

timeseq = 0
lasttime = long(0)
timelock = Lock()

def gettimeseq():
    global lasttime, timeseq, timelock
    timelock.acquire()
    try:
        thistime = long(time.time())
        if thistime == lasttime:
            timeseq += 1
            return (thistime, timeseq)
        else:
            lasttime = thistime
            timeseq = 0
            return (thistime, timeseq)
    finally:
        timelock.release()

class MailDir:

    def __init__(self,maildirRoot,domain,username,domainFormat,userFormat,mailFolder=None):
        self.MAILDIR_ROOT=maildirRoot
        domainDirName,userDirName=self.processMaildirPath(domain,username,domainFormat,userFormat)
        self.__maildir = self.getMaildirPath(domainDirName,userDirName,mailFolder)
        #print self.__maildir

    def getMaildirPath(self,domain,user,mailFolder):
        #test if the maildir for the domain path exists, else make it
        if not os.path.exists(os.path.join(self.MAILDIR_ROOT,domain)):
            os.mkdir(os.path.join(self.MAILDIR_ROOT,domain))
            os.mkdir(os.path.join(self.MAILDIR_ROOT,domain,user))

       #test if the maildir for the user exists
        elif not os.path.exists(os.path.join(self.MAILDIR_ROOT,domain,user)):
            os.mkdir(os.path.join(self.MAILDIR_ROOT,domain,user))

        #test if the users sent folder exists
        if mailFolder != None:
            if not os.path.exists(os.path.join(self.MAILDIR_ROOT,domain,user,'.'+mailFolder)):
                os.mkdir(os.path.join(self.MAILDIR_ROOT,domain,user,'.'+mailFolder))

            return os.path.join(self.MAILDIR_ROOT,domain,user,'.'+mailFolder)
        else:
            return os.path.join(self.MAILDIR_ROOT,domain,user)

    def isMaildir(self):
        if os.path.exists(os.path.join(self.__maildir,'new')) and os.path.exists(os.path.join(self.__maildir,'cur')) and os.path.exists(os.path.join(self.__maildir,'tmp')):
            return True
        else:
            return False

    def createMaildir(self):
        os.mkdir(os.path.join(self.__maildir,'new'))
        os.mkdir(os.path.join(self.__maildir,'cur'))
        os.mkdir(os.path.join(self.__maildir,'tmp'))

    def getvisiblename(self):
        return self.__maildir

    def storeEmail(self,data):
        if self.isMaildir()==False:
            self.createMaildir()

        #f=open(self.__maildir+'/new/testemail'+`time.time()`,'w')
        #f.write(data)
        #f.close()
        return self.savemessage(data,os.path.join(self.__maildir,'new'),os.path.join(self.__maildir,'tmp'))



    #def savemessage(self, uid, content, flags):
    def savemessage(self,content, newdir,tmpdir):
        #newdir = os.path.join(self.getfullname(), 'new')
        #tmpdir = os.path.join(self.getfullname(), 'tmp')
        messagename = None
        attempts = 0

        while 1:
            if attempts > 15:
                raise IOError, "Couldn't write to file %s" % messagename
            timeval, timeseq = gettimeseq()
            messagename = '%d_%d.%d.%s' % \
                      (timeval,
                      timeseq,
                      os.getpid(),
                      socket.gethostname())
                
            if os.path.exists(os.path.join(tmpdir, messagename)):
                time.sleep(2)
                attempts += 1
            else:
                break

        tmpmessagename = messagename
        #ui.debug('maildir', 'savemessage: using temporary name %s' % tmpmessagename)
        file = open(os.path.join(tmpdir, tmpmessagename), "wt")
        file.write(content)
        file.close()
        #ui.debug('maildir', 'savemessage: moving from %s to %s' % \
        #        (tmpmessagename, messagename))
        os.link(os.path.join(tmpdir, tmpmessagename),
                os.path.join(newdir, messagename))
        os.unlink(os.path.join(tmpdir, tmpmessagename))
        #self.messagelist[uid] = {'uid': uid, 'flags': [],
        #                     'filename': os.path.join(newdir, messagename)}
        #self.savemessageflags(uid, flags)
        #ui.debug('maildir', 'savemessage: returning uid %d' % uid)
        #return uid
        return os.path.join(newdir, messagename)



    """
    POP_MAILDIR_DOMAIN_FORMAT='proxyHostname' #options include proxyHostname,proxyHostnameSubDomain,userNameSubDomain

    POP_MAILDIR_USER_FORMAT='userName' #options include userNamePreDomain,userName

    SMTP_MAILDIR_DOMAIN_FORMAT='proxyHostname' #options include proxyHostname,proxyHostnameSubDomain,userNameSubDomain

    SMTP_MAILDIR_USER_FORMAT='userName' #options include userNamePreDomain,userName
    """
    def processMaildirPath(self,domain,user,domainFormat,userFormat):
        if domainFormat not in ('proxyHostname','proxyHostnameSubDomain','userNameSubDomain'):
            domainReturned=domain
        elif domainFormat=='proxyHostnameSubDomain':
            if len(domain.split('.',1))>1:
                domainReturned=domain.split('.',1)[1]
            else:
                domainReturned=domain
        elif domainFormat=='userNameSubDomain':
            if len(user.split('@',1))>1:
                domainReturned=user.split('@',1)[1]
            else:
                domainReturned=user
        elif domainFormat=='proxyHostname':
            domainReturned=domain
            
        if userFormat not in ('userNamePreDomain','userName') or userFormat=='userName':
            userReturned=user
        elif userFormat=='userNamePreDomain':
            if len(user.split('@',1))>1:
                userReturned=user.split('@',1)[0]
            else:
                userReturned=user
            
        return domainReturned,userReturned

"""
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
