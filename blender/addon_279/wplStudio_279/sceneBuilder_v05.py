# TBD: 2.80 porting
# https://blog.michelanders.nl/2018/12/upgrading-blender-add-ons-from-279-to280-part-2.html
# https://blog.michelanders.nl/2019/02/upgrading-blender-add-ons-from-279-to280-part-4.html

import os
import math
import copy
import mathutils
from datetime import datetime

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from datetime import datetime
# from bpy.app import handlers

bl_info = {
	"name": "Scene Builder",
	"author": "IPv6",
	"version": (1, 4, 34),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}

kWPLSystemSun = "zzz_MainSun"
kWPLEdgesMainCam = "zzz_MainCamera"
kWPLSystemWorld = "World"
kWPLSystemRefPostfix = ["_ref1", "_ref2", "_ref3"]
kWPLSystemAOVFileNodeTag = "#syslayers_aov:"
kWPLSystemAOVObjMaskTag = "#obj_id:"
kWPLSystemAOVObjMask = {
	"body": ["_charb"], 
	"head": ["_head","lip","eye"], 
	"hair": ["_hair"],
	"garm": ["_garm"],
	"garm1": ["_garm1"],
	"garm2": ["_garm2"],
	"garm3": ["_garm3"],
	"garm4": ["_garm4"],
	"far": ["_zzz","zzz_","_sys","sys_","_far","far_"]
	#"mainsun": [kWPLSystemSun]
}
kWPLFrameBindPostfix = "_##"
kWPLFrameBindPostfixNo = "_##!"
kWPLNodePrefix = "#"
kWPLMatTokenWPV = '_v'
kWPLTrafarefToken = "Frame,Trafaref"
kWPLOslQueryMaxObjs = 500
kWPLOslQueryMaxName = 20
kWPLSystemEmpty = "zzz_Support"
kWPLSystemOslScriptPrefix = "sys_sceneQuery"
kWPLSystemOslProps = "DecorC,TexInfluence" #TexInfluence->emission mats, TexScale,TexSize,TexU,TexV -> not really ever used
kWPLSystemOslIncluded = "fg_,_fg"
kWPLSystemOslIgnored = "sys_,_sys"
kWPLSystemRL1Flag = "zzz_MatReestr_sysLayers"
kWPLSystemLayerObj = "sysLayersC,"+kWPLSystemRL1Flag
kWPLSystemLayer = 19
kWPLFaceLayerObj = "sysLayersF,face_,_face,wrap_,_wrap"
kWPLFaceLayer = 18
kWPLSystemLayerRenderOpts = {
	"RenderLayer_s500": {"samples": 10, "max_bounces": 1},
	"RenderLayer_s500_b2": {"samples": 10, "max_bounces": 2},
	"sysLayersD": {"samples": 0},
	"sysLayersT_BgMeshBloom": {"samples": 2},
	"sysLayersT_BgMeshEmi": {"samples": 2}
}
kWPLComposeMainNodeTag = "wplc_sysLayersAOVs"
kWPLComposeMainNodeChecks = "fin_,rl_,la_,lb_,lc_,ld_"

kWPLIslandsVC = "Islands"
kWPLEdgeFlowUV = "Edges"
kWPLEBoneFlowUV = "Bone"

class WPL_G:
	store = {}
######################### ######################### #########################
######################### ######################### #########################
def moveObjectOnLayer(c_object, layId):
	#print("moveObjectOnLayer",c_object.name,layId)
	def layers(l):
		all = [False]*20
		all[l]=True
		return all
	c_object.layers = layers(layId)

def getSysEmpty(context,subname):
	emptyname = kWPLSystemEmpty
	if subname is not None and len(subname)>0:
		emptyname = subname
	empty = context.scene.objects.get(emptyname)
	if empty is None:
		empty = bpy.data.objects.new(emptyname, None)
		empty.empty_draw_size = 0.45
		empty.empty_draw_type = 'PLAIN_AXES'
		context.scene.objects.link(empty)
		context.scene.update()
		if subname is not None and len(subname)>0:
			empty.parent = getSysEmpty(context,"")
	return empty

def makeObjectNoShadow(c_object, andWire, andNoRender):
	c_object.cycles_visibility.camera = True
	c_object.cycles_visibility.diffuse = False
	c_object.cycles_visibility.glossy = False
	c_object.cycles_visibility.transmission = False
	c_object.cycles_visibility.scatter = False
	c_object.cycles_visibility.shadow = False
	if andWire is not None and andWire == True:
		c_object.draw_type = 'WIRE'
	if andNoRender is not None:
		c_object.hide_render = andNoRender
		c_object.cycles_visibility.camera = not andNoRender

def hideObjectWithChilds(obj,ishide):
	obj.hide = ishide
	obj.hide_render = ishide
	if len(obj.children)>0:
		for ch in obj.children:
			hideObjectWithChilds(ch,ishide)

def findChildObjectByName(obj, childName):
	# looking childs
	if len(obj.children)>0:
		for ch in obj.children:
			if childName in ch.name:
				return ch
	# looking in all objects
	for objx in bpy.data.objects:
		if childName in objx.name and obj.name in objx.name:
			return objx
	return None

def select_and_change_mode(obj, obj_mode):
	#print("select_and_change_mode",obj_mode)
	m = bpy.context.mode
	if obj_mode == "EDIT_MESH" or  obj_mode == "EDIT_CURVE":
		obj_mode = "EDIT"
	if obj_mode == "PAINT_VERTEX":
		obj_mode = "VERTEX_PAINT"
	if (obj is not None and bpy.context.scene.objects.active != obj) or m != 'OBJECT':
		# stepping out from currently active object mode, or switch may fail
		try:
			bpy.ops.object.mode_set(mode='OBJECT')
		except:
			print("select_and_change_mode: failed to prep mode", bpy.context.scene.objects.active, obj, m)
	for objx in bpy.data.objects:
		objx.select = False
	if obj:
		if obj.hide == True:
			obj.hide = False
		obj.select = True
		bpy.context.scene.objects.active = obj
		bpy.context.scene.update()
		bpy.ops.object.mode_set(mode=obj_mode)
	return m

def strToTokens(sustrParts):
	if sustrParts is None or len(sustrParts) == 0:
		return []
	sustrParts = sustrParts.replace(";",",")
	sustrParts = sustrParts.replace("+",",")
	sustrParts = sustrParts.replace("|",",")
	stringTokens = [x.strip().lower() for x in sustrParts.split(",")]
	return stringTokens
	
def isTokenInStr(toks, nme, defl = True):
	if toks is None or len(toks) == 0 or nme is None or len(nme) == 0:
		return defl
	nmeLower = nme.lower()
	toksList = [x.strip().lower() for x in toks.split(",")]
	for tok in toksList:
		if tok in nmeLower:
			return True
	return False

# def getWPLOslQueryName():
	# base_name = bpy.path.basename(bpy.data.filepath)
	# if ".blend" in base_name:
		# base_name = base_name.split(".blend", 1)[0]
	# base_name = bpy.path.clean_name(base_name)
	# if kWPLMatTokenWPV in base_name:
		# base_name = base_name.split(kWPLMatTokenWPV, 1)[0]
	# return kWPLSystemOslScriptPrefix+base_name+kWPLOslQueryPostfx
