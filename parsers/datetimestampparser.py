#!/usr/bin/python

from commons import *

class DateTimestampParser:

    def name(self):
        return self.__class__.__name__

    def check(self, data):
        return False

    def parse(self, data):
        return None


