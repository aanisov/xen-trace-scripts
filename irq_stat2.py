#!/bin/env python3
from pcpu_split import next_rec, parse_rec, interrupted
import signal
import statistics
import itertools

TRC_HW_IRQ = 0x00802000
TRC_AIRQ = (TRC_HW_IRQ + 0x800)
TRC_AIRQ_1 = (TRC_AIRQ + 0x1)
TRC_AIRQ_2 = (TRC_AIRQ + 0x2)
TRC_AIRQ_3 = (TRC_AIRQ + 0x3)
TRC_AIRQ_4 = (TRC_AIRQ + 0x4)
TRC_AIRQ_5 = (TRC_AIRQ + 0x5)
TRC_AIRQ_6 = (TRC_AIRQ + 0x6)
TRC_AIRQ_7 = (TRC_AIRQ + 0x7)
TRC_AIRQ_8 = (TRC_AIRQ + 0x8)
TRC_AIRQ_9 = (TRC_AIRQ + 0x9)

def sighand(x,y):
    global interrupted
    interrupted = True

signal.signal(signal.SIGTERM, sighand)
signal.signal(signal.SIGHUP,  sighand)
signal.signal(signal.SIGINT,  sighand)

evt_str = {
    TRC_AIRQ_1: "TRC_AIRQ_1",
    TRC_AIRQ_2: "TRC_AIRQ_2",
    TRC_AIRQ_3: "TRC_AIRQ_3",
    TRC_AIRQ_4: "TRC_AIRQ_4",
    TRC_AIRQ_5: "TRC_AIRQ_5",
    TRC_AIRQ_6: "TRC_AIRQ_6",
    TRC_AIRQ_6: "TRC_AIRQ_7",
    TRC_AIRQ_6: "TRC_AIRQ_8",
    TRC_AIRQ_6: "TRC_AIRQ_9",
    }

irq_stats = {}
def add_irq_stat(num, time):
    global irq_stats

    if num is None:
        num = 1023

    if num not in irq_stats:
        irq_stats[num] = []
    irq_stats[num].append(time)

def print_irq_stack(stack):
    for x in stack:
        print ("   IRQ %s : %s (%d)"%(x[1], x[0], x[2]))

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

def process_irq_from_stack(irq_stack, tsc):
    if len(irq_stack) == 0:
        return
    irq = irq_stack.pop()
    #            if len(irq_stack) == 0:
    t = tsc - irq[0] - irq[2]
    add_irq_stat(irq[1], t)
    if t > 41134:
        print(tsc, irq[0], irq[1])
    for irq in irq_stack:
            irq[2] += t

def main():
    global tsc_start, tsc_end
    n = 0
    irq_stack = []

    whole_ctx_switch = {}
    ctx_switch_from = {}
    ctx_switch_to = {}
    ctx_switch_rem = {}

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

#        print(n, evt_str[evt], s, irq_stack)
        if evt == TRC_AIRQ_1:
            irq_stack.append([tsc, None, 0])

        if evt == TRC_AIRQ_2:
            irqn = s[3]
            if irqn == 1023:
                continue
            if irq_stack[-1][1] != None:
#                print("Some stupid problem at %d"%tsc)
                continue

            irq_stack[-1][1] = irqn
            if len(irq_stack) > 3:
                   print ("%d nested interrupts:"%len(irq_stack))
                   print_irq_stack(irq_stack)

        if evt == TRC_AIRQ_3:
            if len(irq_stack) > 1:
                print("[3]More interrupts in stack")
                print_irq_stack(irq_stack)

            while len(irq_stack) != 0:
                process_irq_from_stack(irq_stack, tsc)

        if evt == TRC_AIRQ_4:
            if len(irq_stack) > 1:
                print("[4]More interrupts in stack")
                print_irq_stack(irq_stack)

            while len(irq_stack) != 0:
                if irq_stack[-1][1] == 151:
                    print("Going to idle:", irq_stack[-1])
                process_irq_from_stack(irq_stack, tsc)

        if evt == TRC_AIRQ_6:
            process_irq_from_stack(irq_stack, tsc)

        if evt == TRC_AIRQ_7:
            if len(s) > 3:
                k = "%08x - %08x" % (s[3], s[2])
                add_time_stat(k, ctx_switch_from, tsc - last_evt[TRC_AIRQ_5])
            else:
                print("BAD!", s)

        if evt == TRC_AIRQ_8:
            k = "%08x - %08x" % (s[3], s[2])
            add_time_stat(k, ctx_switch_to, tsc - last_evt[TRC_AIRQ_7])

        if evt == TRC_AIRQ_9:
            k = "%08x - %08x" % (s[3], s[2])
            add_time_stat(k, ctx_switch_rem, tsc - last_evt[TRC_AIRQ_8])
            add_time_stat(k, whole_ctx_switch, tsc - last_evt[TRC_AIRQ_5])

        update_last_evt(last_evt, evt, tsc)

    print("Total: %d events\n" % n)
    print_irq_stat()
    print_times("CTX Switch 5-9", whole_ctx_switch)
    print_times("CTX Switch From  5-7", ctx_switch_from)
    print_times("CTX Switch To 7-8", ctx_switch_to)
    print_times("CTX Switch Rem 8-9", ctx_switch_rem)

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

def print_irq_stat():
    print("%20s   Max     Min         Mean        Stdev       Total      Events   RunTime percent" % ("IRQ/Event"))
    keys = sorted(irq_stats.keys())
    gt = []

    for k in keys:
        data = irq_stats[k]
        print_stat(str(k), data)
        gt += data
    print_stat("(total)", gt)

if __name__ == "__main__":
    main()