# def getWPLOslPaletteName():
	# base_name = bpy.path.basename(bpy.data.filepath)
	# if ".blend" in base_name:
		# base_name = base_name.split(".blend", 1)[0]
	# base_name = bpy.path.clean_name(base_name)
	# if kWPLMatTokenWPV in base_name:
		# base_name = base_name.split(kWPLMatTokenWPV, 1)[0]
	# return kWPLOslpalettePrefix+base_name+kWPLOslpalettePostfx

def getAllMat():
	mats = list(bpy.data.materials)
	worlds = list(bpy.data.worlds)
	all_mat = mats+worlds
	all_mat = sorted(all_mat, key=lambda k: k.name)
	return all_mat

def getAllMatNodes():
	all_nodes = []
	node_groups = bpy.data.node_groups
	for group in node_groups:
		for node in group.nodes:
			all_nodes.append(node)
	all_mat = getAllMat()
	for mat in all_mat:
		if mat.use_nodes:
			for node in mat.node_tree.nodes:
				all_nodes.append(node)
	compostree = bpy.context.scene.node_tree
	for node in compostree.nodes:
		all_nodes.append(node)
	return all_nodes
	
def getMatNodesBackmapped():
	all_nodes = {}
	all_mat = getAllMat()
	for mat in all_mat:
		if mat.use_nodes:
			for node in mat.node_tree.nodes:
				all_nodes[node] = mat
	return all_nodes

def getFullObjName(obj):
	names = []
	names.append(obj.name.lower())
	rootp = obj.parent
	while (rootp is not None):
		names.append(rootp.name.lower())
		rootp = rootp.parent
	return ",".join(names)

def getIsDumpable(obj):
	if obj is None:
		return False
	if obj.name == kWPLSystemSun or obj.name == kWPLEdgesMainCam:
		return True
	if obj.hide and obj.hide_select and obj.hide_render:
		return False
	if obj.type == 'CURVE' and obj.data.dimensions == '2D':
		return False
	# only ref and animated objects can be dumped in invisible mode
	# only BG elems, FG all: problem with debuggin during alpha-posing... hairs are off -> not dumpes -> problems
	obj_full_name = getFullObjName(obj)
	if obj.hide_render and obj.animation_data is None and (not isTokenInStr(kWPLSystemOslIncluded, obj_full_name)):
		return False
	if (kWPLSystemRL1Flag in obj_full_name) or (kWPLSystemEmpty in obj_full_name):
		return False
	return True

def dumpPythonObject(obj):
	print("- object Dump:")
	for attr in dir(obj):
		if hasattr( obj, attr ):
			print( "...%s = %s" % (attr, getattr(obj, attr)))

def getBoundsRecursive(obj, bounds_cache):
	if obj.name in bounds_cache:
		return bounds_cache[obj.name]
	bbc = [] #[obj.matrix_world.to_translation()]
	isOk = False
	if obj.type == 'MESH' or obj.type == 'CURVE' or obj.type == 'FONT':
		isOk = True
	if (kWPLSystemRefPostfix[0] in obj.name) or (kWPLSystemRefPostfix[1] in obj.name) or (kWPLSystemRefPostfix[2] in obj.name):
		isOk = False
	if isOk:
		bbc.extend([obj.matrix_world * Vector(corner) for corner in obj.bound_box])
	if len(obj.children)>0:
		for chi in obj.children:
			bbc.extend(getBoundsRecursive(chi, bounds_cache))
	if len(bbc) == 0:
		bbc.append(obj.matrix_world.to_translation())
	bounds_cache[obj.name] = bbc
	return bbc

def sortkey4obj(obj_name):
	if obj_name not in bpy.data.objects:
		return "zzzzzzzz"
	cam_obj = bpy.data.objects.get(kWPLEdgesMainCam)
	cam_g_loc = cam_obj.matrix_world.to_translation()
	obj = bpy.data.objects.get(obj_name)
	#obj_full_name = getFullObjName(obj)
	objtype = "z"
	objsubtype = "z"
	objdisttype = 0
	if obj.name == kWPLSystemSun:
		objtype = "a"
	elif obj.name == kWPLEdgesMainCam:
		objtype = "b"
	elif (kWPLSystemRefPostfix[0] in obj.name) or (kWPLSystemRefPostfix[1] in obj.name) or (kWPLSystemRefPostfix[2] in obj.name):
		objtype = "c"
	elif obj.type == 'CURVE' or obj.type == 'FONT' or obj.type == 'ARMATURE':
		objtype = "d"
	elif (obj.animation_data is not None):
		objtype = "e"
	elif isTokenInStr(kWPLSystemOslIncluded, obj.name):
		objtype = "f"
	else:
		obj_g_loc = obj.matrix_world.to_translation()
		objdisttype = (cam_g_loc - obj_g_loc).length
		objdisttype = int(objdisttype)
	rootp = obj
	while (rootp.parent is not None):
		rootp = rootp.parent
		if rootp.type == 'CURVE' or rootp.type == 'FONT' or rootp.type == 'ARMATURE':
			objsubtype = "d"
		elif (rootp.animation_data is not None):
			objsubtype = "e"
		elif isTokenInStr(kWPLSystemOslIncluded, rootp.name):
			objsubtype = "f"
	objdisttype = str(objdisttype).zfill(5)
	sortname = objtype+objsubtype+objdisttype+rootp.name[:50].zfill(50)+obj.name[:50].zfill(50)
	#print ("-", obj.name, sortname)
	return sortname

