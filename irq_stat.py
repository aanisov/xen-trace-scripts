#!/bin/env python3
from pcpu_split import next_rec, parse_rec, interrupted
import signal

TRC_HW_IRQ = 0x00802000
TRC_AIRQ = (TRC_HW_IRQ + 0x800)
TRC_AIRQ_1 = (TRC_AIRQ + 0x1)
TRC_AIRQ_2 = (TRC_AIRQ + 0x2)
TRC_AIRQ_3 = (TRC_AIRQ + 0x3)
TRC_AIRQ_4 = (TRC_AIRQ + 0x4)
TRC_AIRQ_5 = (TRC_AIRQ + 0x5)
TRC_AIRQ_6 = (TRC_AIRQ + 0x6)

def sighand(x,y):
    global interrupted
    interrupted = True

signal.signal(signal.SIGTERM, sighand)
signal.signal(signal.SIGHUP,  sighand)
signal.signal(signal.SIGINT,  sighand)

def main():
    n = 0
    prev_evt = None
    prev_dom = None
    prev_vcpu = None
    prev_irq = None

    irq_stack = []
    while not interrupted:
        n += 1
        ret = next_rec()
        if ret == None:
            break
        rec, tsc_in = ret
        evt, s = parse_rec(rec, tsc_in)

        # generic validation
        # if evt == TRC_AIRQ_2:
        #     if prev_evt != TRC_AIRQ_1:
        #         print ("Extra evt %X between TRC_AIRQ_1 and TRC_AIRQ_2" % prev_evt)

        if evt == TRC_AIRQ_4:
            if prev_evt != TRC_AIRQ_3:
                print ("Extra evt %X between TRC_AIRQ_3 and TRC_AIRQ_4" % prev_evt)

        if evt == TRC_AIRQ_1 or evt == TRC_AIRQ_2 or evt == TRC_AIRQ_3 or evt == TRC_AIRQ_4:
            dom = s[2] >> 16
            vcpu = s[2] & 0xFF
        else:
            print("Unknown event %X\n", evt)

        if evt == TRC_AIRQ_1 or evt == TRC_AIRQ_2:
            irq = s[3]

        prev_evt = evt
        prev_dom = dom
        prev_vcpu = vcpu

        if evt == TRC_AIRQ_4:
            if prev_dom != dom or prev_vcpu != vcpu:
                print("Dom/VCPU mismatch");

        if evt == TRC_AIRQ_1:
            irq_stack.append(irq)

        if evt == TRC_AIRQ_2:
            if prev_dom != dom or prev_vcpu != vcpu:
                print("[%d]Dom/VCPU/IRQ mismatch for TRC_AIRQ_2: %d != %d"%(s[1], irq, prev_irq));

            if len(irq_stack) > 2:
                print("[%d]Stack level is %d" % (s[1], len(irq_stack)))

            pirq = irq_stack.pop()
            if irq != pirq:
                print("[%d]IRQ stack error: %d != %d"%(s[1], irq, pirq))

        if evt == TRC_AIRQ_1 or evt == TRC_AIRQ_2:
            prev_irq = irq
    print("Total: %d events\n" % n)

if __name__ == "__main__":
    main()








