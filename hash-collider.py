#!/usr/bin/python

import math
import time
import urllib
import signal
import hashlib
import itertools
import multiprocessing
from commons import *
from myexceptions import *
from functools import partial
from multiprocessing.managers import BaseManager

try:
    import importlib
except ImportError:
    raise ImportError("Could not import `importlib` module. Try with: pip install importlib")

WORKERS = multiprocessing.cpu_count() * 4
main_hasher = None

def init_worker():
    # http://stackoverflow.com/a/6191991
    signal.signal(signal.SIGINT, signal.SIG_IGN)


# In order to make this worker function picklable, it must be defined
# in the top-level of a module, instead of a static method within HashCollider
# class.
def hash_collider_worker(stopevent, hasher, inputs):
    if not inputs or len(inputs) == 0:
        return False

    for i in range(len(inputs)):
        inp = inputs[i]
        if stopevent.is_set():
            return False
        if hasher.check(inp):
            stopevent.set()
            return inp
    return False

class Hasher:
    hashlens = {}
    hashing_algo = None
    incr_lock = multiprocessing.Lock()
    checks = 0
    
    def __init__(self, data):
        self.init_hash_lens()
        self.set_hash(data)

    def init_hash_lens(self):
        for algo in hashlib.algorithms:
            self.hashlens[algo] = len(getattr(hashlib, algo)('test').hexdigest())

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
                    with self.incr_lock:
                        self.hashing_algo = getattr(hashlib, a)
        return self.hashing_algo

    def hashit(self, data):
        return self.get_algo()(data).hexdigest()

    def check(self, data):
        with self.incr_lock:
            self.checks += 1
        return self.data == self.hashit(data)


class HashCollider:
    hasher = None
    elements = set()
    parsers = {}
    separators = ['', '+', '|', '.']

    def __init__(self, hasher):
        self.hasher = hasher
        self.register_parsers()
        dbg("Dealing with data hashed using %s" % self.hasher.hashing_algo().name )

    def load_parser(self, parser):
        def import_file(full_path_to_module):
            # Partially from: http://stackoverflow.com/a/68628
            module_dir, module_file = os.path.split(full_path_to_module)
            module_name, _ = os.path.splitext(module_file)
            sys.path.append(module_dir)
            return __import__(module_name)

        parser_name = os.path.splitext(os.path.basename(parser))[0].lower()
        if not parser_name in [x.lower() for x in self.parsers.keys()]:
            dbg("Loading parser: '%s'" % parser)
            mod = import_file(parser)
            for objs in mod.__dict__.keys():
                if 'Parser' in objs:
                    dbg("Found parser's definition: %s" % objs)
                    self.register_parsers(getattr(mod, objs)())


    def register_parsers(self, parsers=None):
        def _register_parser(parser):
            if hasattr(parser, 'check'):
                if hasattr(parser, 'parse'):
                    if hasattr(parser, 'name'):
                        dbg("Registering new parser: %s" % parser.name())
                        self.parsers[parser.name()] = parser
                    else:
                        raise InvalidParserException, "Parser registration failed: no `name` attribute found"
                else:
                    raise InvalidParserException, "Parser registration failed: no `parse()` method found"
            else:
                raise InvalidParserException, "Parser registration failed: no `check()` method found"

        if parsers == None:
            # Registering all of the available parsers.
            currpath = os.path.dirname(os.path.realpath(__file__))
            modules_path = os.path.join(currpath, 'parsers')
            for top, _, parsers in os.walk(modules_path):
                map(self.load_parser, map(lambda x: os.path.join(top, x), parsers))

        else:
            if isinstance(parsers, list):
                map(_register_parser, parsers)
            else:
                _register_parser(parsers)

    def print_elements(self):
        out = ''
        for e in self.elements:
            out += '"{}", '.format(e)
        return out

    def feed(self, element, parser=None):
        try:
            parsed = self.parse(element, parser)
        except ParserNotFoundException:
            warning("Could not parse input data.")
            return False
            
        l1 = len(self.elements)

        if isinstance(parsed, list) or isinstance(parsed, tuple):
            self.elements.update(parsed)
        elif isinstance(parsed, basestring) or isinstance(parsed, int) or isinstance(parsed, float):
            self.elements.add(str(parsed))
        elif isinstance(parsed, dict):
            for k, v in parsed.items():
                self.elements.add(k)
                self.elements.add(v)
        else:
            assert False, "Unrecognized `parsed` data type."

        dbg("Fed collider with %d new elements" % (len(self.elements) - l1))
        dbg("\n--- Elements list:\n\t%s\n---\n" % self.print_elements())

        return True


    def parse(self, data, parser1=None):
        if not parser1:
            for parser_name, parser in self.parsers.items():
                if parser.check(data):
                    dbg("Parser %s agreed to process: ['%s']..." % (parser_name, data[:64]))
                    return parser.parse(data)

            raise ParserNotFoundException
        else:
            return parser1.parse(data)

    def number_of_permutations(self):
        # Permutations without repetitions
        items = self.elements
        def V(n, k):
            return math.factorial(n)/math.factorial(n-k)
        return sum(map(lambda x: V(len(items), x), range(len(items))))

    def generate_combinations(self):
        def permutations(items):
            for i in range(len(items)):
                yield itertools.permutations(items, i)
        
        elements = set()
        for comb in permutations(self.elements):
            for p in comb:
                for sep in self.separators:
                    elements.add(sep.join([str(c) for c in p]))

        return elements

    def print_result(self, data):
        return '%s("%s") == "%s"' % (self.hasher.hashing_algo().name, data, self.data)

    def collide(self):
        warning("Generating about %d samples out of %d elements" % \
            (len(self.separators) * self.number_of_permutations(), len(self.elements)))

        elements = None
        try:
            elements = self.generate_combinations()
        except KeyboardInterrupt:
            error("User has interrupted combinations generation phase.")
            warning("Proceeding with collected elements instead of their combinations")
            elements = self.elements

        if len(elements) == 0:
            error("No input data to work on, no generated dictionary")
            return False

        warning("Engaging hashing loop over %d candidates with %d workers. Stay tight." % (len(elements), WORKERS))

        pool = multiprocessing.Pool(WORKERS, init_worker)
        manager = multiprocessing.Manager()
        stopevent = manager.Event()
        func = partial(hash_collider_worker, stopevent, self.hasher)
        try:
            results = pool.map_async(func, elements)
            pool.close()

            while True:
                if results.ready():
                    break
                sys.stdout.write("\r{0:%} done.".format((float(results._number_left)/float(len(elements)))))
                time.sleep(0.5)

        except KeyboardInterrupt:
            pool.terminate()
            pool.join()
            error("User has interrupted collisions loop.")
            return False

        result = False
        for r in results.get():
            if r:
                result = r

        if result:
            info("[+] Got it: %s" % self.print_result(result))    
        else:
            warning("Could not find a collision from provided data.")

        return result
        


def main():
    global main_hasher

    info('\n\tHash-Collider - looking for hash collision from permutations of input data')
    info('\tMariusz B. / mgeeky, 2016\n')

    if len(sys.argv) < 2:
        warning('Usage: hash-collider <hash>')
        sys.exit(0)

    data = sys.argv[1]
    main_hasher = Hasher(data)
    collider = HashCollider(main_hasher)

    d = raw_input("Data: ")
    collider.feed(d)
    collider.collide()


if __name__ == '__main__':
    main()
