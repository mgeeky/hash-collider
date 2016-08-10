#!/usr/bin/python

import urlparse

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


