# Extracts layers from Multi-layered EXR into set of PNG files
# With proper half/float and Linear->sRGB conversion
# Using oiiotool from OpenImageIO suite, without python bindings
# Windows binary (with OCIO support) can be found here: http://www.nico-rehberg.de/tools.html
# On windows needs proper config.ocio (can be found inside Blender installation folder)

import re
import os
import sys
import subprocess

isWin = True
if isWin:
	oiioexe = "f:\__GameResources\zzz_TOOLS\openimageio\oiiotool.exe"
	ocioconf = "c:\Program Files\Blender Foundation\Blender\2.78\datafiles\colormanagement\config.ocio"
else:
	oiioexe = "/Users/ipv6/Documents/zTmp/oiio/dist/macosx/bin/oiiotool"
	ocioconf = ""

if len(sys.argv) < 2:
	print 'Need path to EXR, quitting'
	sys.exit(0)

print 'Oiiotool path:', oiioexe
if not os.path.exists(oiioexe):
	print 'Invalid path to oiiotool, quitting'
	sys.exit(0)

exrfile = sys.argv[1]
print 'EXR to parse:', exrfile
if not os.path.exists(exrfile):
	print 'Invalid path to EXR, quitting'
	sys.exit(0)
exrlayers = []

oiio_env = os.environ.copy()
if len(ocioconf) > 0:
	oiio_env["OCIO"] = ocioconf
oiiocall = []
oiiocall.append(oiioexe)
oiiocall.append("--info")
oiiocall.append("-v")
oiiocall.append(exrfile)
ps = subprocess.Popen(oiiocall, stdin = subprocess.PIPE, stdout = subprocess.PIPE, env=oiio_env)
(stdout, stderr) = ps.communicate()
exrinfo = stdout.splitlines()
for exrinfoline in exrinfo:
	if exrinfoline.find("channel list:") >= 0:
		headr_content = exrinfoline.split(':')
		if len(headr_content) >= 2:
			exrlayers = [x.strip() for x in headr_content[1].split(',')]
			break
print 'Layers found:', exrlayers
if len(exrlayers) == 0:
	print 'No layers found, quitting'
	sys.exit(0)

exrname = os.path.basename(exrfile)
exrname = os.path.splitext(exrname)[0]
def flush_stack(stk, stkfrm):
	if len(stk) == 0:
		return
	outname = stk[0].rsplit('.', 1)[0]
	outname = outname.replace(".","_")
	outname = outname.replace("+","_")
	outname = exrname+"_"+outname
	print "Extracting: ", outname, ", format:", stkfrm
	oiiocall = []
	oiiocall.append(oiioexe)
	oiiocall.append(exrfile)
	oiiocall.append("--ch")
	oiiocall.append(",".join(stk))
	oiiocall.append("-d")
	oiiocall.append(stkfrm)
	oiiocall.append("--tocolorspace")
	oiiocall.append("sRGB")
	oiiocall.append("-o")
	oiiocall.append(outname+".png")
	ps = subprocess.Popen(oiiocall, stdin = subprocess.PIPE, stdout = subprocess.PIPE, env=oiio_env)
	(stdout, stderr) = ps.communicate()
	return
curr_format = "half"
curr_chstack = []
for layername in exrlayers:
	name_type_pair = layername.split(' ')
	#print "Analyzing: ", layername, ", format:", ",".join(name_type_pair)
	if len(name_type_pair) > 0:
		layerName = name_type_pair[0]
		if len(name_type_pair) > 1:
			layerFrmt = name_type_pair[1]
		else:
			layerFrmt = "(half)"
		if layerName.find(".R") >= 0:
			# flushing previous layer
			flush_stack(curr_chstack, curr_format)
			# setting new layer up
			curr_chstack = []
			curr_format = re.search(r'\((.*?)\)',layerFrmt).group(1)
		if layerName.find(".R") >= 0 or layerName.find(".G") >= 0 or layerName.find(".B") >= 0 or layerName.find(".A") >= 0:
			curr_chstack.append(layerName)
flush_stack(curr_chstack, curr_format)
curr_chstack = []
print "All done"


# WIN:
# TEST: oiiotool.exe --info -v c:\_WPLabs\PROJECTS_GAMES\YandexDisk\SideArts\_3D\Renders\a1x0001.exr
# TEST RESULT: channel list: Combined.Combined.R (half), Combined.Combined.G (half), Combined.Combined.B (half), Combined.Combined.A (half), DiffCol+Z+Norm.AO.R (half), DiffCol+Z+Norm.AO.G (half), DiffCol+Z+Norm.AO.B (half), DiffCol+Z+Norm.Combined.R (half), DiffCol+Z+Norm.Combined.G (half), DiffCol+Z+Norm.Combined.B (half), DiffCol+Z+Norm.Combined.A (half), DiffCol+Z+Norm.Depth.Z (float), DiffCol+Z+Norm.DiffCol.R (half), DiffCol+Z+Norm.DiffCol.G (half), DiffCol+Z+Norm.DiffCol.B (half), DiffCol+Z+Norm.Normal.Z (half), DiffCol+Z+Norm.Normal.X (half), DiffCol+Z+Norm.Normal.Y (half), EdgeDetect.Combined.R (half), EdgeDetect.Combined.G (half), EdgeDetect.Combined.B (half), EdgeDetect.Combined.A (half), EdgeDetect.Depth.Z (float), EdgeDetect.DiffCol.R (half), EdgeDetect.DiffCol.G (half), EdgeDetect.DiffCol.B (half), SideLights.Combined.R (half), SideLights.Combined.G (half), SideLights.Combined.B (half), SideLights.Combined.A (half), SideLights.Depth.Z (float) ...
# TEST EXTRACT: oiiotool.exe c:\_WPLabs\PROJECTS_GAMES\YandexDisk\SideArts\_3D\Renders\a1x0001.exr --ch Combined.Combined.R,Combined.Combined.G,Combined.Combined.B -d half --tocolorspace sRGB -o aaa.png

# MAC:
# python /Users/ipv6/Documents/_CloudDrives/Dropbox/_project/_scripts/blender/addons/_exr_extractlayers.py /Users/ipv6/Documents/_CloudDrives/Yandex.Disk.localized/SideArts/_3D/Renders/a20001.exr
