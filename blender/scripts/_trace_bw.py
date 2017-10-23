# Extracts layers from Multi-layered EXR into set of PNG files
# With proper half/float and Linear->sRGB conversion
# Using oiiotool from OpenImageIO suite, without python bindings
# Windows binary (with OCIO support) can be found here: http://www.nico-rehberg.de/tools.html
# On windows needs proper config.ocio (can be found inside Blender installation folder)

import re
import os
import sys
import subprocess

toolsetups = [
	("f:\__GameResources\zzz_TOOLS\potrace\potrace.exe", "f:\__GameResources\zzz_TOOLS\immagic\convert.exe"),
	("/Users/ipv6/Documents/zTmp/potrace/potrace", "???")]

if len(sys.argv) < 3:
	print 'Need path to PNG and channel, quitting'
	sys.exit(0)

potrace_exe = "???"
convert_exe = "???"
for stp in toolsetups:
	if os.path.exists(stp[0]):
		potrace_exe = stp[0]
		convert_exe = stp[1]
		break
	
print '- Potrace path:', potrace_exe
if not os.path.exists(potrace_exe):
	print 'Invalid path to Potrace, quitting'
	sys.exit(0)

print '- Convert path:', convert_exe
if not os.path.exists(convert_exe):
	print 'Invalid path to Convert, quitting'
	sys.exit(0)

pngfile = sys.argv[1]
print '- File to trace:', pngfile
cnlfile = sys.argv[2]
print '- Channel to extract:', cnlfile

# BMP+channel split
bmpfile = pngfile+"_"+cnlfile+".bmp"
if not os.path.exists(bmpfile):
	convert_env = os.environ.copy()
	convert_call = []
	convert_call.append(convert_exe)
	convert_call.append(pngfile)
	convert_call.append("-channel")
	convert_call.append(cnlfile)
	convert_call.append("-separate")
	convert_call.append(bmpfile)
	convert_ps = subprocess.Popen(convert_call, stdin = subprocess.PIPE, stdout = subprocess.PIPE, env=convert_env)
	(stdout, stderr) = convert_ps.communicate()

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

print "- All done"
