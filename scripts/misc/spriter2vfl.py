#cd ~/kristallum/scripts/misc/
#python ./spriter2vfl.py /Volumes/untitled/Dropbox/web/static-ldu/vn_storyline/art/anims/emots_motion/em.scml jump
#python ./spriter2vfl.py c:\_WPLabs\PROJECTS_GAMES\Bitbucket-priv\Dropbox\web\static-ldu\vn_storyline\art\anims\objects_motion\om.scml phone_shake

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
isFirstKeyfound = False
for s in animslist:
    animname = s.getAttribute('name')
    if animname == args.animation:
        print("- found '"+animname+"'")
        timelast = float(s.getAttribute('length'))
        timelines = s.getElementsByTagName('timeline')
        if len(timelines) > 0:
            keytime = 0
            prev_r = -9999.99
            prev_x = -9999.99
            prev_y = -9999.99
            prev_a = -9999.99
            prev_sx = -9999.99
            prev_sy = -9999.99
            first_r = -9999.99
            first_x = -9999.99
            first_y = -9999.99
            first_a = -9999.99
            first_sx = -9999.99
            first_sy = -9999.99
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
                        prev_x = -9999.99
                    if len(o.getAttribute('y'))>0:
                        y = -1*float(o.getAttribute('y'))
                        prev_y = -9999.99
                    if len(o.getAttribute('a'))>0:
                        a = float(o.getAttribute('a'))
                        prev_a = -9999.99
                    if len(o.getAttribute('angle'))>0:
                        r = -1*float(o.getAttribute('angle'))
                        prev_r = -9999.99
                    if len(o.getAttribute('scale_x'))>0:
                        sx = float(o.getAttribute('scale_x'))
                        prev_sx = -9999.99
                    if len(o.getAttribute('scale_y'))>0:
                        sy = float(o.getAttribute('scale_y'))
                        prev_sy = -9999.99
                    if r>180:
                        r = r - 360
                    if r<-180:
                        r = r + 360
                    if abs(a)<0.001:
                        a = 0
                    if abs(x)<0.001:
                        x = 0
                    if abs(y)<0.001:
                        y = 0
                    if abs(r)<0.001:
                        r = 0
                    if abs(sx)<0.001:
                        sx = 0
                    if abs(sy)<0.001:
                        sy = 0
                    print("-- time: " + str(keytime) + ", x="+str(x) + ", y="+str(y) + ", r="+str(r) + ", a="+str(a))
                    if isFirstKeyfound == False:
                        isFirstKeyfound = True
                        first_r = r
                        first_x = x
                        first_y = y
                        first_a = a
                        first_sx = sx
                        first_sy = sy
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
            if keytime < timelast:
                outvfl.append("t" + str(timelast/1000.0))
                outvfl.append("x" + str(first_x))
                outvfl.append("y" + str(first_y))
                outvfl.append("a" + str(first_a))
                outvfl.append("r" + str(first_r))
                outvfl.append("sx" + str(first_sx))
                outvfl.append("sy" + str(first_sy))
                outvfl.append("loop")
    else:
        print("- skipping '"+animname+"'")
if isFirstKeyfound:
    print("=== vfl for '" + args.animation + "'===")
    print(", ".join(outvfl))
    print("=== === === ===")
