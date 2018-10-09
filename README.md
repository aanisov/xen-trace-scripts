# Custom XEN trace analyzing scripts #

This is a set of quick-hacked scripts for a hacked XEN with additional trace points in certain places

 1. Split trace to per-PCPU traces: ` # python3 pcpu_split.py < trace.bin `
    will create files cpu[0-3].bin in the current directory.

 2. Process IRQ (and ctx swath) statistics (only for certain PCPU!): 
 ` # python3  irq_stat2.py < cpu.bin `
