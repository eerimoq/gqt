import sys
import time

from rich.console import Console
from rich.progress import Progress

def main():
    with Progress(console=Console(file=sys.stderr)) as progress:
        task = progress.add_task("Test", total=2)
        time.sleep(0.5)
        progress.update(task, advance=1)
        time.sleep(0.5)
        progress.update(task, advance=1)
        time.sleep(0.5)
