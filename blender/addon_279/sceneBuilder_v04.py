import math
import copy
import random
import mathutils

from datetime import datetime
from random import random, seed

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from datetime import datetime
from bpy.app import handlers

bl_info = {
	"name": "Scene Builder",
	"author": "IPv6",
	"version": (1, 1, 17),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: "WPL"
	}

kWPLSystemSun = "zzz_MainSun"
kWPLEdgesMainCam = "zzz_MainCamera"
kWPLSystemRL1Flag = "zzz_RenderLayer1"
#kWPLSystemMainVolObj = "zzz_MainVolume_env"
#kWPLEdgeColVC = "DecorC"

kWPLOslQueryPrefix = "sys_sceneQuery_"
kWPLOslQueryPostfx = "_v04.osl"
kWPLOslQueryMaxObjs = 500
kWPLSystemEmpty = "zzz_Support"
kWPLSystemReestrObjs = "Reestr"
kWPLMatTokenDedup = '.'
kWPLMatTokenWPV = '_v'

kWPLObjF3Props2Base = "DecorC,Wri,TexScale,TexSize,TexShift,TexU,TexV,DispFur,EnvOpt"
kWPLSystemLayerObj = "sys,bevel,+rlonly"
kWPLSystemLayer = 19
kWPLDetailLayerObj = "lip,eyebrow,eyelash,detail,edge,wri"
kWPLEdgeLayer = 9
kWPLEdgeAutoScale = {"_charb": 0.5, "_head": 0.5}
# TBD: 2.80 porting
# https://blog.michelanders.nl/2018/12/upgrading-blender-add-ons-from-279-to280-part-2.html

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
	if len(subname)>0:
		emptyname = subname
	empty = context.scene.objects.get(emptyname)
	if empty is None:
		empty = bpy.data.objects.new(emptyname, None)
		empty.empty_draw_size = 0.45
		empty.empty_draw_type = 'PLAIN_AXES'
		context.scene.objects.link(empty)
		moveObjectOnLayer(empty,kWPLSystemLayer)
		context.scene.update()
		if len(subname) > 0:
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

def getWPLOslQueryName():
	base_name = bpy.path.basename(bpy.data.filepath)
	if ".blend" in base_name:
		base_name = base_name.split(".blend", 1)[0]
	base_name = bpy.path.clean_name(base_name)
	if kWPLMatTokenWPV in base_name:
		base_name = base_name.split(kWPLMatTokenWPV, 1)[0]
	return kWPLOslQueryPrefix+base_name+kWPLOslQueryPostfx
# def getWPLOslPaletteName():
	# base_name = bpy.path.basename(bpy.data.filepath)
	# if ".blend" in base_name:
		# base_name = base_name.split(".blend", 1)[0]
	# base_name = bpy.path.clean_name(base_name)
	# if kWPLMatTokenWPV in base_name:
		# base_name = base_name.split(kWPLMatTokenWPV, 1)[0]
	# return kWPLOslpalettePrefix+base_name+kWPLOslpalettePostfx


def getAllMatNodes():
	all_nodes = []
	node_groups = bpy.data.node_groups
	for group in node_groups:
		for node in group.nodes:
			all_nodes.append(node)
	mats = list(bpy.data.materials)
	worlds = list(bpy.data.worlds)
	for mat in mats + worlds:
		if mat.use_nodes:
			for node in mat.node_tree.nodes:
				all_nodes.append(node)
	return all_nodes
