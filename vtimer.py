#!/bin/env python3
from pcpu_split import next_rec, parse_rec, interrupted
import signal
import statistics
import itertools
import numpy

TRC_HW_IRQ = 0x00802000
TRC_XT = (TRC_HW_IRQ + 0x800)
TRC_XT_IRQ_START = (TRC_XT + 0x1)
TRC_XT_IRQ_END = (TRC_XT + 0x2)
TRC_XT_IRQ_CTXT_SW_START = (TRC_XT + 0x3)
TRC_XT_IRQ_CTXT_SW_END = (TRC_XT + 0x4)
TRC_XT_VIRT_TMR_SAVE_START = (TRC_XT + 0x5)
TRC_XT_VIRT_TMR_SAVE_END = (TRC_XT + 0x6)
TRC_XT_VIRT_TMR_RESTORE_START = (TRC_XT + 0x7)
TRC_XT_VIRT_TMR_RESTORE_END = (TRC_XT + 0x8)

def sighand(x,y):
    global interrupted
    interrupted = True

signal.signal(signal.SIGTERM, sighand)
signal.signal(signal.SIGHUP,  sighand)
signal.signal(signal.SIGINT,  sighand)

evt_str = {
    TRC_XT_IRQ_START:              "TRC_XT_IRQ_START",
    TRC_XT_IRQ_END:                "TRC_XT_IRQ_END",
    TRC_XT_IRQ_CTXT_SW_START:      "TRC_XT_IRQ_CTXT_SW_START",
    TRC_XT_IRQ_CTXT_SW_END:        "TRC_XT_IRQ_CTXT_SW_END",
    TRC_XT_VIRT_TMR_SAVE_START:    "TRC_XT_VIRT_TMR_SAVE_START",
    TRC_XT_VIRT_TMR_SAVE_END:      "TRC_XT_VIRT_TMR_SAVE_END",
    TRC_XT_VIRT_TMR_RESTORE_START: "TRC_XT_VIRT_TMR_RESTORE_START",
    TRC_XT_VIRT_TMR_RESTORE_END:   "TRC_XT_VIRT_TMR_RESTORE_END",
}

def add_time_stat(k, s, val):
    if val < 0:
        print("Events in wrong order!")
        return False
    if k not in s:
        s[k] = []
    s[k].append(val)
    return True

def update_last_evt(d, evt, tsc):
    if evt not in d:
        d[evt] = 0
    d[evt] = tsc

tsc_start = None
tsc_end = None

def main():
    global tsc_start, tsc_end
    n = 0

    ctx_switch_to = {}

    last_evt = {}
    while not interrupted:
        n += 1
        if n > 100000000:
            break

        ret = next_rec()
        if ret == None:
            break

        rec, tsc_in = ret
        evt, s = parse_rec(rec, tsc_in)

        tsc = s[1]
        if not tsc_start:
            tsc_start = tsc
        tsc_end = tsc

        try:
            if evt == TRC_XT_IRQ_END:
                k = "irq_inject"
                add_time_stat(k, ctx_switch_to, tsc - last_evt[TRC_XT_IRQ_START])

            if evt == TRC_XT_IRQ_CTXT_SW_START:
                k = "ctx_sw"
                add_time_stat(k, ctx_switch_to, tsc - last_evt[TRC_XT_IRQ_CTXT_SW_END])

            if evt == TRC_XT_VIRT_TMR_SAVE_START:
                k = "vtimer_save"
                add_time_stat(k, ctx_switch_to, tsc - last_evt[TRC_XT_VIRT_TMR_SAVE_END])

            if evt == TRC_XT_VIRT_TMR_RESTORE_START:
                k = "vtimer_restore"
                add_time_stat(k, ctx_switch_to, tsc - last_evt[TRC_XT_VIRT_TMR_RESTORE_END])

        except KeyError:
            print

        update_last_evt(last_evt, evt, tsc)

    print("Total: %d events\n" % n)
    print("%20s   Max     Min         Mean        Stdev       Total      Events   RunTime percent" % ("IRQ/Event"))
    print_times("", ctx_switch_to)

def print_stat(name, data):
    if len(data) == 0:
        print("%20s ===================== NO DATA ======================"%name)
        return
    total = sum(data)
    print("%20s %7d %5d    %12.4f %12.4f %10d   %7d      %f%%" % (name,
                                                                     max(data),
                                                                     min(data),
                                                                     statistics.mean(data),
                                                                     statistics.stdev(data),
                                                                     total,
                                                                     len(data),
                                                                     total/(tsc_end - tsc_start) * 100))

def print_times(name, d):
    print(name)
    gt = []
    for k in d.keys():
        print_stat(k, d[k])
        gt += d[k]
    print_stat("(total)", gt)
    for k in d.keys():
        print_hist(k, d[k])

def print_hist(name, data):
    vals = list(set(data))
    vals.append(max(vals) + 1)

    if len (vals) < 40:
        hist = numpy.histogram(data, bins = sorted(vals))
    else:
        hist = numpy.histogram(data, bins = 40)

    m = max(hist[0])
    scale = 120 / m
    print("%s" % name)
    for i in range(len(hist[0])):
        print ("%12.2f %5d  |%s" %  (hist[1][i], hist[0][i], "*"  *  int(hist[0][i] * scale)))

if __name__ == "__main__":
    main()