def oslbake_getscene( context ):
	c_scene = bpy.context.scene
	frameF = c_scene.frame_start
	frameT = c_scene.frame_end
	frameC = c_scene.frame_current
	if len(kWPLSystemOslProps)>0:
		custprpNameParts = [x.strip() for x in kWPLSystemOslProps.split(",")]
	else:
		custprpNameParts = []
	custprpNamePartsMap = {}
	for custprp in custprpNameParts:
		custprp_safe = custprp.replace("(","_")
		custprp_safe = custprp_safe.replace(")","_")
		custprpNamePartsMap[custprp] = custprp_safe
	# frame data and object indexes.
	# important: obj/mat indexes should NOT change between frames
	objs2dump_names = []
	for i,obj in enumerate(bpy.data.objects):
		obj.pass_index = i+kWPLOslQueryMaxObjs
		isOk = 1
		if not getIsDumpable(obj):
			isOk = -1
		if isTokenInStr(kWPLSystemOslIgnored, obj.name):
			isOk = -2
		if (kWPLSystemRefPostfix[0] in obj.name) or (kWPLSystemRefPostfix[1] in obj.name) or (kWPLSystemRefPostfix[2] in obj.name):
			isOk = 2 #always
		if isOk > 0:
			objs2dump_names.append(obj.name)
		#else:
		#	print("OSL-Bake: object skipped:", obj.name, isOk)
	objs2dump_names = sorted(objs2dump_names, key=lambda k: sortkey4obj(k))
	objs2dump_names_full = objs2dump_names
	if len(objs2dump_names) > kWPLOslQueryMaxObjs:
		# too many objects
		print("OSL-Bake: Too many objects ("+str(len(objs2dump_names))+"). Trimming to first "+str(kWPLOslQueryMaxObjs))
		objs2dump_names = objs2dump_names[:kWPLOslQueryMaxObjs]
	else:
		print("OSL-Bake: objects =", str(len(objs2dump_names)))
	
	objs2dump = []
	bounds_cache = {}
	objsI2oMap = {}
	objsLastIndex = 0
	objsMap_frame = {}
	for i,obj_name in enumerate(objs2dump_names):
		# in advance for proper parenting
		if obj_name in bpy.data.objects:
			obj = bpy.data.objects.get(obj_name)
			objs2dump.append(obj)
			objsLastIndex = i+1
			obj.pass_index = objsLastIndex
			objsI2oMap[obj.pass_index] = obj
	matLastIndex = 0
	for m in bpy.data.materials:
		matLastIndex = matLastIndex+1
		m.pass_index = matLastIndex
	for i, obj in enumerate(objs2dump):
		item = {}
		g_loc = obj.matrix_world.to_translation() # * obj.location
		mx_norm = mathutils.Matrix()
		if abs(obj.matrix_world.to_scale()[0])+abs(obj.matrix_world.to_scale()[1])+abs(obj.matrix_world.to_scale()[2]) > 0.0001:
			mx_inv = obj.matrix_world.inverted()
			mx_norm = mx_inv.transposed().to_3x3()
		g_locx = (mx_norm * Vector((1,0,0))).normalized()
		g_locy = (mx_norm * Vector((0,1,0))).normalized()
		g_locz = (mx_norm * Vector((0,0,1))).normalized()
		bbc = getBoundsRecursive(obj, bounds_cache)
		obj_name = obj.name.replace("\"","'")
		if len(obj_name) > kWPLOslQueryMaxName:
			obj_name = obj_name[:kWPLOslQueryMaxName]
		item["name"] = "\""+obj_name+"\""
		item["rootI"] = repr(obj.pass_index) #self! for easier chaining
		item["parentI"] = repr(obj.pass_index) #self! for easier chaining
		rootp = obj.parent
		refsIdx1 = 0
		refsIdx2 = 0
		refsIdx3 = 0
		refsIdx1_dosearch = True
		refsIdx2_dosearch = True
		refsIdx3_dosearch = True
		if kWPLSystemRefPostfix[0] in bpy.data.objects:
			refsIdx1 = bpy.data.objects.get(kWPLSystemRefPostfix[0]).pass_index
		if kWPLSystemRefPostfix[1] in bpy.data.objects:
			refsIdx2 = bpy.data.objects.get(kWPLSystemRefPostfix[1]).pass_index
		if kWPLSystemRefPostfix[2] in bpy.data.objects:
			refsIdx3 = bpy.data.objects.get(kWPLSystemRefPostfix[2]).pass_index
		if (rootp is not None) and (rootp in objs2dump):
			rootI = rootp.pass_index
			item["parentI"] = repr(rootI)
			item["rootI"] = repr(rootI)
			while (rootp is not None) and (rootp in objs2dump):
				if rootp.type == 'EMPTY' and obj.name not in kWPLSystemRefPostfix:
					# checking refs
					if refsIdx1_dosearch:
						refs1Sub = findChildObjectByName(rootp, kWPLSystemRefPostfix[0])
						if refs1Sub is not None:
							refsIdx1 = refs1Sub.pass_index
							refsIdx1_dosearch = False
							print("- object ref1 found:", refs1Sub.name, " for ", obj.name)
					if refsIdx2_dosearch:
						refs2Sub = findChildObjectByName(rootp, kWPLSystemRefPostfix[1])
						if refs2Sub is not None:
							refsIdx2 = refs2Sub.pass_index
							refsIdx2_dosearch = False
							#print("- object ref2 found:", refs2Sub.name, " for ", obj.name)
					if refsIdx3_dosearch:
						refs3Sub = findChildObjectByName(rootp, kWPLSystemRefPostfix[2])
						if refs3Sub is not None:
							refsIdx3 = refs3Sub.pass_index
							refsIdx3_dosearch = False
							#print("- object ref3 found:", refs3Sub.name, " for ", obj.name)
				rootI = rootp.pass_index
				item["rootI"] = repr(rootI)
				rootp = rootp.parent
		item["refsI"] = "point("+repr(refsIdx1)+","+repr(refsIdx2)+","+repr(refsIdx3)+")"
		item["location"] = "point("+repr(g_loc[0])+","+repr(g_loc[1])+","+repr(g_loc[2])+")"
		item["normx"] = "point("+repr(g_locx[0])+","+repr(g_locx[1])+","+repr(g_locx[2])+")"
		item["normy"] = "point("+repr(g_locy[0])+","+repr(g_locy[1])+","+repr(g_locy[2])+")"
		item["normz"] = "point("+repr(g_locz[0])+","+repr(g_locz[1])+","+repr(g_locz[2])+")"
		item["scale"] = "point("+repr(obj.scale[0])+","+repr(obj.scale[1])+","+repr(obj.scale[2])+")"
		item["dims"] = "point("+repr(obj.dimensions[0])+","+repr(obj.dimensions[1])+","+repr(obj.dimensions[2])+")"
		item["bbmin"] = "point("+repr(min(item[0] for item in bbc))+","+repr(min(item[1] for item in bbc))+","+repr(min(item[2] for item in bbc))+")"
		item["bbmax"] = "point("+repr(max(item[0] for item in bbc))+","+repr(max(item[1] for item in bbc))+","+repr(max(item[2] for item in bbc))+")"
		item["iscurve"] = repr(0.0)
		if obj.type == 'CURVE' or obj.type == 'FONT':
			item["iscurve"] = repr(1.0)
		if obj.type == 'CAMERA':
			if obj.data.type == 'ORTHO':
				item["iscurve"] = repr(1.0)
				print("- OLS bake: ortho camera")
		item["color"] = "color("+repr(obj.color[0])+","+repr(obj.color[1])+","+repr(obj.color[2])+")"
		for custprp in custprpNameParts:
			if obj.get(custprp) is not None:
				val = obj[custprp]
				if isinstance(val,int) or isinstance(val,float):
					custcol = Vector((val,val,val))
				else:
					custcol = val
				print("- Found object prop:","["+obj.name+"]:",custprp) #,val,custcol
			else:
				custcol = Vector((0,0,0))
			#print("Custom object parameters", obj.name, custprp, custcol)
			item[custprp] = "color("+repr(custcol[0])+","+repr(custcol[1])+","+repr(custcol[2])+")"
		objsMap_frame[obj.name] = item
	WPL_G.store["osl_frame"+str(frameC)] = objsMap_frame
	frames_key = []
	frames_idx = []
	for frm in range(int(frameF), int(frameT)+1):
		if "osl_frame"+str(frm) in WPL_G.store:
			frames_key.append("osl_frame"+str(frm))
			frames_idx.append(frm)
	if frameC not in frames_idx:
		frames_key.append("osl_frame"+str(frameC))
		frames_idx.append(frameC)
	print("OSL-Bake: frames in cache:", frames_key, "current frame:", frameC)
	osl_content = []
	osl_content.append("/*")
	osl_content.append(" WARNING: text below is autogenerated, DO NOT EDIT.")
	osl_content.append(" TIMESTAMP: "+str(datetime.now()))
	osl_content.append(" FILE: "+bpy.data.filepath)
	osl_content.append(" FRAMES: "+",".join(frames_key))
	#for k in objs2dump_names_full:
	#	osl_content.append(k+": "+sortkey4obj(k))
	osl_content.append("*/")
	osl_content.append("")
	#osl_content.append("#define STRSTR_INIT string splitTemp[3]")
	#osl_content.append("#define STRSTR(orig,substr) (split((orig), splitTemp, (substr), 2) > 1)")
	osl_content.append("#define DUMPLEN "+str(objsLastIndex))
	osl_content.append("shader sceneQuery (")
	osl_content.append(" int in_frame = 0,")
	osl_content.append(" int by_index = 0,")
	osl_content.append(" string name_objColor = \"\",")
	osl_content.append(" string name_objTok = \"\",")

	osl_content.append(" output int index = 0,")
	osl_content.append(" output int parent_index = 0,")
	osl_content.append(" output int root_index = 0,")
	osl_content.append(" output point g_Location = point(0,0,0),")
	osl_content.append(" output point g_normalX = point(0,0,0),")
	osl_content.append(" output point g_normalY = point(0,0,0),")
	osl_content.append(" output point g_normalZ = point(0,0,0),")
	osl_content.append(" output point g_boundsMax = point(0,0,0),")
	osl_content.append(" output point g_boundsMin = point(0,0,0),")
	osl_content.append(" output point scale = point(0,0,0),")
	osl_content.append(" output point dimensions = point(0,0,0),")
	osl_content.append(" output color objColor = color(0,0,0),")
	osl_content.append(" output float objIsCurve = 0.0,")
	osl_content.append(" output float objIsNameTok = 0.0,")
	osl_content.append(" output point objRefsIdx = point(0,0,0),")
	osl_content.append("){")
	#osl_content.append("STRSTR_INIT;")
	for fi, frame_key in enumerate(frames_key):
		objsMap = WPL_G.store[frame_key]
		objsData = []
		objsData_frameC = []
		for obj in objs2dump:
			if (obj.name not in objsMap_frame):
				print("OSL-Bake: invalid frame cache, obj not found:",obj.name)
				return None
			if (obj.name not in objsMap):
				objsData.append(objsMap_frame[obj.name])
			else:
				objsData.append(objsMap[obj.name])
			objsData_frameC.append(objsMap_frame[obj.name])
		if fi > 0:
			osl_content.append("else") # ot avoid OSL optimizations...
		if fi < len(frames_key)-1:
			osl_content.append(" if (in_frame == "+str(frames_idx[fi])+"){ // baked frame "+str(frames_idx[fi]))
		else:
			#osl_content.append(" { // baked frame "+str(frames_idx[fi]))
			osl_content.append(" if (in_frame >= 0){ // baked frame "+str(frames_idx[fi]))
		osl_content.append("  int pIndex[DUMPLEN] = {"+",".join([ item['parentI'] for item in objsData_frameC ])+"};")
		osl_content.append("  int rIndex[DUMPLEN] = {"+",".join([ item['rootI'] for item in objsData_frameC ])+"};")
		osl_content.append("  point refsIdx[DUMPLEN] = {"+",".join([ item['refsI'] for item in objsData_frameC ])+"};")
		osl_content.append("  string sNames[DUMPLEN] = {"+",".join([ item['name'] for item in objsData ])+"};")
		osl_content.append("  point sLocas[DUMPLEN] = {"+",".join([ item['location'] for item in objsData ])+"};")
		osl_content.append("  point sScales[DUMPLEN] = {"+",".join([ item['scale'] for item in objsData ])+"};")
		osl_content.append("  point sNormalX[DUMPLEN] = {"+",".join([ item['normx'] for item in objsData ])+"};")
		osl_content.append("  point sNormalY[DUMPLEN] = {"+",".join([ item['normy'] for item in objsData ])+"};")
		osl_content.append("  point sNormalZ[DUMPLEN] = {"+",".join([ item['normz'] for item in objsData ])+"};")
		osl_content.append("  point sDimens[DUMPLEN] = {"+",".join([ item['dims'] for item in objsData ])+"};")
		osl_content.append("  point sBbmax[DUMPLEN] = {"+",".join([ item['bbmax'] for item in objsData ])+"};")
		osl_content.append("  point sBbmin[DUMPLEN] = {"+",".join([ item['bbmin'] for item in objsData ])+"};")
		osl_content.append("  point sColor[DUMPLEN] = {"+",".join([ item['color'] for item in objsData ])+"};")
		osl_content.append("  float isCurve[DUMPLEN] = {"+",".join([ item['iscurve'] for item in objsData ])+"};")
		for custprp in custprpNameParts:
			custprp_safe = custprpNamePartsMap[custprp]
			osl_content.append("  point cp"+custprp_safe+"[DUMPLEN] = {"+",".join([ item[custprp] for item in objsData ])+"};")
		osl_content.append("  int iFoundIndex = -1;")
		osl_content.append("  if(by_index > 0){")
		osl_content.append("   iFoundIndex = by_index-1;")
		osl_content.append("  }")
		#osl_content.append("  else")
		#osl_content.append("  if(strlen(by_name_equality)>0){")
		#osl_content.append("   for(int i=0;i<DUMPLEN;i++){")
		#osl_content.append("    if(sNames[i] == by_name_equality){")
		#osl_content.append("     iFoundIndex = i;")
		#osl_content.append("     break;")
		#osl_content.append("    }")
		#osl_content.append("   }")
		#osl_content.append("  }")
		osl_content.append("  if(iFoundIndex >= 0 && iFoundIndex < DUMPLEN){")
		osl_content.append("   index = iFoundIndex+1;") #osl_content.append("  index = sIndex[iFoundIndex];")
		osl_content.append("   parent_index = pIndex[iFoundIndex];")
		osl_content.append("   root_index = rIndex[iFoundIndex];")
		osl_content.append("   g_Location = sLocas[iFoundIndex];")
		osl_content.append("   g_normalX = sNormalX[iFoundIndex];")
		osl_content.append("   g_normalY = sNormalY[iFoundIndex];")
		osl_content.append("   g_normalZ = sNormalZ[iFoundIndex];")
		osl_content.append("   g_boundsMax = sBbmax[iFoundIndex];")
		osl_content.append("   g_boundsMin = sBbmin[iFoundIndex];")
		osl_content.append("   scale = sScales[iFoundIndex];")
		osl_content.append("   dimensions = sDimens[iFoundIndex];")
		osl_content.append("   objIsCurve = isCurve[iFoundIndex];")
		osl_content.append("   objRefsIdx = refsIdx[iFoundIndex];")
		#osl_content.append("   if(strlen(name_objTok)>0 && STRSTR(sNames[iFoundIndex], name_objTok)){objIsNameTok=1;}else{objIsNameTok=0;}")
		osl_content.append("   if(strlen(name_objTok)>0 && startswith(sNames[iFoundIndex], name_objTok)){objIsNameTok=1;}else{objIsNameTok=0;}")
		osl_content.append("   if(strlen(name_objColor)==0){objColor = sColor[iFoundIndex];}else{")
		for custprp in custprpNameParts:
			custprp_safe = custprpNamePartsMap[custprp]
			osl_content.append("    if(name_objColor==\""+custprp+"\"){objColor = cp"+custprp_safe+"[iFoundIndex];};")
		#osl_content.append(" printf(\"(%i. %i. %f %f %f)\", in_frame, iFoundIndex, g_Location[0], g_Location[1], g_Location[2]);") # DBG
		osl_content.append("   }")
		osl_content.append("  }")
		osl_content.append("  return;")
		osl_content.append(" }")
	osl_content.append("}")
	osl_content_final = "\n".join(osl_content)
	#textblock = bpy.data.texts.get(getWPLOslQueryName())
	#if not textblock:
	#	textblock = bpy.data.texts.new(getWPLOslQueryName())
	#else:
	#	textblock.clear()
	#textblock.write("\n".join(osl_content))
	#self.report({'INFO'}, "Scene query baked, objects="+str(objsLastIndex))
	return osl_content_final
	