######################### ######################### #########################
######################### ######################### #########################
class wplscene_bakequery2osl( bpy.types.Operator ):
	bl_idname = "object.wplscene_bakequery2osl"
	bl_label = "Bake scene into OSL script"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		bakeOpts = context.scene.wplScene2OslSettings
		if len(bakeOpts.nameSubstr2skip)>0:
			skipNameParts = [x.strip().lower() for x in bakeOpts.nameSubstr2skip.split(",")]
		else:
			skipNameParts = []
		if len(bakeOpts.nameCustProps)>0:
			custprpNameParts = [x.strip() for x in bakeOpts.nameCustProps.split(",")]
		else:
			custprpNameParts = []
		custprpNamePartsMap = {}
		for custprp in custprpNameParts:
			custprp_safe = custprp.replace("(","_")
			custprp_safe = custprp_safe.replace(")","_")
			custprpNamePartsMap[custprp] = custprp_safe
		objs2dump = []
		for i,obj in enumerate(bpy.data.objects):
			obj.pass_index = i+kWPLOslQueryMaxObjs
			isOk = True
			for snp in skipNameParts:
				if obj.name.lower().find(snp) >= 0:
					isOk = False
					break
			if isOk:
				objs2dump.append(obj)
		def sortkey4obj(obj):
			objtype = "z"
			objsubtype = "z"
			if obj.name == kWPLSystemSun or obj.name == kWPLEdgesMainCam:
				objtype = "a"
			if obj.type == 'CURVE':
				objtype = "b"
			if obj.type == 'ARMATURE':
				objtype = "c"
			rootp = obj
			while (rootp.parent is not None):
				rootp = rootp.parent
				if rootp.type == 'CURVE':
					objsubtype = "b"
				if rootp.type == 'ARMATURE':
					objsubtype = "c"
			return objtype+objsubtype+rootp.name+obj.name
		objs2dump = sorted(objs2dump, key=lambda k: sortkey4obj(k))
		if len(objs2dump)>kWPLOslQueryMaxObjs:
			# too many objects
			self.report({'INFO'}, "OSL-Bake: Too many objects ("+str(len(objs2dump))+"). Trimming to first "+str(kWPLOslQueryMaxObjs))
			objs2dump = objs2dump[:kWPLOslQueryMaxObjs]
		#print("objs2dump",objs2dump)

		bounds_cache = {}
		def getBoundsRecursive(obj):
			if obj.name in bounds_cache:
				return bounds_cache[obj.name]
			bbc = [] #[obj.matrix_world.to_translation()]
			if obj.type == 'MESH' or obj.type == 'CURVE':
				bbc.extend([obj.matrix_world * Vector(corner) for corner in obj.bound_box])
			if len(obj.children)>0:
				for chi in obj.children:
					bbc.extend(getBoundsRecursive(chi))
			if len(bbc) == 0:
				bbc.append(obj.matrix_world.to_translation())
			bounds_cache[obj.name] = bbc
			return bbc
		objsData = []
		objsI2oMap = {}
		objsLastIndex = 0
		for i,obj in enumerate(objs2dump):
			# in advance for proper parenting
			objsLastIndex = i+1
			obj.pass_index = objsLastIndex
			objsI2oMap[obj.pass_index] = obj
		for i,obj in enumerate(objs2dump):
			item = {}
			g_loc = obj.matrix_world.to_translation() # * obj.location
			mx_inv = obj.matrix_world.inverted()
			mx_norm = mx_inv.transposed().to_3x3()
			g_locx = (mx_norm * Vector((1,0,0))).normalized()
			g_locy = (mx_norm * Vector((0,1,0))).normalized()
			g_locz = (mx_norm * Vector((0,0,1))).normalized()
			bbc = getBoundsRecursive(obj)
			item["name"] = "\""+obj.name+"\""
			#item["index"] = repr(obj.pass_index)
			item["parentI"] = repr(obj.pass_index) #self! for easier chaining
			item["rootI"] = repr(obj.pass_index) #self! for easier chaining
			rootp = obj.parent
			if (rootp is not None) and (rootp in objs2dump):
				rootI = rootp.pass_index
				item["parentI"] = repr(rootI)
				item["rootI"] = repr(rootI)
				rootp = rootp.parent
				while (rootp is not None) and (rootp in objs2dump):
					rootI = rootp.pass_index
					item["rootI"] = repr(rootI)
					rootp = rootp.parent
			item["location"] = "point("+repr(g_loc[0])+","+repr(g_loc[1])+","+repr(g_loc[2])+")"
			item["normx"] = "point("+repr(g_locx[0])+","+repr(g_locx[1])+","+repr(g_locx[2])+")"
			item["normy"] = "point("+repr(g_locy[0])+","+repr(g_locy[1])+","+repr(g_locy[2])+")"
			item["normz"] = "point("+repr(g_locz[0])+","+repr(g_locz[1])+","+repr(g_locz[2])+")"
			item["scale"] = "point("+repr(obj.scale[0])+","+repr(obj.scale[1])+","+repr(obj.scale[2])+")"
			item["dims"] = "point("+repr(obj.dimensions[0])+","+repr(obj.dimensions[1])+","+repr(obj.dimensions[2])+")"
			item["bbmin"] = "point("+repr(min(item[0] for item in bbc))+","+repr(min(item[1] for item in bbc))+","+repr(min(item[2] for item in bbc))+")"
			item["bbmax"] = "point("+repr(max(item[0] for item in bbc))+","+repr(max(item[1] for item in bbc))+","+repr(max(item[2] for item in bbc))+")"
			item["iscurve"] = repr(0.0)
			if obj.type == 'CURVE':
				item["iscurve"] = repr(1.0)
			item["isarray"] = repr(0.0)
			for md in obj.modifiers:
				if md.type == 'ARRAY':
					item["isarray"] = repr(1.0)
			item["isdupli"] = repr(0.0)
			if obj.parent is not None and obj.parent.dupli_type != 'NONE':
				item["isdupli"] = repr(1.0)
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
			objsData.append(item)

		textblock = bpy.data.texts.get(getWPLOslQueryName())
		if not textblock:
			textblock = bpy.data.texts.new(getWPLOslQueryName())
		else:
			textblock.clear()
		osl_content = []
		osl_content.append("// WARNING: text below is autogenerated, DO NOT EDIT.")
		osl_content.append("// TIMESTAMP: "+str(datetime.now()))
		osl_content.append("// FILE: "+bpy.data.filepath)
		osl_content.append("#define DUMPLEN "+str(objsLastIndex))
		#osl_content.append("#define ZEROP point(0,0,0)")
		osl_content.append("shader sceneQuery (")
		osl_content.append(" float maxDistance = 0,")
		osl_content.append(" int by_index = 0,")
		osl_content.append(" string by_name_equality = \"\",")
		osl_content.append(" string by_near_startswith = \"\",")
		osl_content.append(" string name_objColor = \"\",")
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
		osl_content.append(" output string objName = \"\",")
		osl_content.append(" output float objIsCurve = 0.0,")
		osl_content.append(" output float objIsArray = 0.0,")
		osl_content.append(" output float objIsDupli = 0.0,")
		osl_content.append("){")
		#osl_content.append(" int sIndex[DUMPLEN] = {"+",".join([ item['index'] for item in objsData ])+"};")
		osl_content.append(" int pIndex[DUMPLEN] = {"+",".join([ item['parentI'] for item in objsData ])+"};")
		osl_content.append(" int rIndex[DUMPLEN] = {"+",".join([ item['rootI'] for item in objsData ])+"};")
		osl_content.append(" string sNames[DUMPLEN] = {"+",".join([ item['name'] for item in objsData ])+"};")
		osl_content.append(" point sLocas[DUMPLEN] = {"+",".join([ item['location'] for item in objsData ])+"};")
		osl_content.append(" point sScales[DUMPLEN] = {"+",".join([ item['scale'] for item in objsData ])+"};")
		osl_content.append(" point sNormalX[DUMPLEN] = {"+",".join([ item['normx'] for item in objsData ])+"};")
		osl_content.append(" point sNormalY[DUMPLEN] = {"+",".join([ item['normy'] for item in objsData ])+"};")
		osl_content.append(" point sNormalZ[DUMPLEN] = {"+",".join([ item['normz'] for item in objsData ])+"};")
		osl_content.append(" point sDimens[DUMPLEN] = {"+",".join([ item['dims'] for item in objsData ])+"};")
		osl_content.append(" point sBbmax[DUMPLEN] = {"+",".join([ item['bbmax'] for item in objsData ])+"};")
		osl_content.append(" point sBbmin[DUMPLEN] = {"+",".join([ item['bbmin'] for item in objsData ])+"};")
		osl_content.append(" point sColor[DUMPLEN] = {"+",".join([ item['color'] for item in objsData ])+"};")
		osl_content.append(" float isCurve[DUMPLEN] = {"+",".join([ item['iscurve'] for item in objsData ])+"};")
		osl_content.append(" float isArray[DUMPLEN] = {"+",".join([ item['isarray'] for item in objsData ])+"};")
		osl_content.append(" float isDupli[DUMPLEN] = {"+",".join([ item['isdupli'] for item in objsData ])+"};")
		for custprp in custprpNameParts:
			custprp_safe = custprpNamePartsMap[custprp]
			osl_content.append(" point cp"+custprp_safe+"[DUMPLEN] = {"+",".join([ item[custprp] for item in objsData ])+"};")
		osl_content.append(" int iFoundIndex = -1;")
		osl_content.append(" if(by_index > 0){")
		osl_content.append("  iFoundIndex = by_index-1;")
		osl_content.append(" }")
		osl_content.append(" if(strlen(by_name_equality)>0){")
		osl_content.append("  for(int i=0;i<DUMPLEN;i++){")
		osl_content.append("   if(sNames[i] == by_name_equality){")
		osl_content.append("    if(maxDistance>0 && length(P-sLocas[i])>maxDistance){")
		osl_content.append("     continue;")
		osl_content.append("    }")
		osl_content.append("    iFoundIndex = i;")
		osl_content.append("    break;")
		osl_content.append("   }")
		osl_content.append("  }")
		osl_content.append(" }")
		osl_content.append(" if(strlen(by_near_startswith)>0){")
		osl_content.append("  iFoundIndex = -1;")
		osl_content.append("  float iNearesDist = 99999.0;")
		osl_content.append("  for(int i=0;i<DUMPLEN;i++){")
		osl_content.append("   if(startswith(sNames[i],by_near_startswith)>0){")
		osl_content.append("    float dist = length(P-sLocas[i]);")
		osl_content.append("    if(maxDistance>0 && length(P-sLocas[i])>maxDistance){")
		osl_content.append("     continue;")
		osl_content.append("    }")
		osl_content.append("    if(dist<iNearesDist){")
		osl_content.append("     iNearesDist = dist;")
		osl_content.append("     iFoundIndex = i;")
		osl_content.append("    }")
		osl_content.append("   }")
		osl_content.append("  }")
		osl_content.append(" }")
		osl_content.append(" if(iFoundIndex >= 0 && iFoundIndex < DUMPLEN){")
		#osl_content.append("  index = sIndex[iFoundIndex];")
		osl_content.append("  index = iFoundIndex+1;")
		osl_content.append("  parent_index = pIndex[iFoundIndex];")
		osl_content.append("  root_index = rIndex[iFoundIndex];")
		osl_content.append("  g_Location = sLocas[iFoundIndex];")
		osl_content.append("  g_normalX = sNormalX[iFoundIndex];")
		osl_content.append("  g_normalY = sNormalY[iFoundIndex];")
		osl_content.append("  g_normalZ = sNormalZ[iFoundIndex];")
		osl_content.append("  g_boundsMax = sBbmax[iFoundIndex];")
		osl_content.append("  g_boundsMin = sBbmin[iFoundIndex];")
		osl_content.append("  scale = sScales[iFoundIndex];")
		osl_content.append("  dimensions = sDimens[iFoundIndex];")
		osl_content.append("  objName = sNames[iFoundIndex];")
		osl_content.append("  objIsCurve = isCurve[iFoundIndex];")
		osl_content.append("  objIsArray = isArray[iFoundIndex];")
		osl_content.append("  objIsDupli = isDupli[iFoundIndex];")
		osl_content.append("  if(strlen(name_objColor)==0){objColor = sColor[iFoundIndex];}else{")
		for custprp in custprpNameParts:
			custprp_safe = custprpNamePartsMap[custprp]
			osl_content.append("   if(name_objColor==\""+custprp+"\"){objColor = cp"+custprp_safe+"[iFoundIndex];};")
		osl_content.append("  }")
		osl_content.append(" }")
		osl_content.append("}")
		textblock.write("\n".join(osl_content))

		self.report({'INFO'}, "Scene query baked, objects="+str(objsLastIndex))
		return {'FINISHED'}

