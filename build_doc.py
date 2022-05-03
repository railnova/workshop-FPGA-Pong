import os
import wavedrom
import cairosvg

# Building the timing diagrams
diagrams = [    

"""{ "head": { "text": "Combinatory vs Syncronous assignment" },
"signal": [
 { "name": "CK",   "wave": "P...", "period": 2  },
 { "name": "a",  "wave": "0.1.....", "phase": 0.5 },
 { "name": "b",  "wave": "0..1....", "phase": 0.5 },
 { "name": "c_comb", "wave": "0..1....","phase": 0.5 },
 { "name": "d",  "wave": "0...1..." },
 { "name": "e",  "wave": "0.....1." }
]}""",
"""{ "head": { "text": "Button debouncing" },
 "signal": [
 { "name": "CK",   "wave": "P......", "period": 2  },
 { "name": "button",  "wave": "0.101...0.1...", "phase": 0.5 },
 { "name": "timer",  "wave": "=.=.=.=...=.=.", "data": ["0", "2", "1", "0", "2", "1"] },
 { "name": "pressed", "wave": "0.1.....0.1..." }
]}""",
"""{ "head": { "text": "Combinatory vs Syncronous assignment" },
"signal": [
 { "name": "CK",   "wave": "P........", "period": 2  },
 { "name": "led_col[0]",  "wave": "1.0.............1." },
 { "name": "led_col[1]",  "wave": "0.1.0............." },
 { "name": "led_col[2]",  "wave": "0...1.0..........." },
 { "name": "led_col[3]",  "wave": "0.....1.0........." },
 { "name": "..." },
 { "name": "led_col[7]",  "wave": "0.............1.0." },
 {},
 { "name": "led_row[0:8]",  "wave": "=.=.=.=.=.=.=.=.=.", "data": ["row 0", "row 1", "row 2", "row 3", "row 4", "row 5", "row 6", "row 7", "row 0"] }
]}""",
"""{ "head": { "text": "Stream interface" },
"signal": [
 { "name": "CK",   "wave": "P........", "period": 2  },
 { "name": "rdy (from sink)",  "wave": "0.....1............." },
 { "name": "ack (from source)",  "wave": "0.1.0...1.0...1...0." },
 { "name": "data (from source)",  "wave": "x.......=.x...=.=.x.", "data": ["#1", "#2", "#3"] }
]}"""
]

for i, diagram in enumerate(diagrams):
    svg_path = f"doc/diagram{i+1:02}.svg"
    png_path = f"doc/diagram{i+1:02}.png"
    print(f"Building {png_path}")
    svg = wavedrom.render(diagram)
    svg.saveas(svg_path)
    cairosvg.svg2pdf(url=svg_path, write_to=png_path, output_width=500)

os.system('rinoh README.md')
