import locale
import subprocess
from itertools import takewhile


def shell(cmd, encoding=None):
    if encoding is None:
        encoding = locale.getpreferredencoding(False)

    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    return map(
        lambda line: line.decode(encoding).rstrip("\n"),
        takewhile(
            lambda line: len(line) != 0 or process.poll() == None,
            iter(process.stdout.readline, False),
        ),
    )