class wplscene_updnodeval( bpy.types.Operator ):
	bl_idname = "object.wplscene_updnodeval"
	bl_label = "Set value into nodes"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		def checkNode(node):
			if len(node.outputs)>0:
				#print("- Node: '%s' -> '%s'" % (node.bl_label, node.outputs[0]))
				if '#' in node.label:
					print("- Node '%s' = '%s'" % (node.label, node.outputs[0].default_value))
				if nodeNameTag in node.label:
					node.outputs[0].default_value = float(nodeNameValue)
					print("- Switching: '%s' -> '%s'" % (node.label, node.outputs[0].default_value))
					return 1
			return 0
		itogo_ok = 0
		bakeOpts = context.scene.wplScene2OslSettings
		nodeNameTag = bakeOpts.nodeNameTag
		nodeNameValue = bakeOpts.nodeNameValue
		all_nodes = getAllMatNodes()
		for node in all_nodes:
			itogo_ok = itogo_ok+checkNode(node)
		self.report({'INFO'}, "Nodes updated: "+str(itogo_ok))
		return {'FINISHED'}

class wplscene_dedupmats( bpy.types.Operator ):
	bl_idname = "object.wplscene_dedupmats"
	bl_label = "Replace Material-dupes with originals"
	bl_options = {'REGISTER', 'UNDO'}

	opt_skipIfParts = StringProperty(
			name = "Objects to skip",
			default = kWPLSystemReestrObjs
	)

	opt_upgrMats = BoolProperty(
		name="Upgrade '_v' mats",
		default=True
	)

	opt_upgrToLinked = BoolProperty(
		name="Prefer linked groups/mats/scripts",
		default=True
	)

	@classmethod
	def poll( cls, context ):
		return True

	def getLibraryAnalogMat(self,mewmat,matsAll):
		if mewmat is None:
			return None
		if mewmat.library is None:
			for ngt in matsAll:
				if ngt.library is not None and ngt.name == mewmat.name:
					mewmat = ngt
		return mewmat

	def getMatByName(self,mat_name,matsAll):
		mewmat = matsAll.get(mat_name)
		return mewmat

	def isObjUpdatable(self,obj,skipNameParts):
		canContinue = True
		for snp in skipNameParts:
			if obj.name.lower().find(snp) >= 0:
				canContinue = False
				break
		return canContinue

	def execute( self, context ):
		mats = bpy.data.materials
		itogo_ok = 0
		itogo_skip = 0
		if len(self.opt_skipIfParts)>0:
			skipNameParts = [x.strip().lower() for x in self.opt_skipIfParts.split(",")]
		else:
			skipNameParts = []
		for obj in bpy.data.objects:
			if not self.isObjUpdatable(obj,skipNameParts):
				continue
			for slt in obj.material_slots:
				part = slt.name.rpartition(kWPLMatTokenDedup)
				if part[2].isnumeric() and part[0] in mats:
					print("- %s: '%s' -> '%s'" % (obj.name, slt.name, part[0]))
					slt.material = self.getMatByName(part[0],mats)
					itogo_ok = itogo_ok+1
				elif len(part[0])>0 and len(part[2])>0:
					itogo_skip = itogo_skip+1
					print("- %s: Skipping '%s'" % (obj.name, slt.name))
		# upgrading AFTER deduping
		if self.opt_upgrMats:
			# checking mat_override in render layers
			for lr in bpy.context.scene.render.layers:
				if lr.material_override is not None:
					slt_old_name = lr.material_override.name
					part = slt_old_name.rpartition(kWPLMatTokenWPV)
					if part[2].isnumeric():
						ver = int(part[2])
						for upgStep in reversed(range(1,100)):
							nextMatName = part[0]+part[1]+str(ver+upgStep).rjust(2, '0')
							if nextMatName in mats:
								print("- %s: '%s' -> '%s'" % ("material_override", slt_old_name, nextMatName))
								lr.material_override = self.getMatByName(nextMatName,mats)
								itogo_ok = itogo_ok+1
								break
					if self.opt_upgrToLinked == True:
						lr.material_override = self.getLibraryAnalogMat(lr.material_override,mats)
			for obj in bpy.data.objects:
				if not self.isObjUpdatable(obj,skipNameParts):
					continue
				for slt in obj.material_slots:
					slt_old_name = slt.name
					part = slt_old_name.rpartition(kWPLMatTokenWPV)
					if part[2].isnumeric():
						ver = int(part[2])
						for upgStep in reversed(range(1,100)):
							nextMatName = part[0]+part[1]+str(ver+upgStep).rjust(2, '0')
							if nextMatName in mats:
								print("- %s: '%s' -> '%s'" % (obj.name, slt_old_name, nextMatName))
								slt.material = self.getMatByName(nextMatName,mats)
								itogo_ok = itogo_ok+1
								break
					elif len(part[0])>0 and len(part[2])>0:
						itogo_skip = itogo_skip+1
						print("- %s: Skipping '%s'" % (obj.name, slt.name))
		if self.opt_upgrToLinked == True:
			for obj in bpy.data.objects:
				if not self.isObjUpdatable(obj,skipNameParts):
					continue
				for slt in obj.material_slots:
					slt.material = self.getLibraryAnalogMat(slt.material,mats)
		self.report({'INFO'}, "Materials updated: "+str(itogo_ok)+", skipped: "+str(itogo_skip))
		return {'FINISHED'}