def setSceneEditingDefauts(enabCycles, enabGP):
	c_scene = bpy.context.scene
	# Resettings tools to defauls
	c_scene.tool_settings.sculpt.use_symmetry_x = False
	c_scene.tool_settings.sculpt.use_symmetry_y = False
	c_scene.tool_settings.sculpt.use_symmetry_z = False
	c_scene.tool_settings.grease_pencil_source = 'OBJECT'
	c_scene.tool_settings.gpencil_stroke_placement_view3d = 'SURFACE'
	bpy.data.brushes["Grab"].use_projected = True
	bpy.data.brushes["Smooth"].use_projected = True
	bpy.data.brushes["Inflate/Deflate"].use_projected = True
	#bpy.data.brushes["Inflate/Deflate"].direction = 'ADD'
	if enabCycles > 0:
		c_scene.render.engine = 'CYCLES'
		c_scene.cycles.device = 'CPU'
		c_scene.cycles.shading_system = True # OSL!!!
		c_scene.cycles.feature_set = 'EXPERIMENTAL'
		c_scene.cycles.samples = 100
		c_scene.cycles.preview_samples = 3
		c_scene.cycles.use_layer_samples = 'USE'
		c_scene.cycles.max_bounces = 1
		c_scene.cycles.transparent_max_bounces = 100
		c_scene.cycles.diffuse_bounces = 3
		c_scene.cycles.glossy_bounces = 3
		c_scene.cycles.transmission_bounces = 3
		c_scene.cycles.volume_bounces = 3
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			c_space = area.spaces[0]
			c_space.clip_start = 0.1
			c_space.clip_end = 10000
			#c_space = bpy.data.screens["Default"]
			if enabGP >= 0:
				if enabGP > 0:
					c_space.show_grease_pencil = True
				else:
					c_space.show_grease_pencil = False
	
