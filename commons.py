
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
    info("\033[1;35m[?] %s\033[1;0m" % txt)

def error(txt):
    info("\033[1;41m[!] %s\033[1;0m" % txt)

def dbg(txt):
    if DEBUG:
        info("\033[1;32m[dbg] %s\033[1;0m" % txt)

