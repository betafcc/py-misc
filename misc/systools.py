import io
import subprocess


def shell(cmd, *args, **kwargs):
    return io.TextIOWrapper(
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout,
        *args,
        **kwargs,
    )