######################### ######################### #########################
######################### ######################### #########################
class wplscene_updnodeval(bpy.types.Operator):
	bl_idname = "object.wplscene_updnodeval"
	bl_label = "Set value into nodes"
	bl_options = {'REGISTER', 'UNDO'}

	opt_autoSetFromMainObjs = BoolProperty(
		name		= "Also Auto-set from Sun/Cam",
		default	 = True,
	)

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		def checkNode(node, keyvalsMap):
			changes = 0
			if kWPLSystemAOVObjMaskTag in node.label:
				return 0 # only automatic, ignoring
			if len(node.outputs)>0:
				#print("- Node: '%s' -> '%s'" % (node.bl_label, node.outputs[0]))
				for nntag in keyvalsMap:
					if nntag in node.label:
						node.outputs[0].default_value = float(keyvalsMap[nntag])
						changes = changes+1
						print("- Switching: '%s' -> '%s'" % (node.label, node.outputs[0].default_value))
			return changes
		def setNodeValues(mats, keyvalsMap):
			changed = 0
			for node in all_nodes:
				changed = changed + checkNode(node, keyvalsMap)
			return changed
		kvmap = {}
		sun_obj = context.scene.objects.get(kWPLSystemSun)
		cam_obj = context.scene.objects.get(kWPLEdgesMainCam)
		if sun_obj is None or cam_obj is None:
			self.report({'ERROR'}, "Main sun/cam not found")
			return {'CANCELLED'}
		if self.opt_autoSetFromMainObjs and len(sun_obj.keys()) > 1:
			for sun_prop in sun_obj.keys():
				if kWPLNodePrefix in sun_prop:
					#print("-", kWPLSystemSun, "prop found:", sun_obj[sun_prop])
					kvmap[sun_prop] = sun_obj[sun_prop]
		if self.opt_autoSetFromMainObjs and len(cam_obj.keys()) > 1:
			for cam_prop in cam_obj.keys():
				if kWPLNodePrefix in cam_prop:
					#print("-", kWPLEdgesMainCam, "prop found:", cam_obj[cam_prop])
					kvmap[cam_prop] = cam_obj[cam_prop]
		bakeOpts = context.scene.wplScene2OslSettings
		kvmap[bakeOpts.nodeNameTag2] = bakeOpts.nodeNameValue
		print("- setting nodeValues:", kvmap)
		all_nodes = getAllMatNodes()
		itogo_ok = setNodeValues(all_nodes, kvmap)
		self.report({'INFO'}, "Nodes updated: "+str(itogo_ok))
		return {'FINISHED'}

