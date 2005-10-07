import pop3_proxy
import smtp_proxy
import config
import Dibbler

#from EmailSearchFrontend import EmailSearchFrontend

#start the smtp proxies

if len(config.SMTP_PROXY) > 0:

    for smtp_proxy_config in config.SMTP_PROXY:
        listener = smtp_proxy.BayesSMTPProxyListener(smtp_proxy_config[0],smtp_proxy_config[1],smtp_proxy_config[2])
    

#start the POP proxies

if len(config.POP_PROXY) > 0:

    for pop_proxy_config in config.POP_PROXY:
        listener = pop3_proxy.BayesProxyListener(pop_proxy_config[0],pop_proxy_config[1],pop_proxy_config[2])

#httpServer = Dibbler.HTTPServer(8081)
#httpServer.register(EmailSearchFrontend())

Dibbler.run()
    
