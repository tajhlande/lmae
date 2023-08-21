import time
from functools import reduce


def measure_clock():
    t0 = time.clock()
    t1 = time.clock()
    while t1 == t0:
        t1 = time.clock()
    return t0, t1, t1-t0

reduce(lambda a,b: a+b, [measure_clock()[2] for i in range(1000000)] )/1000000.0
