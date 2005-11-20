#!/Library/Frameworks/Python.framework/Versions/2.4/bin/python
"""An RFC 2821 smtp proxy.

Usage: %(program)s [options] [localhost:localport [remotehost:remoteport]]

Options:

    --nosetuid
    -n
        This program generally tries to setuid `nobody', unless this flag is
        set.  The setuid call will fail if this program is not run as root (in
        which case, use this flag).

    --version
    -V
        Print the version number and exit.

    --class classname
    -c classname
        Use `classname' as the concrete SMTP proxy class.  Uses `PureProxy' by
        default.

    --debug
    -d
        Turn on debugging prints.

    --help
    -h
        Print this message and exit.

Version: %(__version__)s

If localhost is not given then `localhost' is used, and if localport is not
given then 8025 is used.  If remotehost is not given then `localhost' is used,
and if remoteport is not given, then 25 is used.
"""


# Overview:
#
# This file implements the minimal SMTP protocol as defined in RFC 821.  It
# has a hierarchy of classes which implement the backend functionality for the
# smtpd.  A number of classes are provided:
#
#   SMTPServer - the base class for the backend.  Raises NotImplementedError
#   if you try to use it.
#
#   DebuggingServer - simply prints each message it receives on stdout.
#
#   PureProxy - Proxies all messages to a real smtpd which does final
#   delivery.  One known problem with this class is that it doesn't handle
#   SMTP errors from the backend server at all.  This should be fixed
#   (contributions are welcome!).
#
#   MailmanProxy - An experimental hack to work with GNU Mailman
#   <www.list.org>.  Using this server as your real incoming smtpd, your
#   mailhost will automatically recognize and accept mail destined to Mailman
#   lists when those lists are created.  Every message not destined for a list
#   gets forwarded to a real backend smtpd, as with PureProxy.  Again, errors
#   are not handled correctly yet.
#
# Please note that this script requires Python 2.0
#
# Author: Barry Warsaw <barry@python.org>
#
# TODO:
#
# - support mailbox delivery
# - alias files
# - ESMTP
# - handle error codes from the backend smtpd

import sys
import os
import errno
import getopt
import time
import socket
import asyncore
import asynchat
import thread
import smtplib
from time import sleep

import threading
from StringIO import StringIO 

import mailDir,logging,config

__all__ = ["SMTPServer","DebuggingServer","PureProxy","MailmanProxy"]

program = sys.argv[0]
__version__ = 'Python SMTP proxy version 0.2'


class Devnull:
    def write(self, msg): pass
    def flush(self): pass


DEBUGSTREAM = Devnull()
NEWLINE = '\n'
EMPTYSTRING = ''
COMMASPACE = ', '



def usage(code, msg=''):
    print >> sys.stderr, __doc__ % globals()
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)



