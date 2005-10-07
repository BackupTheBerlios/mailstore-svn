#!/usr/bin/env python

import mailDir ,config
import string
import re
import socket
import asyncore
import asynchat
import getopt
import sys
import os

from pop3_proxy import ServerLineReader

import Dibbler

class SMTPProxyBase(Dibbler.BrighterAsyncChat):
    """An async dispatcher that understands SMTP and proxies to a SMTP
    server, calling `self.onTransaction(command, args)` for each
    transaction.

    self.onTransaction() should return the command to pass to
    the proxied server - the command can be the verbatim command or a
    processed version of it.  The special command 'KILL' kills it (passing
    a 'QUIT' command to the server).
    """

    def __init__(self, clientSocket, serverName, serverPort):
        Dibbler.BrighterAsyncChat.__init__(self, clientSocket)
        self.request = ''
        self.set_terminator('\r\n')
        self.command = ''           # The SMTP command being processed...
        self.args = ''              # ...and its arguments
        self.isClosing = False      # Has the server closed the socket?
        self.inData = False
        self.data = ""
        self.blockData = False

        if not self.onIncomingConnection(clientSocket):
            # We must refuse this connection, so pass an error back
            # to the mail client.
            self.push("421 Connection not allowed\r\n")
            self.close_when_done()
            return

        self.serverSocket = ServerLineReader(serverName, serverPort,
                                             self.onServerLine)


    def onIncomingConnection(self, clientSocket):
        """Checks the security settings."""
        # Stolen from UserInterface.py

        #remoteIP = clientSocket.getpeername()[0]
        #trustedIPs = options["smtpproxy", "allow_remote_connections"]

        #if trustedIPs == "*" or remoteIP == clientSocket.getsockname()[0]:
        #    return True

        #trustedIPs = trustedIPs.replace('.', '\.').replace('*', '([01]?\d\d?|2[04]\d|25[0-5])')
        #for trusted in trustedIPs.split(','):
        #    if re.search("^" + trusted + "$", remoteIP):
        #        return True

        #return False
        return True

    def onTransaction(self, command, args):
        """Overide this.  Takes the raw command and returns the (possibly
        processed) command to pass to the email client."""
        raise NotImplementedError

    def onProcessData(self, data):
        """Overide this.  Takes the raw data and returns the (possibly
        processed) data to pass back to the email client."""
        raise NotImplementedError

    def onServerLine(self, line):
        """A line of response has been received from the SMTP server."""
        # Has the server closed its end of the socket?
        if not line:
            self.isClosing = True

        # We don't process the return, just echo the response.
        self.push(line)
        self.onResponse()

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

        if self.request.strip() == '':
            # Someone just hit the Enter key.
            self.command = self.args = ''
        else:
            # A proper command.
            if self.request[:10].upper() == "MAIL FROM:":
                splitCommand = self.request.split(":", 1)
            elif self.request[:8].upper() == "RCPT TO:":
                splitCommand = self.request.split(":", 1)
            else:
                splitCommand = self.request.strip().split(None, 1)
            self.command = splitCommand[0]
            self.args = splitCommand[1:]

        if self.inData == True:
            self.data += self.request + '\r\n'
            if self.request == ".":
                self.inData = False
                cooked = self.onProcessData(self.data)
                self.data = ""
                if self.blockData == False:
                    self.serverSocket.push(cooked)
                else:
                    self.push("250 OK\r\n")
        else:
            cooked = self.onTransaction(self.command, self.args)
            if cooked is not None:
                self.serverSocket.push(cooked + '\r\n')
        self.command = self.args = self.request = ''

    def onResponse(self):
        # If onServerLine() decided that the server has closed its
        # socket, close this one when the response has been sent.
        if self.isClosing:
            self.close_when_done()

        # Reset.
        self.command = ''
        self.args = ''
        self.isClosing = False


class BayesSMTPProxyListener(Dibbler.Listener):
    """Listens for incoming email client connections and spins off
    BayesSMTPProxy objects to serve them."""

    def __init__(self, serverName, serverPort, proxyPort):
        proxyArgs = (serverName, serverPort)
        Dibbler.Listener.__init__(self, proxyPort, BackupSMTPProxy,proxyArgs)
        #print 'SMTP Listener on port %s is proxying %s:%d' % \
        #       (_addressPortStr(proxyPort), serverName, serverPort)

        
