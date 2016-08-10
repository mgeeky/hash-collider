#!/usr/bin/python

import re
import sys
import urllib
import urlparse
import hashlib


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

class Hasher:
    hashlens = {}
    hashing_algo = None
    checks = 0
    
    def __init__(self, data):
        self.init_hash_lens
        self.set_hash(data)

    def init_hash_lens(self):
        for algo in hashlib.algorithms:
            hashlens[algo] = len(hashlib.__get_builtin_constructor(algo)('test').hexdigest())

    def get_hash(self):
        return self.data

    def set_hash(self, data):
        self.data = data
        self.hashing_algo = None
        self.get_algo()
        if DEBUG:
            for a, l in self.hashlens.items():
                if l == len(self.data):
                    dbg('Specified hash seems to be: %s' % a)

    def get_algo(self):
        if not self.hashing_algo:
            for a, l in self.hashlens.items():
                if l == len(self.data):
                    self.hashing_algo = hashlib.__get_builtin_constructor(a)
        return self.hashing_algo

    def hashit(self, data):
        return self.get_algo()(data).hexdigest()

    def check(self, data):
        self.checks += 1
        return self.data == self.hashit(data)

class HttpRequestParser:
    name = 'HttpRequestParser'

    def check(self, data):
        return False

    def parse(self, data):
        return None

class DateTimestampParser:
    name = 'HttpRequestParser'

    def check(self, data):
        return False

    def parse(self, data):
        return None


class HttpParamsParser:
    name = 'HttpParamsParser'

    def check(self, data):
        try:
            self.parse(data)
            return True
        except ValueError:
            return False

    def parse(self, data):
        vals = urlparse.parse_qsl(data, True, True)
        out = {}
        for val in vals:
            out[val[0]] = val[1]
        return out


class HashCollider:
    hasher = None
    elements = set()
    parsers = []

    def __init__(self, data):
        hasher = Hasher(data)

    def register_parser(self, parser):
        if hasattr(parser, 'check'):
            if hasattr(parser, 'parse'):
                if hasattr(parser, 'name'):
                    dbg("Registering new parser: %s" % parser.name)
                    self.parsers.append(parser)
                else:
                    assert False, "Parser registration failed: no `name` attribute found"
            else:
                assert False, "Parser registration failed: no `parse()` method found"
        else:
            assert False, "Parser registration failed: no `check()` method found"

    def print_elements(self):
        out = ''
        for e in self.elements:
            out += '"{}", '.format(e)
        return out

    def feed(self, element):
        parsed = self.parse(element)
        l1 = len(self.elements)

        if isinstance(parsed, list):
            self.elements.update(parsed)
        elif isinstance(parsed, basestring):
            self.elements.add(parsed)
        elif isinstance(parsed, dict):
            for k, v in parsed.items():
                self.elements.add(k)
                self.elements.add(v)
        else:
            assert False, "Unrecognized `parsed` data type."

        dbg("Fed collider with %d new elements" % (len(self.elements) - l1))
        dbg("\n--- Elements list:\n\t%s\n---\n" % self.print_elements())


    def parse(self, data):
        for parser in self.parsers:
            if parser.check(data):
                dbg("Parser %s agreed to process: ['%s']..." % (parser.name, data[:64]))
                return parser.parse(data)


def main():
    info('\n\tHash-Collider - looking for hash collision from permutations of input data')
    info('\tMariusz B. / mgeeky, 2016\n')

    if len(sys.argv) < 2:
        warning('Usage: hash-collider <hash>')
        sys.exit(0)

    data = sys.argv[1]
    collider = HashCollider(data)
    collider.register_parser(HttpParamsParser())

    d = raw_input("Data: ")
    collider.feed(d)

if __name__ == '__main__':
    main()
