#!/bin/sh
# Run the headphone-amp simulation and print the headline numbers.
cd "$(dirname "$0")" && ngspice -b hp_amp.cir 2>&1 \
  | grep -E "===|vout_rms|ib[12]_|pout|^p =|vin_rms|rload|THD|^vo |gain_1k|f_3db|rror"
