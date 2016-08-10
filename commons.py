
import os
import re
import sys

DEBUG = True

def info(txt):
    sys.stderr.write(txt + '\n')

def warning(txt):
    info('[?] ' + txt)

def error(txt):
    info('[!] ' + txt)

def dbg(txt):
    if DEBUG:
        info('[dbg] '+txt)