class wplscene_dedupnods( bpy.types.Operator ):
	bl_idname = "object.wplscene_dedupnods"
	bl_label = "Replace NodeGroup-dupes with originals"
	bl_options = {'REGISTER', 'UNDO'}

	opt_upgrToLinked = BoolProperty(
		name="Prefer linked groups/mats/scripts",
		default=True
	)
	opt_upgrNodeGroups = BoolProperty(
		name="Upgrade '_v' groups",
		default=True
	)
	opt_upgrNodeScripts = BoolProperty(
		name="Upgrade '_v' scripts",
		default=False
	)

	@classmethod
	def poll( cls, context ):
		return True

	def dump(self,obj):
		for attr in dir(obj):
			if hasattr( obj, attr ):
				print( "obj.%s = %s" % (attr, getattr(obj, attr)))

	def getHigherVerName(self, node_name, nodeAll):
		part = node_name.rpartition(kWPLMatTokenWPV)
		if part[2].isnumeric():
			ver = int(part[2])
			for upgStep in reversed(range(1,100)):
				nextMat = part[0]+part[1]+str(ver+upgStep).rjust(2, '0')
				if nextMat in nodeAll:
					return nextMat
		return None

	def getLibraryAnalog(self,node_name,nodeAll):
		for ngt in nodeAll:
			if ngt.library is not None and ngt.name == node_name:
				return ngt
		return None

	def dedupeScript(self, node, parentName):
		#print("Checking ",node.name,node.script)
		script_texts = bpy.data.texts
		oldscript = node.script
		if oldscript is not None:
			(base, sep, ext) = oldscript.name.rpartition(kWPLMatTokenDedup)
			# Replace the numeric duplicate
			if ext.isnumeric():
				if base in script_texts:
					print("- '%s': Replace script '%s' with '%s'" % (parentName, oldscript.name, base))
					node.script = script_texts.get(base)
					node.update()
				else:
					print("- '%s': Rename script '%s' to '%s'" % (parentName, oldscript.name, base))
					oldscript.name = base
				return True
		return False

	def upgradeScript(self, node, doRealUpgrade, checkLibAtls, parentName):
		script_texts = bpy.data.texts
		if checkLibAtls and node.script.library is None:
			ngt = self.getLibraryAnalog(node.script.name, script_texts)
			if ngt is not None:
				print("- '%s': Warning: library analog found: '%s' -> '%s'" % (parentName, node.script.name, ngt.name))
				node.script = ngt
				print("-- Upgraded to library analog")
		upgrName = self.getHigherVerName(node.script.name, script_texts)
		if upgrName is not None:
			print("- '%s': Warning: upgradable script item '%s' -> '%s'" % (parentName, node.script.name, upgrName))
			if doRealUpgrade:
				node.script = script_texts.get(upgrName)
				print("-- Upgraded to '%s'" % (upgrName))
			return True
		return False

	def dedupeNodeGroup(self, node, parentName):
		#print("Checking ",node.name,node.node_tree.name)
		node_groups = bpy.data.node_groups
		nn_tree = node.node_tree
		(base, sep, ext) = nn_tree.name.rpartition(kWPLMatTokenDedup)
		if ext.isnumeric():
			if base in node_groups:
				print("- '%s': Replace nodegroup '%s' with '%s'" % (parentName, nn_tree.name, base))
				node.node_tree.use_fake_user = False
				node.node_tree = node_groups.get(base)
			else:
				print("- '%s': Rename nodegroup '%s' to '%s'" % (parentName, nn_tree.name, base))
				node.node_tree.name = base
			return True
		return False

	def upgradeNodeGroup(self, node, doRealUpgrade, checkLibAtls, parentName):
		# 00-padding must be present
		# ..._v01 -> ..._v02 - ok. ..._v1 -> ..._v2 - wrong!
		node_groups = bpy.data.node_groups
		if checkLibAtls and node.node_tree.library is None:
			ngt = self.getLibraryAnalog(node.node_tree.name, node_groups)
			if ngt is not None:
				print("- '%s': Warning: library analog found: '%s' -> '%s'" % (parentName, node.node_tree.name, ngt.name))
				node.node_tree = ngt
				print("-- Upgraded to library analog")
		upgrName = self.getHigherVerName(node.node_tree.name,node_groups)
		if upgrName is not None:
			print("- '%s': Warning: upgradable item '%s' -> '%s'" % (parentName, node.node_tree.name, upgrName))
			if doRealUpgrade:
				node.node_tree = node_groups.get(upgrName)
				print("-- Upgraded to '%s'" % (upgrName))
			return True
		return False


	def execute( self, context ):
		itogos = {}
		itogos["cln"] = 0
		itogos["upg"] = 0
		itogos["prb"] = 0
		def checkNode(node, refname):
			if node.bl_idname == 'ShaderNodeScript':
				if node.script is None:
					print("- Warning: Broken node, no script in %s" % (refname))
					itogos["prb"] = itogos["prb"]+1
					return
				if self.dedupeScript(node,refname):
					itogos["cln"] = itogos["cln"]+1
				if self.upgradeScript(node,self.opt_upgrNodeScripts,self.opt_upgrToLinked,refname):
					itogos["upg"] = itogos["upg"]+1
			elif node.bl_idname == 'ShaderNodeGroup' or node.bl_idname == 'CompositorNodeGroup': #node.type == 'GROUP'
				if node.node_tree is None or len(node.node_tree.nodes) == 0:
					print("- Warning: Broken node, no nodetree in", node.name, " mat:", refname)
					itogos["prb"] = itogos["prb"]+1
					return
				if self.dedupeNodeGroup(node,refname):
					itogos["cln"] = itogos["cln"]+1
				if self.upgradeNodeGroup(node,self.opt_upgrNodeGroups,self.opt_upgrToLinked,refname):
					itogos["upg"] = itogos["upg"]+1
				if len(node.node_tree.nodes) < 2:
					# badly linked node, at least input/output should be present!
					print("- Warning: Broken node, no subnodes in", node.node_tree.name, " mat:", refname)
					itogos["prb"] = itogos["prb"]+1
		#--- Search for duplicates in actual node groups - same as getAllMatNodes
		node_groups = bpy.data.node_groups
		for group in node_groups:
			if len(group.nodes) < 2:
				# badly linked node, at least input/output should be present!
				print("- Warning: Broken node, no subnodes in", group.name, ", users:", group.users, group.use_fake_user)
				itogos["prb"] = itogos["prb"]+1
				continue
			for node in group.nodes:
				checkNode(node, group.name)
		#--- Search for duplicates in materials
		mats = list(bpy.data.materials)
		worlds = list(bpy.data.worlds)
		for mat in mats + worlds:
			if mat.use_nodes:
				for node in mat.node_tree.nodes:
					checkNode(node, mat.name)
		#--- composnodes
		compostree = bpy.context.scene.node_tree
		for node in compostree.nodes:
			checkNode(node, "compositor")
		# Scripts text cleanup
		allTexts = bpy.data.texts.keys()
		for scriptname in allTexts:
			script_block = bpy.data.texts.get(scriptname)
			(base, sep, ext) = scriptname.rpartition(kWPLMatTokenDedup)
			if ext.isnumeric():
				if base in bpy.data.texts:
					print("- Text cleanup: Removing", scriptname, " - base script found")
					bpy.data.texts.remove(script_block)
					script_block = None
					itogos["cln"] = itogos["cln"]+1
			if self.opt_upgrToLinked and script_block is not None and script_block.library is None:
				ngt = self.getLibraryAnalog(scriptname, bpy.data.texts)
				if ngt is not None:
					print("- Text cleanup: Removing", scriptname, " - libanalog found")
					bpy.data.texts.remove(script_block)
					script_block = None
					itogos["cln"] = itogos["cln"]+1
		self.report({'INFO'}, "NodeGroups deduped, dupes: "+str(itogos["cln"])+", upgr: "+str(itogos["upg"])+", problems: "+str(itogos["prb"]))
		return {'FINISHED'}