class BackupSMTPProxy(SMTPProxyBase):
    
    """Proxies between an email client and a SMTP server, inserting
    judgement headers.  It acts on the following SMTP commands:

    o RCPT TO:
        o Checks if the recipient address matches the key ham or spam
          addresses, and if so notes this and does not forward a command to
          the proxied server.  In all other cases simply passes on the
          verbatim command.

     o DATA:
        o Notes that we are in the data section.  If (from the RCPT TO
          information) we are receiving a ham/spam message to train on,
          then do not forward the command on.  Otherwise forward verbatim.

    Any other commands are merely passed on verbatim to the server.
    """

    def __init__(self, clientSocket, serverName, serverPort):
        SMTPProxyBase.__init__(self, clientSocket, serverName, serverPort)
        self.handlers = {'RCPT TO': self.onRcptTo, 'DATA': self.onData,
                         'MAIL FROM': self.onMailFrom}
        #self.trainer = trainer
        self.isClosed = False
        
        self.proxyHostname=serverName
        self.MAILDIR_ROOT=config.MAILDIR_ROOT_DIR

    def send(self, data):
        try:
            return SMTPProxyBase.send(self, data)
        except socket.error:
            # The email client has closed the connection - 40tude Dialog
            # does this immediately after issuing a QUIT command,
            # without waiting for the response.
            self.close()

    def close(self):
        # This can be called multiple times by async.
        if not self.isClosed:
            self.isClosed = True
            SMTPProxyBase.close(self)

    def stripAddress(self, address):
        """
        Strip the leading & trailing <> from an address.  Handy for
        getting FROM: addresses.
        """
        if '<' in address:
            start = string.index(address, '<') + 1
            end = string.index(address, '>')
            return address[start:end]
        else:
            return address

    def onTransaction(self, command, args):
        handler = self.handlers.get(command.upper(), self.onUnknown)
        return handler(command, args)

    def onProcessData(self, data):
        
        #currentMaildir=mailDir.MailDir(self.getMaildir(self.mailFrom))
        #currentMaildir.storeEmail(data)
        currentMaildir=mailDir.MailDir(config.MAILDIR_ROOT_DIR,self.proxyHostname,self.mailFrom.split('@')[0],'Sent')
        currentMaildir.storeEmail(data)
        
        return data


    def onRcptTo(self, command, args):
        self.mailTo = self.stripAddress(args[0])
        

        return "%s:%s" % (command, ' '.join(args))

    def onData(self, command, args):
        
        self.inData = True
        """
        if self.train_as_ham == True or self.train_as_spam == True:
            self.push("354 Enter data ending with a . on a line by itself\r\n")
            return None
        """
        print "onData"
        self.mailBody=command + ' ' + ' '.join(args)
        return command + ' ' + ' '.join(args)

    def onMailFrom(self, command, args):
        """Just like the default handler, but has the necessary colon."""
        
        mailsrch = re.compile(r'[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}')
        self.mailFrom=mailsrch.findall(' '.join(args))[0]
        
        rv = "%s:%s" % (command, ' '.join(args))
        return rv

    def onUnknown(self, command, args):
        """Default handler."""
        return self.request


def LoadServerInfo():
    # Load the proxy settings
    servers = []
    proxyPorts = []
    if options["smtpproxy", "remote_servers"]:
        for server in options["smtpproxy", "remote_servers"]:
            server = server.strip()
            if server.find(':') > -1:
                server, port = server.split(':', 1)
            else:
                port = '25'
            servers.append((server, int(port)))
    if options["smtpproxy", "listen_ports"]:
        splitPorts = options["smtpproxy", "listen_ports"]
        proxyPorts = map(_addressAndPort, splitPorts)
    if len(servers) != len(proxyPorts):
        print "smtpproxy:remote_servers & smtpproxy:listen_ports are " + \
              "different lengths!"
        sys.exit()
    return servers, proxyPorts

def CreateProxies(servers, proxyPorts, trainer):
    """Create BayesSMTPProxyListeners for all the given servers."""
    proxyListeners = []
    for (server, serverPort), proxyPort in zip(servers, proxyPorts):
        listener = BayesSMTPProxyListener(server, serverPort, proxyPort,
                                          trainer)
        proxyListeners.append(listener)
    return proxyListeners
    
    
# ===================================================================
# __main__ driver.
# ===================================================================
    
def run():
    listener = BayesSMTPProxyListener('mail.asix.com.my',25,8125)
    Dibbler.run()
    
def _addressPortStr((addr, port)):
    """Encode a string representing a port to bind to, with optional address."""
    if not addr:
        return str(port)
    else:
        return '%s:%d' % (addr, port)
    
def _createProxies(servers, proxyPorts):
    """Create BayesProxyListeners for all the given servers."""
    for (server, serverPort), proxyPort in zip(servers, proxyPorts):
        listener = BayesProxyListener(server, serverPort, proxyPort)
        proxyListeners.append(listener)

    

if __name__ == '__main__':
    run()
