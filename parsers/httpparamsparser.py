#!/usr/bin/python

import urlparse

class HttpParamsParser:

    def name(self):
        return self.__class__.__name__

    def check(self, data):
        try:
            self.parse(data)
            return True
        except ValueError:
            return False

    def parse(self, data):
        vals = urlparse.parse_qsl(data, True, True)
        out = []
        for val in vals:
            # Instead of using parameter values name too:
            #out[val[0]] = val[1]
            # go only with their values:
            out.append(val[1])

        return out