class wplscene_swtstate( bpy.types.Operator ):
	bl_idname = "object.wplscene_swtstate"
	bl_label = "Switch scene state"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		return True

	def updateObjShapekeys( self, context, obj ):
		try:
			if (obj.data is None) or (obj.data.shape_keys is None) or (obj.data.shape_keys.key_blocks is None):
				return
		except:
			return
		bakeOpts = context.scene.wplScene2OslSettings
		keys = obj.data.shape_keys.key_blocks.keys()
		active_idx = 0
		for kk in keys:
			if kk.find(bakeOpts.scnStateCommon) >= 0:
				if kk.find(bakeOpts.scnStateId) >= 0:
					shape_key = obj.data.shape_keys.key_blocks[kk]
					obj.active_shape_key_index = keys.index(kk)
					active_idx = obj.active_shape_key_index
					shape_key.value = 1
				else:
					shape_key = obj.data.shape_keys.key_blocks[kk]
					obj.active_shape_key_index = keys.index(kk)
					shape_key.value = 0
		obj.active_shape_key_index = active_idx
		if obj.type == 'MESH':
			obj.data.update()

	def updateObjPose( self, context, obj ):
		# https://blenderartists.org/forum/showthread.php?254069-Activate-A-Pose-Library-Entry-via-Python-Code
		def isKeyOnFrame(passedFcurve, passedFrame):
			result = False
			for k in passedFcurve.keyframe_points:
				if int(k.co.x) == int(passedFrame):
					result = True
					break
			return result
		try:
			if (obj.pose is None) or (obj.pose_library is None) or (obj.pose_library.pose_markers is None):
				return
		except:
			return
		bakeOpts = context.scene.wplScene2OslSettings
		pl = obj.pose_library
		p = obj.pose
		keys = obj.pose_library.pose_markers.keys()
		for kk in keys:
			if kk.find(bakeOpts.scnStateCommon) >= 0:
				if kk.find(bakeOpts.scnStateId) >= 0:
					pm = pl.pose_markers[kk]
					frame = pm.frame
					action = bpy.data.actions[pl.name]
					for agrp in action.groups:
						# check if group has any keyframes.
						for fc in agrp.channels:
							r = isKeyOnFrame(fc,frame)
							if r == True:
								tmpValue = fc.evaluate(frame)
								i = p.bones.find(agrp.name)
								if i != -1:
									pb = p.bones[i]
									if fc.data_path.find("location") != -1:
										pb.location[fc.array_index] = tmpValue
									if fc.data_path.find("rotation_quaternion") != -1:
										pb.rotation_quaternion[fc.array_index] = tmpValue
									if fc.data_path.find("rotation_euler") != -1:
										pb.rotation_euler[fc.array_index] = tmpValue
									if fc.data_path.find("scale") != -1:
										pb.scale[fc.array_index] = tmpValue

	def execute( self, context ):
		bakeOpts = context.scene.wplScene2OslSettings
		if len(bakeOpts.scnStateCommon) < 1:
			self.report({'ERROR'}, "Invalid common name")
			return {'CANCELLED'}

		objs2check = [obj for obj in bpy.data.objects]
		for obj in objs2check:
			if obj.name.find(bakeOpts.scnStateCommon) >= 0:
				if obj.name.find(bakeOpts.scnStateId) >= 0:
					hideObjectWithChilds(obj,False)
				else:
					hideObjectWithChilds(obj,True)
		for obj in objs2check:
			self.updateObjPose(context, obj)
			self.updateObjShapekeys(context, obj)

		self.report({'INFO'}, "Scene state switched")
		return {'FINISHED'}

