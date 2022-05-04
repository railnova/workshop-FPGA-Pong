import os
import subprocess

from amaranth import *
from amaranth.build import *
from amaranth_boards.resources import *
from amaranth_boards.icestick import *
from amaranth.lib.cdc import FFSynchronizer

# IO definitions for our LED matric and push button extension
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


class LEDMatrix(Elaboratable):
    """LED Matrix scanning module.
    You can access the LED rows through the `pixels` array
    """
    def __init__(self):
        self.pixels = Array(Array(Signal(name=f"col{i}") for i in range(8)) for j in range(8))

    def elaborate(self, platform):
        m = Module()

        # get the Signal() instances representing LEDs output pins
        led_row = platform.request("led_row", 0).o
        led_col = platform.request("led_col", 0).o

        timer = Signal(10)  # Clock divisor for row refresh rate
        row_select = Signal(8, reset=0b1)  # row selection
        row_cnt = Signal(3)
        col = Signal(8)

        # Since we have to command LEDs per row, not per column, rotate the pixels matrix
        pixels_rows = Array(Signal(8, name=f"row{i}") for i in range(8))
        for i in range(8):
            for j in range(8):
                m.d.comb += pixels_rows[i].eq(Cat(self.pixels[j][i] for j in range(8)))

        m.d.comb += [
            led_col.eq(pixels_rows[row_cnt]),
            led_row.eq(row_select),
        ]
        m.d.sync += timer.eq(timer + 1)
        with m.If(timer == 0):
            m.d.sync += [
                row_cnt.eq(row_cnt + 1),
                row_select.eq(Cat(row_select[7], row_select[0:7])),  # 1 bit circular shift column selection
            ]

        return m


class Racket(Elaboratable):
    def __init__(self, player=1):
        if player not in [1, 2]:
            raise ValueError("player must be 1 or 2")
        self._player = player
        self.leds = Signal(8, reset=0b00011000)  # The racket is 2 pixel wide
        self.left = Signal()  # output: set to 1 when the left button is pressed
        self.right = Signal()  # output: set to 1 when the right button is pressed
        self.move_speed=10

    def elaborate(self, platform):
        m = Module()

        player = self._player
        if player == 1:
            m.submodules += FFSynchronizer(~platform.request("button", 1).i, self.right)
            m.submodules += FFSynchronizer(~platform.request("button", 2).i, self.left)
        else:
            m.submodules += FFSynchronizer(~platform.request("button", 3).i, self.right)
            m.submodules += FFSynchronizer(~platform.request("button", 4).i, self.left)

        left = self.left  # this signal is set when the button is pressed
        right = self.right  # this signal is set when the button is pressed
        leds = self.leds

        # These signals will be set when the racket has to be moved
        move_left = Signal()
        move_right = Signal()

        # Use a counter to lower the racket speed.
        # signals move_left and move_right should only be active for a single clock period
        # Otherwise, the racket would move at clock speed (12 MHz!)
        clk_divisor = int(platform.default_clk_frequency // self.move_speed)
        timer = Signal(range(clk_divisor), reset=clk_divisor)

        ############################################################################################
        #                                                                                          #
        #                                 Write your HDL here                                      #
        #                                                                                          #
        ############################################################################################


        # move racket left and right, making sure it does not go outside of the field
        with m.If(move_left & ~move_right):
            with m.If(~leds[-1]):  # racket is not on the top corner
                m.d.sync += leds.eq(leds << 1)
        with m.Elif(move_right & ~move_left):
            with m.If(~leds[0]):  # racket is not on the bottom corner
                m.d.sync += leds.eq(leds >> 1)

        return m


class Pong(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        # We add the Matrix module as a submodule. This creates a Module() tree
        ledm = m.submodules.ledm = LEDMatrix()

        # build Rackets, and add them to the submodules list
        racket_left = m.submodules.racket_left = Racket(player=2)
        racket_right = m.submodules.racket_right = Racket()
        # Connect the racket pixels to the display
        for i in range(8):
            m.d.comb += [
                ledm.pixels[0][i].eq(racket_left.leds[i]),
                ledm.pixels[7][i].eq(racket_right.leds[i]),
            ]

        return m

if __name__ == "__main__":
    plat = ICEStickPlatform()
    plat.add_resources(workshop_pcba)
    plat.build(Pong(), do_program=True, debug_verilog=True)
