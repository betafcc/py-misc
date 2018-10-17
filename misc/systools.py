import os
from subprocess import Popen, PIPE


def lines(cmd):
    '''
    Iterate shell comand output by line
    '''
    with Popen(
        cmd,
        shell=True,
        text=True,
        bufsize=1,
        stdout=PIPE,
    ) as process:
        yield from map(process_line, process.stdout)


def process_line(line):
    return line[:-1] if line[-1] == os.linesep else line
