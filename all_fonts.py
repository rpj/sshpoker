import pyfiglet
import sys

for font in pyfiglet.FigletFont().getFonts():
    print(font)
    print(pyfiglet.figlet_format(sys.argv[-1], font=font))
    print("\n\n")