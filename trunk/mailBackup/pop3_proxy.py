import mailDir,config
import os, sys, re, errno, getopt, time, traceback, socket, cStringIO,email
from thread import start_new_thread

import Dibbler

# Increase the stack size on MacOS X.  Stolen from Lib/test/regrtest.py
if sys.platform == 'darwin':
    try:
        import resource
    except ImportError:
        pass
    else:
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        newsoft = min(hard, max(soft, 1024*2048))
        resource.setrlimit(resource.RLIMIT_STACK, (newsoft, hard))

# exception may be raised if we are already running and check such things.
class AlreadyRunningException(Exception):
    pass

# number to add to STAT length for each msg to fudge for spambayes headers
HEADER_SIZE_FUDGE_FACTOR = 512

class ServerLineReader(Dibbler.BrighterAsyncChat):
    """An async socket that reads lines from a remote server and
    simply calls a callback with the data.  The BayesProxy object
    can't connect to the real POP3 server and talk to it
    synchronously, because that would block the process."""

    lineCallback = None

    def __init__(self, serverName, serverPort, lineCallback):
        Dibbler.BrighterAsyncChat.__init__(self)
        self.lineCallback = lineCallback
        self.request = ''
        self.set_terminator('\r\n')
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # create_socket creates a non-blocking socket.  This is not great,
        # because then socket.connect() will return errno 10035, because
        # connect takes time.  We then don't know if the connect call
        # succeeded or not.  With Python 2.4, this means that we will move
        # into asyncore.loop(), and if the connect does fail, have a
        # loop something like 'while True: log(error)', which fills up
        # stdout very fast.
        self.socket.setblocking(1)
        try:
            self.connect((serverName, serverPort))
        except socket.error, e:
            error = "Can't connect to %s:%d: %s" % (serverName, serverPort, e)
            # Some people have their system setup to check mail very
            # frequently, but without being clever enough to check whether
            # the network is available.  If we continually print the
            # "can't connect" error, we use up lots of CPU and disk space.
            # To avoid this, if not verbose only print each distinct error
            # once per hour.
            # See also: [ 1113863 ] sb_tray eats all cpu time
            now = time.time()
            then = time.time() - 3600
            #if error not in state.reported_errors or \
            #   options["globals", "verbose"] or \
            #   state.reported_errors[error] < then:
            #    print >>sys.stderr, error

                # Record this error in the list of ones we have seen this
                # session.
             #   state.reported_errors[error] = now

            self.lineCallback('-ERR %s\r\n' % error)
            self.lineCallback('')   # "The socket's been closed."
            self.close()
        else:
            self.socket.setblocking(0)
            
    def collect_incoming_data(self, data):
        self.request = self.request + data

    def found_terminator(self):
        self.lineCallback(self.request + '\r\n')
        self.request = ''

    def handle_close(self):
        self.lineCallback('')
        self.close()


class POP3ProxyBase(Dibbler.BrighterAsyncChat):
    """An async dispatcher that understands POP3 and proxies to a POP3
    server, calling `self.onTransaction(request, response)` for each
    transaction. Responses are not un-byte-stuffed before reaching
    self.onTransaction() (they probably should be for a totally generic
    POP3ProxyBase class, but BayesProxy doesn't need it and it would
    mean re-stuffing them afterwards).  self.onTransaction() should
    return the response to pass back to the email client - the response
    can be the verbatim response or a processed version of it.  The
    special command 'KILL' kills it (passing a 'QUIT' command to the
    server).
    """

    def __init__(self, clientSocket, serverName, serverPort):
        Dibbler.BrighterAsyncChat.__init__(self, clientSocket)
        self.request = ''
        self.response = ''
        self.set_terminator('\r\n')
        self.command = ''           # The POP3 command being processed...
        self.args = []              # ...and its arguments
        self.isClosing = False      # Has the server closed the socket?
        self.seenAllHeaders = False # For the current RETR or TOP
        self.startTime = 0          # (ditto)
        
        
        print 'clientSocket:'
        print clientSocket
        
        if not self.onIncomingConnection(clientSocket):
            # We must refuse this connection, so pass an error back
            # to the mail client.
            self.push("-ERR Connection not allowed\r\n")
            self.close_when_done()
            return

        self.serverSocket = ServerLineReader(serverName, serverPort,
                                             self.onServerLine)

    def onIncomingConnection(self, clientSocket):
        """Checks the security settings."""
        # Stolen from UserInterface.py

        #remoteIP = clientSocket.getpeername()[0]
        #trustedIPs = options["pop3proxy", "allow_remote_connections"]

        #if trustedIPs == "*" or remoteIP == clientSocket.getsockname()[0]:
        #    return True

        #trustedIPs = trustedIPs.replace('.', '\.').replace('*', '([01]?\d\d?|2[04]\d|25[0-5])')
        #for trusted in trustedIPs.split(','):
        #    if re.search("^" + trusted + "$", remoteIP):
        #        return True

        #return False
        return True
        
    def onTransaction(self, command, args, response):
        """Overide this.  Takes the raw request and the response, and
        returns the (possibly processed) response to pass back to the
        email client.
        """
        raise NotImplementedError

    def onServerLine(self, line):
        """A line of response has been received from the POP3 server."""
        isFirstLine = not self.response
        self.response = self.response + line

        # Is this the line that terminates a set of headers?
        self.seenAllHeaders = self.seenAllHeaders or line in ['\r\n', '\n']

        # Has the server closed its end of the socket?
        if not line:
            self.isClosing = True

        # If we're not processing a command, just echo the response.
        if not self.command:
            self.push(self.response)
            self.response = ''

        # Time out after 30 seconds for message-retrieval commands if
        # all the headers are down.  The rest of the message will proxy
        # straight through.
        if self.command in ['TOP', 'RETR'] and \
           self.seenAllHeaders and time.time() > self.startTime + 30:
            self.onResponse()
            self.response = ''
        # If that's a complete response, handle it.
        elif not self.isMultiline() or line == '.\r\n' or \
           (isFirstLine and line.startswith('-ERR')):
            self.onResponse()
            self.response = ''

    def isMultiline(self):
        """Returns True if the request should get a multiline
        response (assuming the response is positive).
        """
        if self.command in ['USER', 'PASS', 'APOP', 'QUIT',
                            'STAT', 'DELE', 'NOOP', 'RSET', 'KILL']:
            return False
        elif self.command in ['RETR', 'TOP', 'CAPA']:
            return True
        elif self.command in ['LIST', 'UIDL']:
            return len(self.args) == 0
        else:
            # Assume that an unknown command will get a single-line
            # response.  This should work for errors and for POP-AUTH,
            # and is harmless even for multiline responses - the first
            # line will be passed to onTransaction and ignored, then the
            # rest will be proxied straight through.
            return False

    def collect_incoming_data(self, data):
        """Asynchat override."""
        self.request = self.request + data

    def found_terminator(self):
        """Asynchat override."""
        verb = self.request.strip().upper()
        if verb == 'KILL':
            self.socket.shutdown(2)
            self.close()
            raise SystemExit
        elif verb == 'CRASH':
            # For testing
            x = 0
            y = 1/x

        self.serverSocket.push(self.request + '\r\n')
        if self.request.strip() == '':
            # Someone just hit the Enter key.
            self.command = ''
            self.args = []
        else:
            # A proper command.
            splitCommand = self.request.strip().split()
            self.command = splitCommand[0].upper()
            self.args = splitCommand[1:]
            self.startTime = time.time()

        self.request = ''

    def onResponse(self):
        # We don't support pipelining, so if the command is CAPA and the
        # response includes PIPELINING, hack out that line of the response.
        if self.command == 'CAPA':
            pipelineRE = r'(?im)^PIPELINING[^\n]*\n'
            self.response = re.sub(pipelineRE, '', self.response)

        # Pass the request and the raw response to the subclass and
        # send back the cooked response.
        if self.response:
            cooked = self.onTransaction(self.command, self.args, self.response)
            self.push(cooked)

        # If onServerLine() decided that the server has closed its
        # socket, close this one when the response has been sent.
        if self.isClosing:
            self.close_when_done()

        # Reset.
        self.command = ''
        self.args = []
        self.isClosing = False
        self.seenAllHeaders = False


