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


        counter = Signal(8)
        # Mechanical switches have a 'bounce' effect when they are pressed, which can lead to multiple
        # flanks being generated (and counted).
        # Here we use a 50ms 'debounce' timer to ignore flanks when the timer is running
        debounce_count = int(platform.default_clk_frequency * 50E-3)
        debounce_timer = Signal(range(debounce_count+1))  # our signal holds *at least* values from 0 to debounce_count
        is_pressed = Signal()
        with m.If(is_pressed):
            with m.If(debounce_timer):
                m.d.sync += debounce_timer.eq(debounce_timer - 1)
            with m.Elif(buttons[0] & buttons[1]):
                m.d.sync += is_pressed.eq(0)  # Why do we have to use a synchronous assignment here?
        with m.Else():
            with m.If(~buttons[0]):
                m.d.sync += [
                    counter.eq(counter + 1),
                    is_pressed.eq(1),
                ]
            with m.If(~buttons[1]):
                m.d.sync += [
                    counter.eq(counter - 1),
                    is_pressed.eq(1),
                ]

        m.d.comb += [
            row.eq(0b1),  # We select the first line of LEDs to be lit
            leds.eq(counter),  # We assign a single bit
        ]

        return m


if __name__ == "__main__":
    plat = ICEStickPlatform()
    plat.add_resources(workshop_pcba)
    plat.build(Top(), do_program=True, debug_verilog=True)