class wplscene_findnodeuse( bpy.types.Operator ):
	bl_idname = "object.wplscene_findnodeuse"
	bl_label = "Test nodes"
	bl_options = {'REGISTER', 'UNDO'}
	nameSubstrs = bpy.props.StringProperty(
		name		= "String tokens to search...",
		default	 = "???,???"
		)
	makeAllLocal = bpy.props.BoolProperty(
		name		= "Make all local",
		default	 = False
		)

	@classmethod
	def poll( cls, context ):
		return True

	def testNode( self, nd, src_info, testNames, debug_logs):
		if self.makeAllLocal:
			#if nd.bl_idname == 'ShaderNodeScript' and nd.library:
			#	nd.make_local()
			if nd.bl_idname == 'ShaderNodeGroup' and nd.node_tree.library:
				nd.node_tree.make_local()

		if nd.bl_idname == 'ShaderNodeScript' and nd.script is None:
			log_str = "- !!! found broken node "+nd.name+" in "+src_info
			debug_logs.append(log_str)
			print(log_str)
			return
		if nd.bl_idname == 'ShaderNodeGroup' and (nd.node_tree is None or len(nd.node_tree.nodes) == 0):
			log_str = "- !!! found broken node "+nd.name+" in "+src_info
			debug_logs.append(log_str)
			print(log_str)
			return
		isAnyTestPresent = False
		for tn in testNames:
			if tn in nd.name:
				isAnyTestPresent = True
			if nd.bl_idname == 'ShaderNodeScript' and tn in nd.script.name.lower():
				isAnyTestPresent = True
			if nd.bl_idname == 'ShaderNodeGroup' and tn in nd.node_tree.name.lower():
				isAnyTestPresent = True
		if isAnyTestPresent == False:
			return
		log_str = "- testing node "+nd.name+" in "+src_info
		debug_logs.append(log_str)
		print(log_str)
		for outp in nd.inputs:
			if outp.is_linked:
				for tn in testNames:
					if tn in outp.name.lower():
						log_str = "- found linked input "+outp.name
						debug_logs.append(log_str)
						print(log_str)
		for outp in nd.outputs:
			if outp.is_linked:
				for tn in testNames:
					if tn in outp.name.lower():
						log_str = "- found linked output "+outp.name
						debug_logs.append(log_str)
						print(log_str)
		return

	def execute( self, context ):
		stringTokens = []
		if len(self.nameSubstrs)>0:
			stringTokens = [x.strip().lower() for x in self.nameSubstrs.split(",")]
		print("Test tokens:",stringTokens)
		debug_logs = []
		node_groups = bpy.data.node_groups
		mats = list(bpy.data.materials)
		worlds = list(bpy.data.worlds)
		if self.makeAllLocal:
			for mat in mats + worlds:
				if mat.use_nodes and mat.library is not None:
					mat.make_local()
		for group in node_groups:
			if len(group.nodes) == 0:
				log_str = "- !!! found broken nodegroup "+group.name
				debug_logs.append(log_str)
				print(log_str)
			for node in group.nodes:
				self.testNode(node,"Grp:"+group.name,stringTokens,debug_logs)
		for mat in mats + worlds:
			if mat.use_nodes:
				for node in mat.node_tree.nodes:
					self.testNode(node,"Mat:"+mat.name,stringTokens,debug_logs)
		self.report({'INFO'}, "Nodes tested, warns="+str(len(debug_logs)))
		return {'FINISHED'}

