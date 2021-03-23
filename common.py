import signal


class Writer:

    def __init__(self, name: str):
        self.name = name
        self.f = open(self.name, 'w')

    def line(self, line: str):
        self.f.write(line)
        self.f.write('\n')


done = 0


def sigint(*args, **kwargs):
    globals()['done'] = 1


signal.signal(signal.SIGINT, sigint)
signal.signal(signal.SIGTERM, sigint)
