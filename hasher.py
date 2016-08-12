
import hashlib
from commons import *


class Hasher:

    hashlens = {}
    hashing_algo = None
    lock = multiprocessing.Lock()
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
                    with self.lock:
                        self.hashing_algo = getattr(hashlib, a)
        return self.hashing_algo

    def hashit(self, data):
        return self.get_algo()(data).hexdigest()

    def check(self, data):
        return self.data == self.hashit(data)


