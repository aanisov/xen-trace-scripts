#!/bin/env python3
import re, sys, string, signal, struct, os, getopt
import functools

def sighand(x,y):
    global interrupted
    interrupted = True

signal.signal(signal.SIGTERM, sighand)
signal.signal(signal.SIGHUP,  sighand)
signal.signal(signal.SIGINT,  sighand)

interrupted = False

HDRREC = "=I"
TSCREC = "Q"
D1REC  = "I"
D2REC  = "II"
D3REC  = "III"
D4REC  = "IIII"
D5REC  = "IIIII"
D6REC  = "IIIIII"
D7REC  = "IIIIIII"

no_tsc =    [None,
             HDRREC,
             HDRREC + D1REC,
             HDRREC + D2REC,
             HDRREC + D3REC,
             HDRREC + D4REC,
             HDRREC + D5REC,
             HDRREC + D6REC,
             HDRREC + D7REC]
with_tsc = [None,
            HDRREC,
            None,
            HDRREC + TSCREC,
            HDRREC + TSCREC + D1REC,
            HDRREC + TSCREC + D2REC,
            HDRREC + TSCREC + D3REC,
            HDRREC + TSCREC + D4REC,
            HDRREC + TSCREC + D5REC,
            HDRREC + TSCREC + D6REC,
            HDRREC + TSCREC + D7REC]

total = 0
def next_rec():
    global total
    line = sys.stdin.buffer.read(struct.calcsize(HDRREC))
    if not line:
        print("1111")
        return None

    event = struct.unpack(HDRREC, line)[0]
    n_data = event >> 28 & 0x7
    tsc_in = event >> 31
    to_read = struct.calcsize(D1REC) * n_data
    if tsc_in == 1:
        to_read += struct.calcsize(TSCREC)
    data = sys.stdin.buffer.read(to_read)
    # if not data:
    #     print("2222, %d"% to_read)
    #     return None

    total += len(line) + len(data)
    return (line + data, tsc_in)

@functools.lru_cache(maxsize=32)
def get_format(l, tsc_in):
    l = l//4
    if tsc_in == 0:
        return no_tsc[l]
    else:
        return with_tsc[l]

def parse_rec(rec, tsc_in):
    f = get_format(len(rec), tsc_in)
    if f is None:
        print("bwaaaah")
    s = struct.unpack(f, rec)
    evt = s[0] & 0x0fffffff
    if evt == 0x1f001:
        print("Events lost!")
    if evt == 0x1f002:
        print("Wrap buffer")
    # if tsc_in:
    #     s = list(s)
    #     s[1] = s[1] * 1000 / 8.333
    #     s = tuple(s)
    return evt, s

def main():
    cpuf = []
    cpu_change = 0
    for x in range(4):
        cpuf.append(open("cpu%d.bin"%x, "wb"))

    cpu = None
    while not interrupted:
        ret = next_rec()
        if ret == None:
            break
        rec, tsc_in = ret
        evt, s = parse_rec(rec, tsc_in)
        if evt == 0x1f003:
            cpu = s[1]
            cpu_change += 1

        if evt & 0x0ffff000 != 0x0001f000:
            if cpu is None:
                print("event for unknown CPU!")
            cpuf[cpu].write(rec)

    print("Total bytes processed: %d"%total)
    print("CPU changes: %d\n" % cpu_change)
if __name__ == "__main__":
    main()










