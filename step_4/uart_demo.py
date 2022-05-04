import os
import subprocess

from amaranth import *
from amaranth.build import *
from amaranth_boards.resources import *
from amaranth_boards.icestick import *


class UartDemo(Elaboratable):
    """Continuouslt send the 'A' character on the serial port"""

    def elaborate(self, platform):
        m = Module()

        from amlib.io.serial import AsyncSerialTX
        uart_pins = platform.request("uart")
        uart = m.submodules.uart = AsyncSerialTX(divisor=int(platform.default_clk_frequency // 115200),
                                                 pins=uart_pins)

        m.d.comb += [
          uart.data.eq(int(ord('A'))),
          uart.ack.eq(1),
          # a byte will be sent by the UART when uart.rdy == 1
        ]

        return m


if __name__ == "__main__":
    plat = ICEStickPlatform()
    plat.build(UartDemo(), do_program=True, debug_verilog=True)
