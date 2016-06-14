#python ./spriter2vfl.py /Volumes/untitled/Dropbox/web/static-ldu/vn_storyline/art/anims/objects_motion/om.scml phone_shake

import argparse
from xml.dom import minidom

parser = argparse.ArgumentParser()
parser.add_argument("scml")
parser.add_argument("animation")
args = parser.parse_args()
print "- scml: '" + args.scml + "'"
print "- animation: '" + args.animation + "'"

xmldoc = minidom.parse(args.scml)

animslist = xmldoc.getElementsByTagName('animation')
for s in animslist:
    animname = s.attributes['name'].value
    if animname == args.animation:
        print("- found '"+animname+"'")
        timelines = s.getElementsByTagName('timeline')
        if len(timelines) > 0:
            keys = timelines[0].getElementsByTagName('key')
            for k in keys:
                keytime = 0
                if len(k.getAttribute('time'))>0:
                    keytime = float(k.getAttribute('time'))
                keyobjects = k.getElementsByTagName('object')
                if len(keyobjects) > 0:
                    o = keyobjects[0]
                    r = 0
                    x = 0
                    y = 0
                    a = 1
                    sx = 1
                    sy = 1
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
    else:
        print("- skipping '"+animname+"'")