class SMTPChannel(asynchat.async_chat):
    COMMAND = 0
    DATA = 1

    def __init__(self, server, conn, addr):
        asynchat.async_chat.__init__(self, conn)
        self.__server = server
        self.__conn = conn
        self.__addr = addr
        self.__line = []
        self.__state = self.COMMAND
        self.__greeting = 0
        self.__mailfrom = None
        self.__rcpttos = []
        self.__data = ''
        self.__fqdn = socket.getfqdn()
        self.__peer = conn.getpeername()
        print >> DEBUGSTREAM, 'Peer:', repr(self.__peer)
        self.push('220 %s %s' % (self.__fqdn, __version__))
        self.set_terminator('\r\n')

    # Overrides base class for convenience
    def push(self, msg):
        asynchat.async_chat.push(self, msg + '\r\n')

    # Implementation of base class abstract method
    def collect_incoming_data(self, data):
        self.__line.append(data)

    # Implementation of base class abstract method
    def found_terminator(self):
        line = EMPTYSTRING.join(self.__line)
        print >> DEBUGSTREAM, 'Data:', repr(line)
        self.__line = []
        if self.__state == self.COMMAND:
            if not line:
                self.push('500 Error: bad syntax')
                return
            method = None
            i = line.find(' ')
            if i < 0:
                command = line.upper()
                arg = None
            else:
                command = line[:i].upper()
                arg = line[i+1:].strip()
            method = getattr(self, 'smtp_' + command, None)
            if not method:
                self.push('502 Error: command "%s" not implemented' % command)
                return
            method(arg)
            return
        else:
            if self.__state != self.DATA:
                self.push('451 Internal confusion')
                return
            # Remove extraneous carriage returns and de-transparency according
            # to RFC 821, Section 4.5.2.
            data = []
            for text in line.split('\r\n'):
                if text and text[0] == '.':
                    data.append(text[1:])
                else:
                    data.append(text)
            self.__data = NEWLINE.join(data)
            
            thread.start_new_thread(self.__server.process_message,(self.__peer,
                                                   self.__mailfrom,
                                                   self.__rcpttos,
                                                   self.__data,))
            #status = self.__server.process_message(self.__peer,
                                                   #self.__mailfrom,
                                                   #self.__rcpttos,
                                                   #self.__data)
            status=None
            self.__rcpttos = []
            self.__mailfrom = None
            self.__state = self.COMMAND
            self.set_terminator('\r\n')
            
            if not status:
                self.push('250 Ok')
            else:
                self.push(status)
            
    # SMTP and ESMTP commands
    def smtp_HELO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        if self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.__greeting = arg
            self.push('250 %s' % self.__fqdn)

    def smtp_NOOP(self, arg):
        if arg:
            self.push('501 Syntax: NOOP')
        else:
            self.push('250 Ok')

    def smtp_QUIT(self, arg):
        # args is ignored
        self.push('221 Bye')
        self.close_when_done()

    # factored
    def __getaddr(self, keyword, arg):
        address = None
        keylen = len(keyword)
        if arg[:keylen].upper() == keyword:
            address = arg[keylen:].strip()
            if not address:
                pass
            elif address[0] == '<' and address[-1] == '>' and address != '<>':
                # Addresses can be in the form <person@dom.com> but watch out
                # for null address, e.g. <>
                address = address[1:-1]
        return address

    def smtp_MAIL(self, arg):
        print >> DEBUGSTREAM, '===> MAIL', arg
        address = self.__getaddr('FROM:', arg)
        if not address:
            self.push('501 Syntax: MAIL FROM:<address>')
            return
        if self.__mailfrom:
            self.push('503 Error: nested MAIL command')
            return
        self.__mailfrom = address
        print >> DEBUGSTREAM, 'sender:', self.__mailfrom
        self.push('250 Ok')

    def smtp_RCPT(self, arg):
        print >> DEBUGSTREAM, '===> RCPT', arg
        if not self.__mailfrom:
            self.push('503 Error: need MAIL command')
            return
        address = self.__getaddr('TO:', arg)
        if not address:
            self.push('501 Syntax: RCPT TO: <address>')
            return
        self.__rcpttos.append(address)
        print >> DEBUGSTREAM, 'recips:', self.__rcpttos
        self.push('250 Ok')

    def smtp_RSET(self, arg):
        if arg:
            self.push('501 Syntax: RSET')
            return
        # Resets the sender, recipients, and data, but not the greeting
        self.__mailfrom = None
        self.__rcpttos = []
        self.__data = ''
        self.__state = self.COMMAND
        self.push('250 Ok')

    def smtp_DATA(self, arg):
        if not self.__rcpttos:
            self.push('503 Error: need RCPT command')
            return
        if arg:
            self.push('501 Syntax: DATA')
            return
        self.__state = self.DATA
        self.set_terminator('\r\n.\r\n')
        self.push('354 End data with <CR><LF>.<CR><LF>')



class SMTPServer(asyncore.dispatcher):
    def __init__(self, localaddr, remoteaddr):
        self._localaddr = localaddr
        self._remoteaddr = remoteaddr
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # try to re-use a server port if possible
        self.set_reuse_addr()
        self.bind(localaddr)
        self.listen(5)
        print >> DEBUGSTREAM, \
              '%s started at %s\n\tLocal addr: %s\n\tRemote addr:%s' % (
            self.__class__.__name__, time.ctime(time.time()),
            localaddr, remoteaddr)

    def handle_accept(self):
        conn, addr = self.accept()
        print >> DEBUGSTREAM, 'Incoming connection from %s' % repr(addr)
        channel = SMTPChannel(self, conn, addr)

    # API for "doing something useful with the message"
    def process_message(self, peer, mailfrom, rcpttos, data):
        """Override this abstract method to handle messages from the client.

        peer is a tuple containing (ipaddr, port) of the client that made the
        socket connection to our smtp port.

        mailfrom is the raw address the client claims the message is coming
        from.

        rcpttos is a list of raw addresses the client wishes to deliver the
        message to.

        data is a string containing the entire full text of the message,
        headers (if supplied) and all.  It has been `de-transparencied'
        according to RFC 821, Section 4.5.2.  In other words, a line
        containing a `.' followed by other text has had the leading dot
        removed.

        This function should return None, for a normal `250 Ok' response;
        otherwise it returns the desired response string in RFC 821 format.

        """
        raise NotImplementedError