#def frh_start_timer(scene):
#	WPL_G.store["frh_TIMER"] = datetime.now()
#def frh_elapsed(dummy):
#	print("\nStats: Elapsed:", datetime.now() - WPL_G.store["frh_TIMER"])
class wplscene_prep2render(bpy.types.Operator):
	bl_idname = "object.wplscene_prep2render"
	bl_label = "Prepare to render"
	bl_options = {'REGISTER', 'UNDO'}

	opt_renderPercentage = IntProperty(
		name		= "Render percentage",
		default	 = 200,
	)
	opt_mainSamples = IntProperty(
		name		= "Main samples",
		default	 = 50,
	)
	opt_syslSamples = IntProperty(
		name		= "Syslayers samples",
		default	 = 5,
	)
	opt_finalMode = BoolProperty(
		name		= "Final rendering",
		default	 = True,
	)
	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		# common data & sanity checks
		getSysEmpty(context,"")
		setSceneEditingDefauts(1, 1)
		if kWPLSystemWorld not in bpy.data.worlds:
			self.report({'ERROR'}, "Default World not found: "+kWPLSystemWorld)
			return {'CANCELLED'}
		rl1_obj = context.scene.objects.get(kWPLSystemRL1Flag)
		if rl1_obj is None:
			self.report({'ERROR'}, "Sys obj not found: "+kWPLSystemRL1Flag)
			return {'CANCELLED'}
		sun_obj = context.scene.objects.get(kWPLSystemSun)
		if sun_obj is None:
			self.report({'ERROR'}, "Main sun not found: "+kWPLSystemSun)
			return {'CANCELLED'}
		cam_obj = context.scene.objects.get(kWPLEdgesMainCam)
		if cam_obj is None:
			self.report({'ERROR'}, "Main cam not found: "+kWPLEdgesMainCam)
			return {'CANCELLED'}
		c_scene = bpy.context.scene
		all_nodes = getAllMatNodes()
		active_obj = context.scene.objects.active
		bakeOpts = context.scene.wplScene2OslSettings
		final_render_name = os.path.basename(c_scene.render.filepath)
		if len(final_render_name) == 0:
			final_render_name = os.path.basename(bpy.data.filepath)
			final_render_name = os.path.splitext(final_render_name)[0]
		final_render_path = os.path.dirname(c_scene.render.filepath)
		if len(final_render_path) == 0:
			# folder with file itself
			final_render_path = os.path.dirname(bpy.data.filepath)
			c_scene.render.filepath = final_render_path+os.path.sep+final_render_name
		#final_render_aovpath = final_render_path+os.path.sep+final_render_name+"_aovs"+os.path.sep
		final_render_aovpath = final_render_path+os.path.sep # same as main, easier to extract all...
		if len(final_render_name) == 0 or "/" in final_render_name or "." in final_render_name:
			self.report({'ERROR'}, "Invalid name of output file: "+final_render_name)
			return {'CANCELLED'}
		if not os.path.isdir(final_render_path):
			self.report({'ERROR'}, "Output folder not found: "+final_render_path)
			return {'CANCELLED'}
		if not os.path.exists(final_render_aovpath):
			os.makedirs(final_render_aovpath)
		frameF = c_scene.frame_start
		frameT = c_scene.frame_end
		frameC = c_scene.frame_current
		print("- frames: [",frameF,",",frameT,"], current:",frameC)
		if self.opt_finalMode and frameF != frameT:
			for frm in range(int(frameF), int(frameT)+1):
				if "osl_frame"+str(frm) not in WPL_G.store:
					self.report({'ERROR'}, "Animation detected, but frame not baked: "+str(frm))
					return {'CANCELLED'}
		if frameC < frameF or frameC > frameT:
			if self.opt_finalMode:
				self.report({'ERROR'}, "Invalid current frame, range="+str(frameF)+":"+str(frameT))
				return {'CANCELLED'}

		# object->layers mapping
		for i in range(0,20):
			c_scene.layers[i] = True
		objs2dump = []
		for lobj in bpy.data.objects:
			if not getIsDumpable(lobj):
				continue
			objs2dump.append(lobj)
		for lobj in objs2dump:
			#obj_name = lobj.name.lower()
			obj_name_2top = getFullObjName(lobj)
			isHighLayers = None
			#if isTokenInStr(kWPLEdgesLayerObj, obj_name_2top):
			#	isHighLayers = kWPLEdgesLayer
			if isTokenInStr(kWPLFaceLayerObj, obj_name_2top):
				isHighLayers = kWPLFaceLayer
			if isTokenInStr(kWPLSystemLayerObj, obj_name_2top):
				isHighLayers = kWPLSystemLayer
			if isHighLayers is None:
				#print("- moving", lobj.name, "to base")
				moveObjectOnLayer(lobj,0)
			else:
				#print("- moving", lobj.name, "to", isHighLayers)
				moveObjectOnLayer(lobj, isHighLayers)
		#moveObjectOnLayer(rl1_obj,kWPLSystemLayer) # after all other objects
		
		# mist distance calculations
		# minObjDepth = 999
		# maxObjDepth = 0
		# bounds_cache = {}
		# for lobj in objs2dump:
		# 	if lobj.name == cam_obj.name:
		# 		continue
		# 	if lobj.type != 'MESH':
		# 		# suns, etc can be very far
		# 		continue
		# 	isIgnored = False
		# 	obj_name_2top = getFullObjName(lobj)
		# 	if isTokenInStr(kWPLSystemDepthIgnored, obj_name_2top):
		# 		isIgnored = True
		# 	if lobj.animation_data is not None:
		# 		# some objects are removed from scene by moving very far in some frames
		# 		isIgnored = True
		# 	if isIgnored:
		# 		continue
		# 	bbc = getBoundsRecursive(lobj, bounds_cache)
		# 	for item in bbc:
		# 		dist = (cam_obj.location - item).length
		# 		if dist < minObjDepth:
		# 			minObjDepth = dist
		# 		if dist > maxObjDepth:
		# 			maxObjDepth = dist
		# 			#print("> max depth", lobj.name, maxObjDepth)
		# print("Mist: min-max scene depth",minObjDepth,maxObjDepth)

		# OSL preparations
		# need active non-linked object to compile OSL!
		#bpy.ops.object.wplscene_bakequery2osl()
		osl_scene_bake = oslbake_getscene(context)
		if osl_scene_bake is None:
			self.report({'ERROR'}, "Can`t bake OSL")
			return {'CANCELLED'}
		osl_file_path = final_render_aovpath+final_render_name+"_scene_bake.osl"
		oso_file_path = final_render_aovpath+final_render_name+"_scene_bake.oso"
		if os.path.exists(osl_file_path):
			os.remove(osl_file_path)
		if os.path.exists(oso_file_path):
			os.remove(oso_file_path)
		with open(osl_file_path,"w") as osl_file:
			osl_file.write(osl_scene_bake)
		for node in all_nodes:
			if node.bl_idname == 'ShaderNodeScript' and kWPLSystemOslScriptPrefix in node.label:
				node.mode = 'EXTERNAL'
				node.filepath = osl_file_path
		
		# rendering preparations
		c_scene.render.resolution_percentage = self.opt_renderPercentage
		# render_layer preparations
		if len(c_scene.render.layers)>0:
			#Material auto-override
			all_mat = getAllMat()
			for i, lr in enumerate(c_scene.render.layers):
				#print("Layer",i,lr.name)
				lr.material_override = None
				for mat in all_mat:
					if lr.name.lower() in mat.name.lower():
						print("RenderLayer: material override:",mat.name,"->",lr.name)
						lr.material_override = mat
				if i == 0:
					lr.cycles.use_denoising = True
					lr.use_pass_shadow = True
					lr.use_pass_z = True
					#lr.use_pass_normal = True
					#bpy.data.worlds[kWPLSystemWorld].mist_settings.falloff = 'LINEAR'
					#bpy.data.worlds[kWPLSystemWorld].mist_settings.start = minObjDepth
					#bpy.data.worlds[kWPLSystemWorld].mist_settings.depth = maxObjDepth
				else:
					lr.cycles.use_denoising = False
					lr.use_pass_shadow = False
					lr.use_pass_z = False
					#lr.use_pass_normal = False
				lr.use_pass_mist = False
				lr.use_pass_diffuse_color = True
				lr.use_pass_combined = True
				lr.use_pass_glossy_color = True
				lr.use_pass_transmission_color = True
				lr.use_pass_subsurface_color = True
				lr.use_pass_emit = True
				lr.use_pass_object_index = True
				lr.use_pass_ambient_occlusion = False
				if i == 0:
					lr.samples = self.opt_mainSamples
				else:
					lr.samples = self.opt_syslSamples
				if lr.name in kWPLSystemLayerRenderOpts:
					opts = kWPLSystemLayerRenderOpts[lr.name]
					if "max_bounces" in opts:
						c_scene.cycles.max_bounces = float(opts["max_bounces"])
					sampleFac = opts["samples"]
					sampleFinal = int(lr.samples * sampleFac)
					if sampleFinal < 1:
						# No antialiasing needed, important
						# Or outlines will be broken
						lr.samples = 1
					elif self.opt_finalMode:
						lr.samples = sampleFinal
				if self.opt_finalMode:
					lr.use = True
				for rli in range(0,20):
					lr.layers[rli] = True
					lr.layers_exclude[rli] = False
					# edges-only
					# if rli == kWPLEdgesLayer:
					# 	if isTokenInStr(kWPLEdgesLayerObj, lr.name):
					# 		lr.layers_exclude[rli] = False
					# 	else:
					# 		lr.layers_exclude[rli] = True
					# sysLayersC-only
					if rli == kWPLSystemLayer:
						if isTokenInStr(kWPLSystemLayerObj, lr.name):
							lr.layers_exclude[rli] = False
						else:
							lr.layers_exclude[rli] = True
					# face-only
					if isTokenInStr(kWPLFaceLayerObj, lr.name):
						lr.layers_exclude[rli] = True
						if rli == kWPLFaceLayer:
							lr.layers_exclude[rli] = False
					elif rli == kWPLFaceLayer:
						lr.layers_exclude[rli] = True
		if self.opt_finalMode:
			c_scene.render.use_border = False
			
		# compositing preparations. After OSL bake (proper indexes needed)
		objs2tag = {}
		for lobj in objs2dump:
			if lobj.type != 'MESH' and lobj.type != 'CURVE' and lobj.type != 'FONT':
				# not visible in compositor anyway
				continue
			if (kWPLSystemRefPostfix[0] in lobj.name) or (kWPLSystemRefPostfix[1] in lobj.name) or (kWPLSystemRefPostfix[2] in lobj.name):
				continue
			obj_name = lobj.name.lower()
			# saving tagged sets
			for i, (tag_k, tag_vals) in enumerate(kWPLSystemAOVObjMask.items()):
				if tag_k not in objs2tag:
					objs2tag[ str(tag_k) ] = []
				for tag in tag_vals:
					if (tag.lower() in obj_name): # and lobj.pass_index <= kWPLOslQueryMaxObjs: <- far objects can be OSL-ignored
						objs2tag[ str(tag_k) ].append(lobj)
		for tag_k in objs2tag:
			print("Compositing: obj_id:", tag_k, len(objs2tag[tag_k]))
			#print(objs2tag[tag_k])
		all_nodes_backmap = getMatNodesBackmapped()
		for node in all_nodes:
			# check for compositing output to be connected - can be missed in case of broken libs import!!!
			#print(" -- node", node.label, node.name, node.type)
			if (node.type == 'VIEWER') or (node.type == 'COMPOSITE'):
				#dumpPythonObject(node.inputs[0])
				if node.inputs[0].is_linked == False:
					self.report({'ERROR'}, "Compisiting BROKEN: Viewer/Composite not connected")
					return {'CANCELLED'}
			if node.type == 'GROUP' and kWPLComposeMainNodeTag in node.node_tree.name:
				for inp in node.inputs:
					if isTokenInStr(kWPLComposeMainNodeChecks, inp.name) and inp.is_linked == False:
						self.report({'ERROR'}, "Compisiting BROKEN: Composite input not connected: "+inp.name)
						return {'CANCELLED'}
			if kWPLSystemAOVFileNodeTag in node.label:
				postfix = "aov"
				if len(node.label) > len(kWPLSystemAOVFileNodeTag):
					postfix = node.label[len(kWPLSystemAOVFileNodeTag):]
				if not self.opt_finalMode:
					postfix = postfix + "_test"
				node.format.file_format = 'OPEN_EXR_MULTILAYER'  # 'OPEN_EXR'
				node.format.color_mode = 'RGBA'
				node.format.color_depth = '16'
				node.base_path = final_render_aovpath+final_render_name+"_"+postfix+"_"
				print("Compositing: AOVs path:", node.base_path)
			if kWPLSystemAOVObjMaskTag in node.label:
				node_inpts = node.label.split(":")
				#print("obj_id node:", node.type, node_inpts, node_inpts[1])
				if node.type == 'TEX_IMAGE':
					# local packed Image Texture
					if len(node_inpts) >= 2:
						node_tag = str(node_inpts[1])
						if node in all_nodes_backmap:
							node_tag = node_tag.replace("<mat>", all_nodes_backmap[node].name)
						elif kWPLMatTokenWPV in node_tag:
							node_tag = node_tag.rpartition(kWPLMatTokenWPV)[0]
						img = bpy.data.images.get(node_tag)
						if img is None:
							img = bpy.data.images.get(node_tag+".png")
						if img is None:
							img = bpy.data.images.get(node_tag+".jpg")
						if img is not None:
							node.image = img
						else:
							#print("- Material texture: failed to find image", node.label, all_nodes_backmap[node].name, node_tag)
							#print("- bpy.data.images", bpy.data.images.keys())
							node.image = None
				else:
					finalIndex = None
					if len(node_inpts) >= 2:
						node_tag = str(node_inpts[1])
						if node_tag in objs2tag:
							tagged = objs2tag[ node_tag ]
							idx = int(node_inpts[2])
							finalIndex = kWPLOslQueryMaxObjs
							if idx >= 0 and idx < len(tagged):
								lobj = tagged[idx]
								finalIndex = lobj.pass_index
						else:
							# object name
							if node_tag in bpy.data.objects:
								node_obj = bpy.data.objects.get(node_tag)
								finalIndex = node_obj.pass_index
					if finalIndex is not None:
						if node.type == 'VALUE':
							node.outputs[0].default_value = finalIndex
						if node.type == 'ID_MASK':
							node.index = finalIndex
		isErrorsFound = False
		if self.opt_finalMode:
			# generating islands, edge unwrap and bone normals for all "_fg_" objects
			# if required map not already present
			for obj in objs2dump:
				if obj.hide_render == True:
					# ignored
					continue
				if obj.type == 'MESH' and isTokenInStr(kWPLSystemOslIncluded, getFullObjName(obj) ):
					active_mesh = obj.data
					# uv_layer_ob = active_mesh.uv_textures.get(kWPLEdgeFlowUV)
					# if uv_layer_ob is None:
					# 	print("- adding extra map:", getFullObjName(obj), kWPLEdgeFlowUV)
					# 	select_and_change_mode(obj,'OBJECT')
					# 	bpy.ops.object.wpluvvg_unwrap_edges(opt_tranfType='DST_PRJ') # WPL
					vc_layer_ob = active_mesh.vertex_colors.get(kWPLIslandsVC)
					if vc_layer_ob is None:
						print("- adding extra map:", getFullObjName(obj), kWPLIslandsVC)
						select_and_change_mode(obj,'OBJECT')
						bpy.ops.object.wpluvvg_islandsmid() # WPL
					uv_layer_ob = active_mesh.uv_textures.get(kWPLEBoneFlowUV+"_nrmXY")
					vg_layer_ob = obj.vertex_groups.get("head")
					if uv_layer_ob is None and vg_layer_ob is not None:
						print("- extra map not found:", getFullObjName(obj), kWPLEBoneFlowUV+"_nrmXY")
						#print("- adding extra map:", getFullObjName(obj), kWPLEBoneFlowUV+"_nrmXY")
						#print("-- Using CURRENT Camera position!")
						#select_and_change_mode(obj,'OBJECT')
						#bpy.ops.object.wpluvvg_unwrap_bonenrm() # WPL
						isErrorsFound = True
						self.report({'ERROR'}, "FINAL: No bone-normals in "+getFullObjName(obj))
		if isErrorsFound == False:
			if self.opt_finalMode:
				self.report({'INFO'}, "FINAL: "+str(int(c_scene.render.resolution_x*c_scene.render.resolution_percentage/100.0))+":"+str(int(c_scene.render.resolution_y*c_scene.render.resolution_percentage/100.0)))
				#if "frh" not in WPL_G.store:
				#	WPL_G.store["frh"] = 1
				#	handlers.render_pre.append(frh_start_timer)
				#	handlers.render_stats.append(frh_elapsed)
			else:
				self.report({'INFO'}, "TEST prepared")
		return {'FINISHED'}

