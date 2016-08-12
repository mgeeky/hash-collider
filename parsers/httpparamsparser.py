#!/usr/bin/python

import urlparse
from commons import *

class HttpParamsParser:

    def name(self):
        return self.__class__.__name__

    def check(self, data):
        if '&' not in data or '=' not in data:
            return False

        try:
            self.parse(data)
            return True
        except ValueError:
            return False

    def parse(self, data, more=False):
        vals = urlparse.parse_qsl(data, True, True)
        out = []
        for val in vals:
            if more:
                out[val[0]] = val[1]
            else:
                out.append(val[1])

        return out


