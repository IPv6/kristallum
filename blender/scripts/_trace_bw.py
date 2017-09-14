# Extracts layers from Multi-layered EXR into set of PNG files
# With proper half/float and Linear->sRGB conversion
# Using oiiotool from OpenImageIO suite, without python bindings
# Windows binary (with OCIO support) can be found here: http://www.nico-rehberg.de/tools.html
# On windows needs proper config.ocio (can be found inside Blender installation folder)

import re
import os
import sys
import subprocess

isWin = False
if isWin:
	potrace_exe = "???"
	#convert_exe = "???"
else:
	potrace_exe = "/Users/ipv6/Documents/zTmp/potrace/potrace"
	#convert_exe = "/Users/ipv6/Documents/zTmp/ImageMagick/bin/convert"

if len(sys.argv) < 2:
	print 'Need path to BMP, quitting'
	sys.exit(0)

print 'Potrace path:', potrace_exe
if not os.path.exists(potrace_exe):
	print 'Invalid path to Potrace, quitting'
	sys.exit(0)
#print 'Convert path:', convert_exe
#if not os.path.exists(convert_exe):
#	print 'Invalid path to Convert, quitting'
#	sys.exit(0)

bmpfile = sys.argv[1]
print 'BMP to trace:', bmpfile

# BMP+channel split
#bmpfile = pngfile+".bmp"
# convert in.png -channel R -separate a.bmp

# http://potrace.sourceforge.net/README
potrace_env = os.environ.copy()
potrace_call = []
potrace_call.append(potrace_exe)
potrace_call.append("--svg")
potrace_call.append("--turdsize") #suppress speckles of up to this size
potrace_call.append("2")
potrace_call.append("--alphamax") # corner threshold parameter
potrace_call.append("1")
potrace_call.append("--color")
potrace_call.append("#ffffff")
potrace_call.append("--fillcolor")
potrace_call.append("#000000")
potrace_call.append("--opaque")
potrace_call.append("--i")
potrace_call.append(bmpfile)
potrace_ps = subprocess.Popen(potrace_call, stdin = subprocess.PIPE, stdout = subprocess.PIPE, env=potrace_env)
(stdout, stderr) = potrace_ps.communicate()

print "All done"