class wplscene_trafa(bpy.types.Operator):
	bl_idname = "object.wplscene_trafa"
	bl_label = "Setup bg image"
	bl_options = {'REGISTER', 'UNDO'}

	opt_opacity = IntProperty(
		name		= "Opacity",
		default	 = 100,
	)
	opt_imge = StringProperty(
		name		= "Image",
		default	 = "",
	)

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		for area in bpy.context.screen.areas:
			if area.type == 'VIEW_3D':
				c_space = area.spaces[0]
				if self.opt_opacity > 0:
					c_space.show_background_images = True
				else:
					c_space.show_background_images = False
				if len(c_space.background_images) > 0:
					bm = c_space.background_images[0]
					bm.show_on_foreground = True
					# no offset -> easy to forget //
					bm.offset_x = 0.0
					bm.offset_y = 0.0
					if self.opt_opacity > 0:
						bm.opacity = float(self.opt_opacity)/float(100.0)
					if len(self.opt_imge) > 0:
						bm.image = bpy.data.images[self.opt_imge]
		return {'FINISHED'}

class wplscene_framebind(bpy.types.Operator):
	bl_idname = "object.wplscene_framebind"
	bl_label = "Bind visibility to frames"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		objs2check = [obj for obj in bpy.context.scene.objects]
		c_scene = bpy.context.scene
		bindedObj = 0
		bindedModf = 0
		bindedShk = 0
		bindedCon = 0
		frameF = c_scene.frame_start
		frameT = c_scene.frame_end
		frames = []
		frames.append(0)
		for frm in range(int(frameF), int(frameT)+1):
			frames.append(frm)
		print("- frames: [",frameF,",",frameT,"]")
		for obj in objs2check:
			# Object visibility
			if (kWPLFrameBindPostfix in obj.name) or (kWPLFrameBindPostfixNo in obj.name):
				bindedObj = bindedObj+1
				ini_hide = obj.hide
				ini_hide_render = obj.hide_render
				for frm in frames:
					if (kWPLFrameBindPostfixNo in obj.name):
						frmKey = kWPLFrameBindPostfixNo+str(frm)
						frmHide = False
						if frmKey in obj.name:
							frmHide = True
					else:
						frmKey = kWPLFrameBindPostfix+str(frm)
						frmHide = True
						if frmKey in obj.name:
							frmHide = False
					#if frm == 0:
					#	frmHide = False
					obj.hide = frmHide
					obj.hide_render = frmHide
					obj.keyframe_insert("hide", frame = frm)
					obj.keyframe_insert("hide_render", frame = frm)
					print("-",frm, "obj:",obj.name, "hide=", frmHide)
				obj.hide = ini_hide
				obj.hide_render = ini_hide_render
			# modifier visilibity
			for md in obj.modifiers:
				if (kWPLFrameBindPostfix in md.name) or (kWPLFrameBindPostfixNo in md.name):
					bindedModf = bindedModf+1
					ini_show_render = md.show_render
					ini_show_viewport = md.show_viewport
					for frm in frames:
						if (kWPLFrameBindPostfixNo in md.name):
							frmKey = kWPLFrameBindPostfixNo+str(frm)
							frmShow = True
							if frmKey in md.name:
								frmShow = False
							#if frm == 0:
							#	frmShow = False
						else:
							frmKey = kWPLFrameBindPostfix+str(frm)
							frmShow = False
							if frmKey in md.name:
								frmShow = True
							#if frm == 0:
							#	frmShow = True
						md.show_render = frmShow
						md.show_viewport = frmShow
						md.keyframe_insert("show_render", frame = frm)
						md.keyframe_insert("show_viewport", frame = frm)
						print("-",frm, "modf:",md.name, "show=", frmShow)
					md.show_render = ini_show_render
					md.show_viewport = ini_show_viewport
			# shapekey visibility
			if (obj.type == 'MESH' or obj.type == 'CURVE') and (obj.data is not None) and (obj.data.shape_keys is not None) and len(obj.data.shape_keys.key_blocks) > 0:
				for shk in obj.data.shape_keys.key_blocks:
					#shk = obj.data.shape_keys[shk_key]
					if kWPLFrameBindPostfix in shk.name:
						bindedShk = bindedShk+1
						ini_mute = shk.mute
						for frm in frames:
							frmKey = kWPLFrameBindPostfix+str(frm)
							frmHide = True
							if frmKey in shk.name:
								frmHide = False
							#if frm == 0:
							#	frmHide = True
							shk.mute = frmHide
							shk.keyframe_insert("mute", frame = frm)
							print("-",frm, "shapekey:",shk.name, "mute=", frmHide)
						shk.mute = ini_mute
			# constrains
			if obj.constraints is not None:
				for constr in obj.constraints:
					if (kWPLFrameBindPostfix in constr.name) or (kWPLFrameBindPostfixNo in constr.name):
						bindedCon = bindedCon+1
						ini_mute = constr.mute
						for frm in frames:
							if (kWPLFrameBindPostfixNo in constr.name):
								frmKey = kWPLFrameBindPostfixNo+str(frm)
								frmHide = False
								if frmKey in constr.name:
									frmHide = True
								#if frm == 0:
								#	frmHide = True
							else:
								frmKey = kWPLFrameBindPostfix+str(frm)
								frmHide = True
								if frmKey in constr.name:
									frmHide = False
								#if frm == 0:
								#	frmHide = False
							constr.mute = frmHide
							constr.keyframe_insert("mute", frame = frm)
							print("-",frm, "constr:",constr.name, "mute=", frmHide)
						constr.mute = ini_mute
		result = "Binded "+str(bindedObj)+" objects, "+str(bindedModf)+" modf, "+str(bindedShk)+" shapekeys,"+str(bindedCon)+" constr"
		print("Results:", result)
		self.report({'INFO'}, result)
		return {'FINISHED'}

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class WPLScene2OslSettings(bpy.types.PropertyGroup):
	# nodeNameTag = bpy.props.StringProperty(
	# 	name		= "Node tag",
	# 	default	 = "#isdebug"
	# )
	nodeNameTag2 = EnumProperty( # main values, used in material nodes
		name="Source", default="#isdebug",
		items=(("#isdebug", "#isdebug", ""), ("#sun_ispoint", "#sun_ispoint", ""))
	)
	nodeNameValue = bpy.props.StringProperty(
		name		= "Node value",
		default	 = "0"
	)