def frh_start_timer(scene):
	WPL_G.store["frh_TIMER"] = datetime.now()
def frh_elapsed(dummy):
	print("\nStats: Elapsed:", datetime.now() - WPL_G.store["frh_TIMER"])
class wplscene_prep2render( bpy.types.Operator ):
	bl_idname = "object.wplscene_prep2render"
	bl_label = "Prepare to render"
	bl_options = {'REGISTER', 'UNDO'}

	opt_renderPercentage = IntProperty(
		name		= "Render percentage",
		default	 = 200,
	)
	opt_mainSamples = IntProperty(
		name		= "Main samples",
		default	 = 40,
	)
	opt_syslSamples = IntProperty(
		name		= "Syslayers samples",
		default	 = 5,
	)
	opt_scriptComp = EnumProperty(
		items = [
			('NONE', "None", ""),
			('QUER', "Scene query", ""),
			('ALL', "All scripts", ""),
		],
		name="Osl compilation",
		default='QUER',
	)
	opt_enableAllRL = BoolProperty(
		name		= "With render layers",
		default	 = True,
	)
	opt_rlayer9toks = StringProperty(
		name		= "Layer 9 objects",
		default	 = kWPLDetailLayerObj,
	)
	opt_rlayer19toks = StringProperty(
		name		= "Layer 19 objects",
		default	 = kWPLSystemLayerObj,
	)
	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		def full_chain_name(obj):
			names = []
			names.append(obj.name.lower())
			rootp = obj.parent
			while (rootp is not None):
				names.append(rootp.name.lower())
				rootp = rootp.parent
			return ",".join(names)
		rl1_obj = context.scene.objects.get(kWPLSystemRL1Flag)
		if rl1_obj is None:
			self.report({'ERROR'}, "Sys obj not found: "+kWPLSystemRL1Flag)
			return {'CANCELLED'}
		sun_obj = context.scene.objects.get(kWPLSystemSun)
		if sun_obj is None:
			self.report({'ERROR'}, "Main sun not found: "+kWPLSystemSun)
			return {'CANCELLED'}
		active_obj = context.scene.objects.active
		# need active non-linked object to compile OSL!
		select_and_change_mode(sun_obj, 'OBJECT')
		bakeOpts = context.scene.wplScene2OslSettings
		c_scene = bpy.context.scene
		c_scene.render.engine = 'CYCLES'
		#activate all layers
		for i in range(0,20):
			c_scene.layers[i] = True
		opt_res = {}
		opt_res["okitems"] = 0
		bpy.ops.object.wplscene_bakequery2osl()
		if len(self.opt_rlayer9toks)+len(self.opt_rlayer19toks)>0:
			nametoks9 = []
			if len(self.opt_rlayer9toks)>0:
				nametoks9 = [x.strip().lower() for x in self.opt_rlayer9toks.split(",")]
			nametoks19 = []
			if len(self.opt_rlayer19toks)>0:
				nametoks19 = [x.strip().lower() for x in self.opt_rlayer19toks.split(",")]
			objs2dump = [lobj for lobj in bpy.data.objects]
			for lobj in objs2dump:
				obj_name = lobj.name.lower()
				obj_name_2top = full_chain_name(lobj)
				isHighLayers = False
				for tkn in nametoks19:
					if tkn in obj_name:
						isHighLayers = True
						moveObjectOnLayer(lobj,kWPLSystemLayer)
						break
					if "+" in tkn:
						if tkn[1:] in obj_name_2top:
							isHighLayers = True
							moveObjectOnLayer(lobj,kWPLSystemLayer)
							break
				for tkn in nametoks9:
					if tkn in obj_name:
						isHighLayers = True
						moveObjectOnLayer(lobj,kWPLEdgeLayer)
						break
					if "+" in tkn:
						if tkn[1:] in obj_name_2top:
							isHighLayers = True
							moveObjectOnLayer(lobj,kWPLEdgeLayer)
							break
				if isHighLayers == False:
					moveObjectOnLayer(lobj,0)
		moveObjectOnLayer(rl1_obj,kWPLSystemLayer) # after all other objects
		if self.opt_scriptComp != 'NONE':
			area = context.area
			oldareatype = area.type
			area.type = 'NODE_EDITOR'
			all_nodes = getAllMatNodes()
			for node in all_nodes:
				#if node.label == "="+kWPLSystemMainVolObj:
				#	# point cloud node
				#	volObj = context.scene.objects.get(kWPLSystemMainVolObj)
				#	node.object = volObj
				#	node.vertex_attribute_name = kWPLEdgeColVC
				if node.bl_idname == 'ShaderNodeScript' and node.mode == 'INTERNAL' and node.script is not None:
					isSceneQuery = False
					if kWPLOslQueryPrefix in node.script.name:
						scriptblock = bpy.data.texts.get(getWPLOslQueryName())
						node.script = scriptblock
						isSceneQuery = True
					# if kWPLOslpalettePrefix in node.script.name:
						# scriptblock = bpy.data.texts.get(getWPLOslPaletteName())
						# node.script = scriptblock
						# isSceneQuery = True
					if self.opt_scriptComp == 'ALL' or isSceneQuery:
						print("Compiling",node,node.script)
						node_override = context.copy()
						node_override["node"] = node
						node_override["active_node"] = None
						node_override["selected_nodes"] = None
						node_override["edit_text"] = node.script
						#bpy.types.RenderEngine.update_script_node(node)
						#print("- rebuild script context:", node_override)
						bpy.ops.node.shader_script_update(node_override)
						node.update()
						opt_res["okitems"] = opt_res["okitems"]+1
			area.type = oldareatype
		c_scene.render.resolution_percentage = self.opt_renderPercentage
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
		if len(c_scene.render.layers)>0:
			c_scene.render.layers[0].samples = self.opt_mainSamples
			for i, lr in enumerate(c_scene.render.layers):
				if i == 0:
					lr.cycles.use_denoising = True
				else:
					lr.cycles.use_denoising = False
				lr.use_pass_z = False
				lr.use_pass_diffuse_color = True
				lr.use_pass_combined = True
				lr.use_pass_glossy_color = True
				lr.use_pass_transmission_color = True
				lr.use_pass_subsurface_color = True
				lr.use_pass_emit = True
				lr.use_pass_shadow = False
				lr.use_pass_ambient_occlusion = False
				if i>0:
					lr.samples = self.opt_syslSamples
				if self.opt_enableAllRL:
					lr.use = True
				for rli in range(0,20):
					lr.layers[rli] = True
					lr.layers_exclude[rli] = False
					if i > 0 and rli > kWPLEdgeLayer:
						lr.layers_exclude[rli] = True
		if self.opt_enableAllRL:
			c_scene.render.use_border = False
		if self.opt_enableAllRL:
			self.report({'INFO'}, "FINAL: "+str(int(c_scene.render.resolution_x*c_scene.render.resolution_percentage/100.0))+":"+str(int(c_scene.render.resolution_y*c_scene.render.resolution_percentage/100.0))+", nodes="+str(opt_res["okitems"]))
			if "frh" not in WPL_G.store:
				WPL_G.store["frh"] = 1
				handlers.render_pre.append(frh_start_timer)
				handlers.render_stats.append(frh_elapsed)
		else:
			self.report({'INFO'}, "TEST prepared, nodes="+str(opt_res["okitems"]))
		if active_obj is not None:
			select_and_change_mode(active_obj, 'OBJECT')
		return {'FINISHED'}


