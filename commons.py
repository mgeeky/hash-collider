
import os
import re
import sys
import multiprocessing

DEBUG = True
WORKERS = multiprocessing.cpu_count() * 4
main_hasher = None


def info(txt):
    sys.stderr.write(txt + '\n')

def warning(txt):
    info('[?] ' + txt)

def error(txt):
    info('[!] ' + txt)

def dbg(txt):
    if DEBUG:
        info('[dbg] '+txt)