class WPLSceneBuilder_Panel1(bpy.types.Panel):
	bl_label = "Scene builder"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	#bl_context = "objectmode"
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		bakeOpts = context.scene.wplScene2OslSettings
		col = self.layout.column()
		# display the properties
		box1 = col.box()
		row = box1.row()
		row.prop(bakeOpts, "nodeNameTag2")
		row.prop(bakeOpts, "nodeNameValue")
		box1.operator("object.wplscene_updnodeval", text="Set value on nodes")
		opRP_f = box1.operator("object.wplscene_prep2render", text="--> RENDER FINAL")
		opRP_f.opt_renderPercentage = 100
		opRP_f.opt_mainSamples = 50 # ok for single sun, outdoors
		opRP_f.opt_syslSamples = 5
		opRP_f.opt_finalMode = True
		opRP_t = box1.operator("object.wplscene_prep2render", text="--> RENDER TEST")
		opRP_t.opt_renderPercentage = 50
		opRP_t.opt_mainSamples = 5
		opRP_t.opt_syslSamples = 1
		opRP_t.opt_finalMode = False

		col.separator()
		col.operator("object.wplscene_framebind")

		col.separator()
		box2 = col.box()
		box2.operator("object.wplscene_trafa", text="Trafaref: ON").opt_opacity = 100
		box2.operator("object.wplscene_trafa", text="Trafaref: 70%").opt_opacity = 70
		box2.operator("object.wplscene_trafa", text="Trafaref: 50%").opt_opacity = 50
		box2.operator("object.wplscene_trafa", text="Trafaref: 20%").opt_opacity = 20
		box2.operator("object.wplscene_trafa", text="Trafaref: OFF").opt_opacity = 0
		box2.separator()
		for im in bpy.data.images:
			if isTokenInStr(kWPLTrafarefToken, im.name):
				box2.operator("object.wplscene_trafa", text=im.name).opt_imge = im.name



def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wplScene2OslSettings = PointerProperty(type=WPLScene2OslSettings)

def unregister():
	del bpy.types.Scene.wplScene2OslSettings
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