class WPLScene2OslSettings(bpy.types.PropertyGroup):
	nameSubstr2skip = bpy.props.StringProperty(
		name		= "Skip if object name contain...",
		default	 = "sys_,sub_"
		)
	nameCustProps = bpy.props.StringProperty(
		name		= "Object props to bake",
		default	 = kWPLObjF3Props2Base
		)

	scnStateCommon = bpy.props.StringProperty(
		name		= "Prefix of state",
		description = "Objname/Shapekeys common namepart",
		default	 = "##"
		)
	scnStateId = bpy.props.StringProperty(
		name		= "ID of state",
		description = "Objname/Shapekeys state namepart",
		default	 = "0"
		)
	nodeNameTag = bpy.props.StringProperty(
		name		= "Node tag",
		default	 = "#isdebug"
		)
	nodeNameValue = bpy.props.StringProperty(
		name		= "Node value",
		default	 = "1"
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
		row.prop(bakeOpts, "nodeNameTag")
		row.prop(bakeOpts, "nodeNameValue")
		box1.operator("object.wplscene_updnodeval", text="Set value on nodes")
		opRP_f = box1.operator("object.wplscene_prep2render", text="--> RENDER FINAL")
		opRP_f.opt_renderPercentage = 100
		opRP_f.opt_mainSamples = 50 # enough for big resolutions
		opRP_f.opt_syslSamples = 10
		opRP_f.opt_scriptComp = 'QUER' #'ALL'
		opRP_f.opt_enableAllRL = True
		opRP_t = box1.operator("object.wplscene_prep2render", text="--> RENDER TEST")
		opRP_t.opt_renderPercentage = 50
		opRP_t.opt_mainSamples = 5
		opRP_t.opt_syslSamples = 1
		opRP_t.opt_scriptComp = 'QUER'
		opRP_t.opt_enableAllRL = False
		col.separator()
		col.separator()
		box3 = col.box()
		row = box3.row()
		row.prop(bakeOpts, "scnStateCommon")
		row.prop(bakeOpts, "scnStateId")
		box3.operator("object.wplscene_swtstate", text="Switch scene state")
		col.separator()
		col.separator()
		box4 = col.box()
		box4.operator("object.wplscene_dedupnods", text="Dedupe NodeGroups")
		box4.operator("object.wplscene_dedupmats", text="Dedupe Materials")
		box4.operator("object.wplscene_findnodeuse", text="Test nodes")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wplScene2OslSettings = PointerProperty(type=WPLScene2OslSettings)

def unregister():
	del bpy.types.Scene.wplScene2OslSettings
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
