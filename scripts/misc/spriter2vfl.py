#cd ~/kristallum/scripts/misc/
#python ./spriter2vfl.py /Volumes/untitled/Dropbox/web/static-ldu/vn_storyline/art/anims/objects_motion/om.scml fly_in

import argparse
from xml.dom import minidom

parser = argparse.ArgumentParser()
parser.add_argument("scml")
parser.add_argument("animation")
args = parser.parse_args()
print "- scml: '" + args.scml + "'"
print "- animation: '" + args.animation + "'"

xmldoc = minidom.parse(args.scml)
outvfl = []
animslist = xmldoc.getElementsByTagName('animation')
for s in animslist:
    animname = s.attributes['name'].value
    if animname == args.animation:
        print("- found '"+animname+"'")
        timelines = s.getElementsByTagName('timeline')
        if len(timelines) > 0:
            prev_r = -9999.99
            prev_x = -9999.99
            prev_y = -9999.99
            prev_a = -9999.99
            prev_sx = -9999.99
            prev_sy = -9999.99
            keys = timelines[0].getElementsByTagName('key')
            for k in keys:
                keytime = 0
                if len(k.getAttribute('time'))>0:
                    keytime = float(k.getAttribute('time'))
                keyobjects = k.getElementsByTagName('object')
                if len(keyobjects) > 0:
                    o = keyobjects[0]
                    r = 0.0
                    x = 0.0
                    y = 0.0
                    a = 1.0
                    sx = 1.0
                    sy = 1.0
                    lerp = None
                    lerp_c1 = 0.0
                    lerp_c2 = 0.0
                    if len(k.getAttribute('curve_type'))>0 and k.getAttribute('curve_type') == "cubic":
                        lerp = "cubic_"
                        lerp_c1 = float(k.getAttribute('c1'))
                        lerp_c2 = float(k.getAttribute('c2'))
                    if len(o.getAttribute('x'))>0:
                        x = float(o.getAttribute('x'))
                    if len(o.getAttribute('y'))>0:
                        y = float(o.getAttribute('y'))
                    if len(o.getAttribute('a'))>0:
                        a = float(o.getAttribute('a'))
                    if len(o.getAttribute('angle'))>0:
                        r = float(o.getAttribute('angle'))
                    if len(o.getAttribute('scale_x'))>0:
                        sx = float(o.getAttribute('scale_x'))
                    if len(o.getAttribute('scale_y'))>0:
                        sy = float(o.getAttribute('scale_y'))
                    if r>180:
                        r = r - 360
                    print("-- time: " + str(keytime) + ", x="+str(x) + ", y="+str(y) + ", r="+str(r) + ", a="+str(a))
                    time_blk = "t" + str(keytime/1000.0)
                    if(lerp is not None):
                        time_blk = time_blk + " " + lerp + "c1" + str(lerp_c1) + " " + lerp + "c2" + str(lerp_c2)
                    outvfl.append(time_blk)
                    if x != prev_x:
                        outvfl.append("x" + str(x))
                    if y != prev_y:
                        outvfl.append("y" + str(y))
                    if a != prev_a:
                        outvfl.append("a" + str(a))
                    if r != prev_r:
                        outvfl.append("r" + str(r))
                    if sx != prev_sx:
                        outvfl.append("sx" + str(sx))
                    if sy != prev_sy:
                        outvfl.append("sy" + str(sy))
                    prev_r = r
                    prev_x = x
                    prev_y = y
                    prev_a = a
                    prev_sx = sx
                    prev_sy = sy
    else:
        print("- skipping '"+animname+"'")
print("=== vfl for '" + args.animation + "'===")
print(", ".join(outvfl))
print("=== === === ===")
