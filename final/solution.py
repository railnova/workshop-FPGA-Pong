import os
import subprocess

from amaranth import *
from amaranth.build import *
from amaranth_boards.resources import *
from amaranth_boards.icestick import *

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
            m.d.comb += [
                self.right.eq(~platform.request("button", 1).i),
                self.left.eq(~platform.request("button", 2).i),
            ]
        else:
            m.d.comb += [
                self.right.eq(~platform.request("button", 3).i),
                self.left.eq(~platform.request("button", 4).i),
            ]

        left = self.left
        right = self.right
        leds = self.leds

        # These signals will be set when the rack has to be moved
        move_left = Signal()
        move_right = Signal()

        # We use a counter to lower the racket speed.
        # Otherwise, the racket would move at clock speed (12 MHz!)
        clk_divisor = int(platform.default_clk_frequency // self.move_speed)
        timer = Signal(range(clk_divisor), reset=clk_divisor)
        with m.If(timer == 0):
            with m.If(left | right):
                m.d.sync += timer.eq(timer.reset),
            m.d.comb += [
                # By default, Signal() instances value are 0. Here the move_* signals will be set
                # for a single clock cycle, each time the button is pressed and timer has expired
                move_left.eq(left),
                move_right.eq(right),
            ]
        with m.Else():
            m.d.sync += timer.eq(timer - 1)

        # move racket left and right, making sure it does not go outside of the field
        with m.If(move_left & ~move_right):
            with m.If(~leds[-1]):  # racket is not on the top corner
                m.d.sync += leds.eq(leds << 1)
        with m.Elif(move_right & ~move_left):
            with m.If(~leds[0]):  # racket is not on the bottom corner
                m.d.sync += leds.eq(leds >> 1)

        return m


class Ball(Elaboratable):
    move_speed = 7

    def __init__(self):
        self.row = Signal(3, reset=3) # output: ball's row position
        self.col = Signal(3, reset=1) # output: ball's column position
        self.move_up = Signal() # input: set the vertical movement direction to up
        self.move_down = Signal() # input: set the vertical movement direction to down
        self.reset = Signal()  # input: set to 1 to reset the ball position
        self.rebound = Signal()  # input: set to 1 to immediately change the horizontal direction of the ball

    def elaborate(self, platform):
        m = Module()

        moving = Signal()
        row = self.row
        col = self.col
        move_down = self.move_down
        move_up = self.move_up
        move_row = Signal()
        move_col = Signal()

        # We use a counter to lower the racket speed.
        # Otherwise, the racket would move at clock speed (12 MHz!)
        clk_divisor = int(platform.default_clk_frequency // self.move_speed)
        clk_divisor_col = int(platform.default_clk_frequency // (self.move_speed))
        timer = Signal(range(clk_divisor), reset=clk_divisor)
        timer = Signal(range(clk_divisor_col), reset=clk_divisor_col)

        with m.If(timer == 0):
            m.d.sync += timer.eq(timer.reset),
        with m.Else():
            m.d.sync += timer.eq(timer - 1)

        with m.If(moving):
            # Horizontal movement
            with m.If(self.rebound):
                with m.If(col == 0):
                    m.d.sync += col.eq(1)
                with m.If(col == 7):
                    m.d.sync += col.eq(6)    
                m.d.sync += move_col.eq(~move_col)
            with m.Elif(timer == 0):
                m.d.sync += timer.eq(timer.reset),
                with m.If(move_col):  # ball moving right
                    with m.If(col != 7):  # ball is on the right: don't move
                        m.d.sync += col.eq(col + 1)
                with m.Else():  # ball moving left
                    with m.If(col!=0):  # ball is on the left: don't move
                        m.d.sync += col.eq(col - 1)
            

            # Vertical movement
            with m.If(timer == 0):
                m.d.sync += timer.eq(timer.reset),
                with m.If(move_row):  # ball moving up
                    with m.If(row==7):  # ball is on the ceiling: reverse vertical movement direction
                        m.d.sync += [
                            move_row.eq(0),
                            row.eq(row - 1),
                        ]
                    with m.Else():
                        m.d.sync += row.eq(row + 1)
                with m.Else():  # ball moving down
                    with m.If(row==0):  # ball is on the floor: reverse vertical movement direction
                        m.d.sync += [
                            move_row.eq(1),
                            row.eq(row + 1),
                        ]
                    with m.Else():
                        m.d.sync += row.eq(row - 1)

            # To change the ball vertical direction using the racket
            with m.If((col == 0) | (col == 7)):
                with m.If(move_down & ~move_up):
                    m.d.sync += move_row.eq(0)
                with m.If(move_up & ~move_down):
                    m.d.sync += move_row.eq(1)
        with m.Else():
            with m.If(move_up & move_down):
                m.d.sync += moving.eq(1)
            with m.Elif(timer != 0):
                pass
            with m.Elif(move_up):
                m.d.sync += [
                    move_col.eq(~move_col),
                    row.eq(row + 1),
                ]
            with m.Elif(move_down):
                m.d.sync += [
                    move_col.eq(~move_col),
                    row.eq(row - 1),
                ]

        with m.If(self.reset):
            with m.If(col[-1]): # right side
                m.d.sync += [
                    col.eq(6),
                    move_col.eq(0),
                ]
            with m.Else():  # left side
                m.d.sync += [
                    col.eq(1),
                    move_col.eq(1),
                ]
            m.d.sync += [
                moving.eq(0),
            ]

        return m


class ScoreUart(Elaboratable):
    def __init__(self):
        self.score_left = Signal(range(10))
        self.score_right = Signal(range(10))
        self.update = Signal()

    def elaborate(self, platform):
        m = Module()

        from amlib.io.serial import AsyncSerialTX
        uart_pins = platform.request("uart")
        uart = m.submodules.uart = AsyncSerialTX(divisor=int(platform.default_clk_frequency // 115200),
                                                 pins=uart_pins)
        score_left = self.score_left
        score_right = self.score_right
        update = self.update

        with m.FSM(name="score_uart"):
            with m.State("IDLE"):
                with m.If(update):
                    m.next = "LEFT"
            with m.State("LEFT"):
                m.d.comb += [
                    uart.data.eq(ord('0') + score_left),
                    uart.ack.eq(1),
                ]
                with m.If(uart.rdy):
                    m.next = "DASH"
            with m.State('DASH'):
                m.d.comb += [
                    uart.data.eq(ord('-')),
                    uart.ack.eq(1),
                ]
                with m.If(uart.rdy):
                    m.next = "RIGHT"
            with m.State('RIGHT'):
                m.d.comb += [
                    uart.data.eq(ord('0') + score_right),
                    uart.ack.eq(1),
                ]
                with m.If(uart.rdy):
                    m.next = "NEWLINE"
            with m.State('NEWLINE'):
                m.d.comb += [
                    uart.data.eq(ord('\r')),
                    uart.ack.eq(1),
                ]
                with m.If(uart.rdy):
                    m.next = "NEWLINE2"
            with m.State('NEWLINE2'):
                m.d.comb += [
                    uart.data.eq(ord('\n')),
                    uart.ack.eq(1),
                ]
                with m.If(uart.rdy):
                    m.next = "IDLE"

        return m


class Pong(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        # We add the Matrix module as a submodule. This creates a Module() tree
        ledm = m.submodules.ledm = LEDMatrix()

        # broadcast the score on the UART
        uart = m.submodules.uart = ScoreUart()

        # our ball
        ball = m.submodules.ball = Ball()

        # build Rackets and display them
        racket_left = m.submodules.racket_left = Racket(player=2)
        racket_right = m.submodules.racket_right = Racket()
        for i in range(8):
            m.d.comb += [
                ledm.pixels[0][i].eq(racket_left.leds[i]),
                ledm.pixels[7][i].eq(racket_right.leds[i]),
            ]

        # allow the racket to change the ball direction only when it's touching the ball
        with m.If(~ball.col[-1]):
            m.d.comb += ball.move_up.eq(racket_left.left),
            m.d.comb += ball.move_down.eq(racket_left.right),
        with m.If(ball.col[-1]):
            m.d.comb += ball.move_up.eq(racket_right.left),
            m.d.comb += ball.move_down.eq(racket_right.right),

        # rebound when the ball is on the racket
        # At this stage, ledm.pixels does not contain the ball, so we can use it to check for ball and racket overlap
        rebound = Signal()
        # m.d.comb += rebound.eq(ledm.pixels[ball.col][ball.row])

        # Draw the ball
        m.d.comb += ledm.pixels[ball.col][ball.row].eq(1)

        # Score
        score_left = Signal()
        score_right = Signal()
        m.d.sync += uart.update.eq(0)  # clears the update signal every clock cycle
        with m.If(ball.col == 0):
            with m.If(~rebound):
                m.d.sync += [
                    score_left.eq(score_left + 1),
                    uart.update.eq(1)
                ]
                m.d.comb += ball.reset.eq(1),
        with m.If(ball.col == 7):
            with m.If(~rebound):
                m.d.sync += [
                    score_right.eq(score_right + 1),
                    uart.update.eq(1)
                ]
                m.d.comb += ball.reset.eq(1),
        with m.If(~platform.request("button", 5)):
            m.d.comb += [
                ball.reset.eq(1),
            ]
            m.d.sync += [
                score_left.eq(0),
                score_right.eq(0),
                uart.update.eq(1)
            ]
        m.d.comb += [
            uart.score_right.eq(score_right),
            uart.score_left.eq(score_left),
        ]

        return m

if __name__ == "__main__":
    plat = ICEStickPlatform()
    plat.add_resources(workshop_pcba)
    plat.build(Pong(), do_program=True, debug_verilog=True)
