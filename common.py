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
    global done
    done = 1


signal.signal(0x02, sigint)
signal.signal(0x0f, sigint)