class BayesProxyListener(Dibbler.Listener):
    """Listens for incoming email client connections and spins off
    BayesProxy objects to serve them.
    """

    def __init__(self, serverName, serverPort, proxyPort):
        proxyArgs = (serverName, serverPort)
        Dibbler.Listener.__init__(self, proxyPort, BackupProxy, proxyArgs)
        #print 'Listener on port %s is proxying %s:%d' % \
        #       (_addressPortStr(proxyPort), serverName, serverPort)
               
               
class BackupProxy(POP3ProxyBase):
    """Proxies between an email client and a POP3 server, storing the 
    email being passed to an POP3 server

     o RETR:
        o Stores the email.

     o USER:
        o Captures the username being sent to the proxy
    """
    def __init__(self, clientSocket, serverName, serverPort):
        POP3ProxyBase.__init__(self, clientSocket, serverName, serverPort)
        self.handlers = {'RETR': self.onRetr,'USER': self.onUser}
        #state.totalSessions += 1
        #state.activeSessions += 1
        self.isClosed = False   
        self.MAILDIR_ROOT=config.MAILDIR_ROOT_DIR
        self.proxyHostname=serverName


    def send(self, data):
        """Logs the data to the log file."""
        #if options["globals", "verbose"]:
        #    state.logFile.write(data)
        #    state.logFile.flush()
        #print data
        try:
            return POP3ProxyBase.send(self, data)
        except socket.error:
            # The email client has closed the connection - 40tude Dialog
            # does this immediately after issuing a QUIT command,
            # without waiting for the response.
            self.close()

    def recv(self, size):
        """Logs the data to the log file."""
        data = POP3ProxyBase.recv(self, size)
        #if options["globals", "verbose"]:
        #    state.logFile.write(data)
        #    state.logFile.flush()
        #print data
        return data

    def close(self):
        # This can be called multiple times by async.
        if not self.isClosed:
            self.isClosed = True
            #state.activeSessions -= 1
            POP3ProxyBase.close(self)

    def onTransaction(self, command, args, response):
        """Takes the raw request and response, and returns the
        (possibly processed) response to pass back to the email client.
        """
        handler = self.handlers.get(command, self.onUnknown)
        return handler(command, args, response)

    def onRetr(self, command, args, response):
        print "in onRetr"
        ok, messageText = response.split('\n', 1)
        #try :
        currentMaildir=mailDir.MailDir(config.MAILDIR_ROOT_DIR,self.proxyHostname,self.userName,config.POP_MAILDIR_DOMAIN_FORMAT,config.POP_MAILDIR_USER_FORMAT)
        currentMaildir.storeEmail(messageText)
           
        #except Exception,e:
           #empty except to always trap errors to ensure that we always return the email body
           #pass

        return response

    def onUser(self, command, args, response):
        self.userName=args[0]
        return response

    def onUnknown(self, command, args, response):
        """Default handler; returns the server's response verbatim."""
        return response