class PureProxy(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data):
        lines = data.split('\n')
        # Look for the last header
        i = 0
        for line in lines:
            if not line:
                break
            i += 1
        lines.insert(i, 'X-Peer: %s' % peer[0])
        data = NEWLINE.join(lines)
        refused = self._deliver(mailfrom, rcpttos, data)
        
        currentMaildir=mailDir.MailDir(config.MAILDIR_ROOT_DIR,self._remoteaddr[0],mailfrom,config.SMTP_MAILDIR_DOMAIN_FORMAT,config.SMTP_MAILDIR_USER_FORMAT,'Sent')
        newEmailLocation=currentMaildir.storeEmail(data)
        
        logging.info('SMTP:Storing email at : %s'%(newEmailLocation))
        
        # TBD: what to do with refused addresses?
        print >> DEBUGSTREAM, 'we got some refusals:', refused
    
    def write(self,msg):
        if len(msg.strip())>0:
            logging.log(config.VERY_DETAILED,'SMTP: '+msg)

    def _deliver(self, mailfrom, rcpttos, data):
        refused = {}
        
        old_error = smtplib.stderr 
        new_error = self
        smtplib.stderr=new_error
        #sys.stdout.write('dodojingo')
        try:
            s = smtplib.SMTP()
            s.set_debuglevel(1)
            s.connect(self._remoteaddr[0], self._remoteaddr[1])
            s.ehlo()
            s.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            #s.connect(self._remoteaddr[0], self._remoteaddr[1])
            try:
                refused = s.sendmail(mailfrom, rcpttos, data)
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused, e:
            print >> DEBUGSTREAM, 'got SMTPRecipientsRefused'
            refused = e.recipients
        except (socket.error, smtplib.SMTPException), e:
            print >> DEBUGSTREAM, 'got', e.__class__
            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise,fake it with a non-triggering
            # exception code.
            errcode = getattr(e, 'smtp_code', -1)
            errmsg = getattr(e, 'smtp_error', 'ignore')
            for r in rcpttos:
                refused[r] = (errcode, errmsg)
        #finally:
        smtplib.stderr = old_error
        return refused

class Options:
    setuid = 1
    classname = 'PureProxy'
    
def parseargs():
    global DEBUGSTREAM
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], 'nVhc:d',
            ['class=', 'nosetuid', 'version', 'help', 'debug'])
    except getopt.error, e:
        usage(1, e)

    options = Options()
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-V', '--version'):
            print >> sys.stderr, __version__
            sys.exit(0)
        elif opt in ('-n', '--nosetuid'):
            options.setuid = 0
        elif opt in ('-c', '--class'):
            options.classname = arg
        elif opt in ('-d', '--debug'):
            DEBUGSTREAM = sys.stderr

    # parse the rest of the arguments
    if len(args) < 1:
        localspec = 'localhost:8025'
        remotespec = 'localhost:25'
    elif len(args) < 2:
        localspec = args[0]
        remotespec = 'localhost:25'
    elif len(args) < 3:
        localspec = args[0]
        remotespec = args[1]
    else:
        usage(1, 'Invalid arguments: %s' % COMMASPACE.join(args))

    # split into host/port pairs
    i = localspec.find(':')
    if i < 0:
        usage(1, 'Bad local spec: %s' % localspec)
    options.localhost = localspec[:i]
    try:
        options.localport = int(localspec[i+1:])
    except ValueError:
        usage(1, 'Bad local port: %s' % localspec)
    i = remotespec.find(':')
    if i < 0:
        usage(1, 'Bad remote spec: %s' % remotespec)
    options.remotehost = remotespec[:i]
    try:
        options.remoteport = int(remotespec[i+1:])
    except ValueError:
        usage(1, 'Bad remote port: %s' % remotespec)
    return options

if __name__ == '__main__':
    
    if config.LOG_FILE != '' :
        if config.LOG_LEVEL==config.DETAILED:
            loggingLevel=logging.DEBUG
        elif config.LOG_LEVEL==config.VERY_DETAILED:
            loggingLevel=config.VERY_DETAILED
        else:
            loggingLevel=logging.INFO
    
        logging.basicConfig(level=loggingLevel,
                            format='%(asctime)s %(levelname)s %(message)s',
                            filename=config.LOG_FILE,
                            filemode='a+')
    
    options = parseargs()
    # Become nobody
    if options.setuid:
        try:
            import pwd
        except ImportError:
            print >> sys.stderr, \
                  'Cannot import module "pwd"; try running with -n option.'
            sys.exit(1)
        nobody = pwd.getpwnam('nobody')[2]
        try:
            os.setuid(nobody)
        except OSError, e:
            if e.errno != errno.EPERM: raise
            print >> sys.stderr, \
                  'Cannot setuid "nobody"; try running with -n option.'
            sys.exit(1)
    classname = options.classname
    if "." in classname:
        lastdot = classname.rfind(".")
        mod = __import__(classname[:lastdot], globals(), locals(), [""])
        classname = classname[lastdot+1:]
    else:
        import __main__ as mod
    class_ = getattr(mod, classname)
    proxy = class_((options.localhost, options.localport),
                   (options.remotehost, options.remoteport))
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass
        


