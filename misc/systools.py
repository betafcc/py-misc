import os
from subprocess import Popen, PIPE, CalledProcessError
from concurrent.futures import ThreadPoolExecutor as Pool


def lines(cmd):
    """
    Iterate shell comand output by line
    """
    with Popen(cmd, shell=True, text=True, bufsize=1, stdout=PIPE) as process:
        yield from map(process_line, process.stdout)


def process_line(line):
    return line[:-1] if line[-1] == os.linesep else line


def pipe_iter(it, command):
    """
    Pipe each item in ``it`` as a line to stdin of
    a subprocess shell called with ``command``
    """
    with Popen(
        command, shell=True, text=True, stdin=PIPE, stdout=PIPE, stderr=PIPE
    ) as process, Pool(max_workers=2) as executor:
        # keep stderr
        stderr = executor.submit("".join, process.stderr)
        executor.submit(_write_each, it, process.stdin)

        try:
            yield from map(process_line, process.stdout)
        except:
            process.kill()
            raise

        retcode = process.poll()
        if retcode:
            raise CalledProcessError(retcode, process.args, stderr=stderr.result())


def _write_each(it, fp):
    for el in it:
        fp.write(str(el))
        fp.write(os.linesep)
        fp.flush()
    fp.close()
