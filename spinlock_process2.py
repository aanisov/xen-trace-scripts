#!/bin/env python3
import re, sys, string, signal, struct, os, getopt
import functools
import statistics
import numpy

def sighand(x,y):
    global interrupted
    interrupted = True

signal.signal(signal.SIGTERM, sighand)
signal.signal(signal.SIGHUP,  sighand)
signal.signal(signal.SIGINT,  sighand)

interrupted = False

TRC_HW_IRQ = 0x00802000
TRC_AIRQ = (TRC_HW_IRQ + 0x800)
TRC_AIRQ_1 = (TRC_AIRQ + 0x1)
TRC_AIRQ_2 = (TRC_AIRQ + 0x2)
TRC_AIRQ_3 = (TRC_AIRQ + 0x3)
TRC_AIRQ_4 = (TRC_AIRQ + 0x4)
TRC_AIRQ_SPB = (TRC_AIRQ + 0x7)
TRC_AIRQ_SPA = (TRC_AIRQ + 0x8)
TRC_AIRQ_SPBU = (TRC_AIRQ + 0x9)
TRC_AIRQ_SPU = (TRC_AIRQ + 0xA)

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

syms = {}

def read_syms():
    global syms
    f = open("spinlock2/xen-syms.map", "rt")
    l = f.readline()
    while l:
        fields = l.split(" ")
        syms[fields[0][2:]] = (fields[2].strip())
        l = f.readline()

read_syms()

evts = {
    TRC_AIRQ_SPB: "TRC_AIRQ_SPB",
    TRC_AIRQ_SPA: "TRC_AIRQ_SPA",
    TRC_AIRQ_SPU: "TRC_AIRQ_SPU",
    TRC_AIRQ_SPBU: "TRC_AIRQ_SPBU",
    }

def format_evt(r):
    evt = r[1] & 0x0fffffff
    return "[%d][CPU:VCPU %d:%d] %s - %s" % (r[2], r[0], r[3], evts[evt], syms["%x"%r[4]])

def update_func_time(d, f, t, pcpu):
    if f not in d:
        d[f] = [[],[],[],[]]
    d[f][pcpu].append(t)

start_c = 0
end_c = 0
def main():
    global start_c, end_c

    trace = []
    cpuf = []
    cpu_change = 0

    cpu = None
    n = 0
    while not interrupted:
        n += 1
        if n > 500000:
            break

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
            data = [cpu] + list(s)
            trace.append(tuple(data))
    print("Reading done, sorting...");
    traces = sorted(trace, key = lambda s: s[2])

    vcpu_states = [(0,0), (0,0), (0,0), (0,0)]
    func_times_locked = {}
    func_times_total = {}
    func_times_wait = {}
    func_times_unlock_time = {}
    func_lock_now = {}
    func_unlock_now = {}
    func_try_now = {}

    for t in traces:
        if interrupted:
            break
        evt = t[1] & 0x0fffffff
        if evt in [TRC_AIRQ_1, TRC_AIRQ_2,  TRC_AIRQ_3, TRC_AIRQ_4]:
            continue
        if len(t)<5:
            print ("evt %X: %s"%(evt, str(t)))
#        if t[0] != t[3]:
#        print(format_evt(t))
        vcpu = t[3]
        tick = t[2]
        func = t[4]
        pcpu = t[0]

        if evt == TRC_AIRQ_SPA:
            # if vcpu_states[vcpu][0] == 3:
            #     print("%s get lock, waited: %d" % (format_evt(t), tick - vcpu_states[vcpu][1]))
            vcpu_states[vcpu] = (1, tick)
            if func not in func_lock_now:
                func_lock_now[func] = [0, 0, 0, 0]
            func_lock_now[func][vcpu] = tick
            update_func_time(func_times_wait, func, tick - func_try_now[func][vcpu], pcpu)

        if evt == TRC_AIRQ_SPBU:
            update_func_time(func_times_locked, func, tick - func_lock_now[func][vcpu], pcpu)
            if func not in func_unlock_now:
                func_unlock_now[func] = [0, 0, 0, 0]
            func_unlock_now[func][vcpu] = tick

        if evt == TRC_AIRQ_SPU:
            if vcpu_states[vcpu][0] == 1:
                vcpu_states[vcpu] = (0, tick)
            update_func_time(func_times_total, func, tick - func_try_now[func][vcpu], pcpu)
            update_func_time(func_times_unlock_time, func, tick - func_unlock_now[func][vcpu], pcpu)

        if evt == TRC_AIRQ_SPB:
            if vcpu_states[vcpu][0] == 1:
                #print("%s locked at %d (%d)"%(format_evt(t), vcpu_states[vcpu][1], tick - vcpu_states[vcpu][1]))
                vcpu_states[vcpu] = (3, tick)
            if func not in func_try_now:
                func_try_now[func] = [0, 0, 0, 0]
            func_try_now[func][vcpu] = tick

    start_c = traces[0][2]
    end_c = traces[-1][2]
    print("Total bytes processed: %d"%total)
    print("CPU changes: %d" % cpu_change)
    print("\nFunction locked stats (A to BU):")
    print_func_stat(func_times_locked)

    print("\nFunction total time stats (B to U):")
    print_func_stat(func_times_total)

    print("\nFunction spin_lock() stats (B to A):")
    print_func_stat(func_times_wait)

    print("\nFunction spin_unlock() (BU to U):")
    print_func_stat(func_times_unlock_time)


def print_hist(hist):
    m = max(hist[0])
    scale = 80 / m
    for i in range(len(hist[0])):
        print ("%6.2f %5d  |%s" %  (hist[1][i], hist[0][i], "*"  *  int(hist[0][i] * scale)))

def print_func_stat(d):
    print("%40s   Max     Min   Mean   Stdev    Total   Events   RunTime percent" % ("Function"))
    for pcpu in range (4):
        print ("\nPCPU %d" % pcpu)
        for f in d:
            data =  d[f][pcpu]
            total = sum(data)
            print("%40s %5d %5d    %6.4f %6.4f %6d   %6d      %f%%" % (syms["%x"%f],
                                       max(data),
                                       min(data),
                                       statistics.mean(data),
                                       statistics.stdev(data),
                                       total,
                                       len(data),
                                       total/(end_c - start_c) * 100))
            vals = list(set(data))
            vals.append(1000)
            #histogram = numpy.histogram(data, bins=sorted(vals))
            #print_hist(histogram)

if __name__ == "__main__":
    main()










