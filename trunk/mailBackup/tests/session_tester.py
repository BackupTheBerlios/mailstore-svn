import getpass, poplib,thread,time

userpassDict={'email@mail.com':'password'}

def establishConnection(username,password):
    M = poplib.POP3('localhost',8110)
    time.sleep(5)

    M.user(username)
    M.pass_(password)
    
    numMessages = len(M.list()[1])
    print username,numMessages

for username,password in userpassDict.items():
    thread.start_new_thread(establishConnection,(username,password,))
    #thread.start_new_thread(test,(1,))
    time.sleep(2)
    #establishConnection(username,password)

#for i in range(numMessages):
#    for j in M.retr(i+1)[1]:
#        print j
