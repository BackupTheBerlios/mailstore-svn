#setup the global state variable which will be used a a way of maintaining
# state related data across the proxies
class State:
    def __init__(self):
        self.totalSessions=0
        self.activeSessions=0

state=State()
