#!/usr/bin/python

import math
import time
import urllib
import signal
import tempfile
import datetime
import itertools
from hasher import *
from commons import *
from myexceptions import *
from functools import partial
from timeit import default_timer as timer
from multiprocessing.managers import BaseManager


def init_worker():
    # http://stackoverflow.com/a/6191991
    signal.signal(signal.SIGINT, signal.SIG_IGN)


# In order to make this worker function picklable, it must be defined
# in the top-level of a module, instead of a static method within HashCollider
# class.
def hash_collider_worker(stopevent, hasher, inputs):
    if not inputs or len(inputs) == 0:
        return False
    if stopevent.is_set():
        return False
    if hasher.check(inputs):
        stopevent.set()
        return inputs

    return False


class HashCollider:

    hasher = None
    parsers = {}
    elements = set()
    separators = ['', '+', '|', '.']
    tmpfile = None

    def __init__(self, hasher, dictonary_outfile=None):
        self.hasher = hasher
        self.register_parsers()
        if dictonary_outfile == None:
            self.tmpfile = tempfile.NamedTemporaryFile(delete=True)
        else:
            dbg("Using custom provided file as working storage = '%s'" % dictonary_outfile)
            self.tmpfile = open(dictonary_outfile, 'w+')


    def load_parser(self, parser):
        def import_file(full_path_to_module):
            # Partially from: http://stackoverflow.com/a/68628
            module_dir, module_file = os.path.split(full_path_to_module)
            module_name, _ = os.path.splitext(module_file)
            sys.path.append(module_dir)
            return __import__(module_name)

        parser_name = os.path.splitext(os.path.basename(parser))[0].lower()
        if not parser_name in [x.lower() for x in self.parsers.keys()]:
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
            
        newelements = set()
        if isinstance(parsed, list) or isinstance(parsed, tuple):
            newelements.update(parsed)
        elif isinstance(parsed, basestring) or isinstance(parsed, int) or isinstance(parsed, float):
            newelements.add(str(parsed))
        elif isinstance(parsed, dict):
            for k, v in parsed.items():
                newelements.add(k)
                newelements.add(v)
        else:
            assert False, "Unrecognized `parsed` data type."

        dbg("Fed collider with %d new elements" % (len(newelements)))

        self.elements.update(newelements)
        dbg("Entire elements list:\n---\n\t%s\n---\n" % self.print_elements())

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
        # It goes like this:
        #   for i..n do
        #       sum := sum + V(n, i)
        #
        items = self.elements
        def V(n, k):
            return math.factorial(n)/math.factorial(n-k)
        return sum(map(lambda x: V(len(items), x), range(len(items))))


    def generate_combinations(self):
        def permutations(items):
            for i in range(len(items)):
                yield itertools.permutations(items, i)
        
        num = 0
        to_generate = self.number_of_permutations()
        step = max(to_generate / 20000, 20000)
        self.tmpfile.seek(0,0)

        for comb in permutations(self.elements):
            for p in comb:
                for sep in self.separators:
                    num += 1
                    element = sep.join([str(c) for c in p]) + '\n'

                    if num % step == 0:
                        sys.stdout.write("\r{:3.5f}% generated so far...".format(100 * float(num) / float(to_generate)))
                    
                    # Tried to optimize this particular way of storing elements
                    # by firstly buffering them into a list of size being 1% of total
                    # samples count or 1500, and then using join storing them at once,
                    # but this resulted in suffered performance by more than 40%.
                    self.tmpfile.write(element)

                self.tmpfile.flush()

        self.tmpfile.flush()

        sys.stdout.write('\n')
        return num


    def print_result(self, data):
        return '%s("%s") == "%s"' % (self.hasher.hashing_algo().name, data, self.hasher.data)


    def prepare_dictonary_file(self):

        info("Generating about %d samples out of %d elements..." % \
            (len(self.separators) * self.number_of_permutations(), len(self.elements)))

        generated_samples = 0
        try:
            before1 = timer()
            generated_samples = self.generate_combinations()
            dur1 = timer() - before1
            dbg("Samples generation phase took {}.{:03d}".format(
                str(datetime.timedelta(seconds=int(dur1))), int((dur1 % 1)*1000)))

        except KeyboardInterrupt:
            error("User has interrupted combinations generation phase.")
            warning("Proceeding with collected elements instead of their combinations")

        except IOError, e:
            if 'No space left on device' in str(e):
                error("Couldn't generate an entire dictonary file. Quitting...")
                error("Please specify in options a different path for working file.")
                return False
            else:
                raise

        if generated_samples == 0:
            error("No input data to work on, no generated dictionary")
            return False

        return generated_samples


    def collide(self):

        generated_samples = self.prepare_dictonary_file()
        if not generated_samples:
            return False

        info("\nEngaging hashing loop over %d candidates with %d workers. Stay tight." 
            % (generated_samples, WORKERS))

        pool = multiprocessing.Pool(WORKERS, init_worker)
        manager = multiprocessing.Manager()
        stopevent = manager.Event()
        func = partial(hash_collider_worker, stopevent, self.hasher)

        processed_elements = 0
        step = max(5000, int(generated_samples / 20000))
        taskssum = 0
        taskscount = 0
        finished_tasks = 0

        before2 = timer()
        try:
            while processed_elements < generated_samples:

                elements = []
                self.tmpfile.seek(0,0)

                for i, line in enumerate(self.tmpfile):
                    if len(line.strip()) == 0:
                        continue

                    if i >= processed_elements and i < (processed_elements + step):
                        # [:-1] stands for stripping only the very last LF 
                        # that was appended by the generator
                        elements.append(line[:-1])

                    if i >= (processed_elements + step):
                        break

                if len(elements) == 0:
                    #dbg("\nRan out of samples. Fininshing.")
                    break

                results = pool.map_async(func, elements)

                numleft = results._number_left
                taskssum += numleft
                taskscount += 1
                total = (taskssum / taskscount) * (generated_samples / step)

                while True:
                    if results.ready():
                        break
                    left = finished_tasks + numleft
                    perc = float(left) / float(total) * 100.0
                    sys.stdout.write("\r{:3.5f}% done (task={}, total={}).".format(perc, left, total))

                processed_elements += step
                finished_tasks += numleft

                result = False
                for r in results.get():
                    if r:
                        result = r

                if result:
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    break

        except KeyboardInterrupt:
            stopevent.set()
            pool.terminate()
            pool.join()
            error("User has interrupted collisions loop.")
            return False

        if result:
            info("\n\033[0;32m[+] FOUND COLLISION:\033[1;0m\n\t\033[0;33m%s\033[1;0m" % (self.print_result(result)))
        else:
            warning("Could not find a collision from provided data.")

        dur2 = timer() - before2
        dbg("\nHash collision lookup took in total: {}.{:03d}".format(
            str(datetime.timedelta(seconds=int(dur2))), int((dur2 % 1)*1000)))

        return result
        


def main():
    global main_hasher

    info('\n\t\033[0;32mHash-Collider - looking for hash collision from permutations of input data\033[1;0m')
    info('\033[0;33m\tMariusz B. / mgeeky, 2016\033[1;0m\n')

    if len(sys.argv) < 2:
        warning('Usage: hash-collider <hash>')
        sys.exit(0)

    data = sys.argv[1]
    main_hasher = Hasher(data)

    fil = '/root/vmshared/out.txt'
    #fil = None
    collider = HashCollider(main_hasher, fil)

    d = raw_input("Data: ")
    collider.feed(d)
    try:
        info("Hash-colliding started at: " + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p"))

        before = timer()
        collider.collide()
        info("\nHash-colliding finished at: " + datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p"))

        dur = timer() - before
        info("\tProgram took roughly: {}.{:03d}".format(
            str(datetime.timedelta(seconds=int(dur))), int((dur % 1)*1000)))
    except KeyboardInterrupt:
        warning("User has interrupted hash collisions process.")


if __name__ == '__main__':
    main()
