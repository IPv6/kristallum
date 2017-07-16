import sys
import subprocess,os
from subprocess import Popen 
import os

# Windows binary (with OCIO support) can be found here: http://www.nico-rehberg.de/tools.html
oiioexe = r"f:\__GameResources\zzz_TOOLS\openimageio\oiiotool.exe"
ocioconf = r"c:\Program Files\Blender Foundation\Blender\2.78\datafiles\colormanagement\config.ocio"

if len(sys.argv) < 2:
	print 'Need path to exr file, quitting'
	sys.exit(0)

exrfile = sys.argv[1]
print 'EXR to parse:', exrfile
exrlayers = []

oiio_env = os.environ.copy()
if len(ocioconf) > 0:
	oiio_env["OCIO"] = ocioconf
oiiocall = []
oiiocall.append(oiioexe)
oiiocall.append("--info")
oiiocall.append("-v")
oiiocall.append(exrfile)
ps = Popen(oiiocall, stdin = subprocess.PIPE, stdout = subprocess.PIPE, env=oiio_env)
(stdout, stderr) = ps.communicate()
exrinfo = stdout.splitlines()
for exrinfoline in exrinfo:
	if exrinfoline.find("channel list:") >= 0:
		exrlayers = [x.strip() for x in exrinfoline.split(',')]
		exrlayers = filter(lambda plt: "channel list:" not in plt,exrlayers)
		break
print 'Layers found:', exrlayers

def flush_stack(stk):
	if len(stk) == 0:
		return
	outname = stk[0].rsplit('.', 1)[0]
	outname = outname.replace(".","_")
	outname = outname.replace("+","_")
	print "Extracting: ", outname
	oiiocall = []
	oiiocall.append(oiioexe)
	oiiocall.append(exrfile)
	oiiocall.append("--ch")
	oiiocall.append(",".join(stk))
	oiiocall.append("-d")
	oiiocall.append("half")
	oiiocall.append("--tocolorspace")
	oiiocall.append("sRGB")
	oiiocall.append("-o")
	oiiocall.append(outname+".png")
	ps = Popen(oiiocall, stdin = subprocess.PIPE, stdout = subprocess.PIPE, env=oiio_env)
	(stdout, stderr) = ps.communicate()
	return
curr_chstack = []
for layername in exrlayers:
	name_type_pair = layername.split(' ')
	if len(name_type_pair) >= 1:
		layerName = name_type_pair[0]
		if layerName.find(".R") >= 0:
			flush_stack(curr_chstack)
			curr_chstack = []
		if layerName.find(".R") >= 0 or layerName.find(".G") >= 0 or layerName.find(".B") >= 0 or layerName.find(".A") >= 0:
			curr_chstack.append(layerName)
flush_stack(curr_chstack)
curr_chstack = []
print "All done"



# TEST: oiiotool.exe --info -v c:\_WPLabs\PROJECTS_GAMES\YandexDisk\SideArts\_3D\Renders\a1x0001.exr
# TEST RESULT: channel list: Combined.Combined.R (half), Combined.Combined.G (half), Combined.Combined.B (half), Combined.Combined.A (half), DiffCol+Z+Norm.AO.R (half), DiffCol+Z+Norm.AO.G (half), DiffCol+Z+Norm.AO.B (half), DiffCol+Z+Norm.Combined.R (half), DiffCol+Z+Norm.Combined.G (half), DiffCol+Z+Norm.Combined.B (half), DiffCol+Z+Norm.Combined.A (half), DiffCol+Z+Norm.Depth.Z (float), DiffCol+Z+Norm.DiffCol.R (half), DiffCol+Z+Norm.DiffCol.G (half), DiffCol+Z+Norm.DiffCol.B (half), DiffCol+Z+Norm.Normal.Z (half), DiffCol+Z+Norm.Normal.X (half), DiffCol+Z+Norm.Normal.Y (half), EdgeDetect.Combined.R (half), EdgeDetect.Combined.G (half), EdgeDetect.Combined.B (half), EdgeDetect.Combined.A (half), EdgeDetect.Depth.Z (float), EdgeDetect.DiffCol.R (half), EdgeDetect.DiffCol.G (half), EdgeDetect.DiffCol.B (half), SideLights.Combined.R (half), SideLights.Combined.G (half), SideLights.Combined.B (half), SideLights.Combined.A (half), SideLights.Depth.Z (float), SideLights.DiffCol.R (half), SideLights.DiffCol.G (half), SideLights.DiffCol.B (half), SideLights.GlossCol.R (half), SideLights.GlossCol.G (half), SideLights.GlossCol.B (half), SideLights.Normal.Z (half), SideLights.Normal.X (half), SideLights.Normal.Y (half), Wireframe.Combined.R (half), Wireframe.Combined.G (half), Wireframe.Combined.B (half), Wireframe.Combined.A (half), Wireframe.Depth.Z (float), Wireframe.DiffCol.R (half), Wireframe.DiffCol.G (half), Wireframe.DiffCol.B (half), Wireframe.Emit.R (half), Wireframe.Emit.G (half), Wireframe.Emit.B (half), Wireframe.Normal.Z (half), Wireframe.Normal.X (half), Wireframe.Normal.Y (half)
# TEST EXTRACT: oiiotool.exe c:\_WPLabs\PROJECTS_GAMES\YandexDisk\SideArts\_3D\Renders\a1x0001.exr --ch Combined.Combined.R,Combined.Combined.G,Combined.Combined.B -d half --tocolorspace sRGB -o aaa.png