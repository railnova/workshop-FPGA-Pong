import os
import subprocess

from amaranth import *
from amaranth.build import *
from amaranth_boards.resources import *
from amaranth_boards.icestick import *

# IO definitions for our LED matrix and push button extension
workshop_pcba = [
    # LED Matrix
    Resource("led_row", 0, Pins("10 9 8 7 6 5 4 3", dir="o", conn=("j", 1)),
         Attrs(IO_STANDARD="SB_LVCMOS")),
    Resource("led_col", 0, Pins("8 7 1 2 3 4 10 9", dir="o", conn=("pmod", 0)),
         Attrs(IO_STANDARD="SB_LVCMOS")),
    # Buttons
    *ButtonResources(pins={1: "4", 2: "3", 3: "6", 4: "7", 5: "5"}, conn=("j", 3),
                     attrs=Attrs(IO_STANDARD="SB_LVCMOS")),
]


class Top(Elaboratable):
    """
    This is our toplevel 'module' builder. The Module holds the Hardware Description.
    Notice that this builder inherits the `Elaboratable` class
    """
    def elaborate(self, platform:Platform) -> Module:
        # our Module `m` will hold all combinatoral and synchronous statements, and optionally submodules
        m = Module()

        # we can request IOs from the platform. Amaranth will error if an IO is requested twice
        buttons = [platform.request("button", i+1).i for i in range(3)]
        leds = platform.request("led_col")  # By default the 0th resource is selected
        row = platform.request('led_row')


        timer = Signal(26)  # This is a 26 `bit` vector
        # Syncronous assignation will yield a D flip-flop which value is updated on the clock rising edge
        m.d.sync += timer.eq(timer+1)  # Every clock rising edge, increment `timer`


        # Combinatoral assignments are "immediate". You cannot create combinatoral "loop".
        m.d.comb += [
            row.eq(0b1),  # We select the first line of LEDs to be lit
            leds[1].eq(~buttons[1]),  # We assign a single bit
            leds[2].eq(~buttons[2]),
            leds[3:].eq(timer[-5:]),  # we can also assign slices of bits
        ]

        return m


if __name__ == "__main__":
    plat = ICEStickPlatform()
    plat.add_resources(workshop_pcba)
    plat.build(Top(), do_program=True, debug_verilog=True)
