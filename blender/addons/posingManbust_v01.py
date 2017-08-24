# Simplified hnd posing for Manuel Bastioni rigs

import bpy
import bmesh
import math
import mathutils
import copy
from mathutils import Vector
from math import radians
import numpy as np

from random import random, seed
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view

from bpy.props import (StringProperty,
						BoolProperty,
						IntProperty,
						FloatProperty,
						FloatVectorProperty,
						EnumProperty,
						PointerProperty,
						BoolVectorProperty
						)
from bpy.types import (Panel,
						Operator,
						AddonPreferences,
						PropertyGroup,
						)

bl_info = {
	"name": "WPL MB-Posing helpers",
	"author": "IPv6",
	"version": (1, 0),
	"blender": (2, 78, 0),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: ""
	}

MBArmatureBones_v02 = {
	"head" : {
		"def": Vector((0, 0, 0)), "min": Vector((-30, -60, -10)), "max": Vector((30, 60, 10)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_head",1]
	},
	"neck" : {
		"def": Vector((0, 0, 0)), "min": Vector((-50, -50, -25)), "max": Vector((50, 50, 25)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_head",0]
	},
	"spine01" : {
		"def": Vector((0, 0, 0)), "min": Vector((-60, -30, -20)), "max": Vector((60, 30, 20)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_spine",0]
	},
	"spine02" : {
		"def": Vector((0, 0, 0)), "min": Vector((-60, -30, -20)), "max": Vector((60, 30, 20)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_spine",1]
	},
	"spine03" : {
		"def": Vector((0, 0, 0)), "min": Vector((-60, -30, -20)), "max": Vector((60, 30, 20)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_spine",2]
	},
	"pelvis" : {
		"def": Vector((0, 0, 0)), "min": Vector((-20, -20, -20)), "max": Vector((20, 20, 20)),
		"spd": Vector((1, 1, 1)),
		"prop": None
	},
	"thigh_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-60, -50, -30)), "max": Vector((60, 50, 30)),
		"spd": Vector((0.5, 1, 1)),
		"prop": ["mbh_legs_L",0]
	},
	"calf_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-100, 0, 0)), "max": Vector((2, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_legs_L",1]
	},
	"foot_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-70, -20, 0)), "max": Vector((50, 20, 0)),
		"spd": Vector((1, 1, 0)),
		"prop": ["mbh_legs_L",2]
	},
	"toes_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-70, 0, 0)), "max": Vector((90, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_legs_L",3]
	},

	"clavicle_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-20, -30, -30)), "max": Vector((30, 60, 20)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_hands_L",0]
	},
	"upperarm_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-40, -30, -40)), "max": Vector((80, 50, 60)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_hands_L",1]
	},
	"lowerarm_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-10, -10, 0)), "max": Vector((130, 50, 0)),
		"spd": Vector((1, 1, 0)),
		"prop": ["mbh_hands_L",2]
	},

	"hand_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-50, -50, -50)), "max": Vector((50, 50, 50)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_wrist_L",0]
	},
	"thumb01_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-20, -20, -40)), "max": Vector((30, 60, 20)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_thumb_L",0]
	},
	"thumb02_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, -10)), "max": Vector((10, 0, 50)),
		"spd": Vector((1, 0, 1)),
		"prop": ["mbh_thumb_L",1]
	},
	"thumb03_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((20, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_thumb_L",2]
	},
	"index01_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, -40)), "max": Vector((30, 0, 10)),
		"spd": Vector((1, 0, 1)),
		"prop": ["mbh_index_L",0]
	},
	"index02_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_index_L",1]
	},
	"index03_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_index_L",2]
	},
	"middle01_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, -40)), "max": Vector((30, 0, 10)),
		"spd": Vector((1, 0, 1)),
		"prop": ["mbh_middle_L",0]
	},
	"middle02_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_middle_L",1]
	},
	"middle03_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_middle_L",2]
	},
	"ring01_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, -40)), "max": Vector((30, 0, 10)),
		"spd": Vector((1, 0, 1)),
		"prop": ["mbh_ring_L",0]
	},
	"ring02_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_ring_L",1]
	},
	"ring03_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_ring_L",2]
	},
	"pinky01_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, -40)), "max": Vector((30, 0, 10)),
		"spd": Vector((1, 0, 1)),
		"prop": ["mbh_pinky_L",0]
	},
	"pinky02_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_pinky_L",1]
	},
	"pinky03_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-80, 0, 0)), "max": Vector((10, 0, 0)),
		"spd": Vector((1, 0, 0)),
		"prop": ["mbh_pinky_L",2]
	},
}

def deduceRightBones():
	bones = list(MBArmatureBones_v02.keys())
	for boneName_L in bones:
		if boneName_L.find("_L") > 0:
			boneName_R = boneName_L.replace("_L","_R")
			propName_L = MBArmatureBones_v02[boneName_L]["prop"][0]
			propName_R = propName_L.replace("_L","_R")
			MBArmatureBones_v02[boneName_R] = copy.deepcopy(MBArmatureBones_v02[boneName_L])
			MBArmatureBones_v02[boneName_R]["prop"][0] = propName_R
deduceRightBones()

def mixBone(context, boneName, curMuls, addVal, rememAfter, applyLims):
	scene = context.scene
	armatr = context.active_object
	if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
		return
	boneNames = armatr.pose.bones.keys()
	if boneName in boneNames:
		bone = armatr.pose.bones[boneName]
		bone.rotation_mode = "ZYX"
		minVal = MBArmatureBones_v02[boneName]["min"]
		maxVal = MBArmatureBones_v02[boneName]["max"]
		curVal = bone.rotation_euler
		newX = curMuls[0]*curVal[0]+addVal[0]
		newY = curMuls[1]*curVal[1]+addVal[1]
		newZ = curMuls[2]*curVal[2]+addVal[2]
		if applyLims:
			newX = np.clip(newX,radians(minVal[0]),radians(maxVal[0]))
			newY = np.clip(newY,radians(minVal[1]),radians(maxVal[1]))
			newZ = np.clip(newZ,radians(minVal[2]),radians(maxVal[2]))
		newVal = Vector((newX,newY,newZ))
		bone.rotation_euler = newVal
		if rememAfter:
			MBArmatureBones_v02[boneName]["rest"] = newVal
		print("Updating bone",boneName,newVal)

def applyAngls(self,context):
	wpposeOpts = context.scene.wplPoseMBSettings
	for boneName in MBArmatureBones_v02:
		defSpd = MBArmatureBones_v02[boneName]["spd"]
		defVal = MBArmatureBones_v02[boneName]["def"]
		boneProp = MBArmatureBones_v02[boneName]["prop"]
		if boneProp is not None:
			propProp = wpposeOpts.get(boneProp[0])
			isEnabled = 0
			if propProp is not None:
				isEnabled = propProp[boneProp[1]]
			if isEnabled > 0:
				refVal = defVal
				if "rest" in MBArmatureBones_v02[boneName]:
					refVal = MBArmatureBones_v02[boneName]["rest"]
				newX = refVal[0]+wpposeOpts.mbh_foldAngle*defSpd[0]
				newY = refVal[1]+wpposeOpts.mbh_twistAngle*defSpd[1]
				newZ = refVal[2]+wpposeOpts.mbh_tiltAngle*defSpd[2]
				rotVec = Vector((newX,newY,newZ))
				#print("Applying", rotVec, "to", boneName)
				mixBone(context, boneName, Vector((0,0,0)), rotVec, False, wpposeOpts.mbh_applyLimits)
	bpy.context.scene.update()
	return None

def restAngls(self,context):
	wpposeOpts = context.scene.wplPoseMBSettings
	for boneName in MBArmatureBones_v02:
		# isEnabled = 0
		# boneProp = MBArmatureBones_v02[boneName]["prop"]
		# propProp = wpposeOpts.get(boneProp[0])
		# if propProp is not None:
			# isEnabled = propProp[boneProp[1]]
			# print("restAngls",boneName,isEnabled,boneProp[0],boneProp[1])
		mixBone(context, boneName, Vector((1,1,1)), Vector((0,0,0)), True, False)
	wpposeOpts.mbh_foldAngle = 0
	wpposeOpts.mbh_twistAngle = 0
	wpposeOpts.mbh_tiltAngle = 0
	bpy.context.scene.update()
	return None

def deflAngls(self,context):
	wpposeOpts = context.scene.wplPoseMBSettings
	wpposeOpts.mbh_foldAngle = 0
	wpposeOpts.mbh_twistAngle = 0
	wpposeOpts.mbh_tiltAngle = 0

	for boneName in MBArmatureBones_v02:
		defVal = MBArmatureBones_v02[boneName]["def"]
		boneProp = MBArmatureBones_v02[boneName]["prop"]
		if boneProp is not None:
			propProp = wpposeOpts.get(boneProp[0])
			isEnabled = 0
			if propProp is not None:
				isEnabled = propProp[boneProp[1]]
			if isEnabled > 0:
				mixBone(context, boneName, Vector((0,0,0)), Vector((defVal[0],defVal[1],defVal[2])), True, False)
	bpy.context.scene.update()
	return None

#############################################################################
#############################################################################
#############################################################################
class wplPoseMBSettings(PropertyGroup):
	mbh_head = BoolVectorProperty(
		size=2,
		default=[False,False], update=restAngls)
	mbh_spine = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_legs_L = BoolVectorProperty(
		size=4,
		default=[False,False,False,False], update=restAngls)
	mbh_legs_R = BoolVectorProperty(
		size=4,
		default=[False,False,False,False], update=restAngls)

	mbh_hands_L = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_hands_R = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)

	mbh_wrist_L = BoolVectorProperty(
		size=1,
		default=[False], update=restAngls)
	mbh_thumb_L = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_index_L = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_middle_L = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_ring_L = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_pinky_L = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_wrist_R = BoolVectorProperty(
		size=1,
		default=[False], update=restAngls)
	mbh_thumb_R = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_index_R = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_middle_R = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_ring_R = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_pinky_R = BoolVectorProperty(
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_foldAngle = FloatProperty(
		name = "Fold",
		min = -3.14,
		soft_min  = -3.14,
		max = 3.14,
		soft_max  = 3.14,
		step = 10.0,
		unit = 'ROTATION',
		default = 0,
		update=applyAngls
	)
	mbh_tiltAngle = FloatProperty(
		name = "Tilt",
		min = -3.14,
		soft_min  = -3.14,
		max = 3.14,
		soft_max  = 3.14,
		step = 3.0,
		unit = 'ROTATION',
		default = 0,
		update=applyAngls
	)
	mbh_twistAngle = FloatProperty(
		name = "Twist",
		min = -3.14,
		soft_min  = -3.14,
		max = 3.14,
		soft_max  = 3.14,
		step = 10.0,
		unit = 'ROTATION',
		default = 0,
		update=applyAngls
	)
	mbh_applyLimits = BoolProperty(
		default = True
	)

#############################################################################
#############################################################################
#############################################################################
class wplposing_mbbn2zero( bpy.types.Operator ):
	bl_idname = "mesh.wplposing_mbbn2zero"
	bl_label = "Reset bones to default angles"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Armature))
		return p

	def execute( self, context ):
		deflAngls(self, context)
		return {'FINISHED'}

class wplposing_clearchbx( bpy.types.Operator ):
	bl_idname = "mesh.wplposing_clearchbx"
	bl_label = "Clear posing checkboxes"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Armature))
		return p

	def execute( self, context ):
		wpposeOpts = context.scene.wplPoseMBSettings
		for boneName in MBArmatureBones_v02:
			boneProp = MBArmatureBones_v02[boneName]["prop"]
			if boneProp is not None:
				propProp = wpposeOpts.get(boneProp[0])
				if propProp is not None:
					propProp[boneProp[1]] = False
		return {'FINISHED'}

class wplposing_bn_select_active( bpy.types.Operator ):
	bl_idname = "mesh.wplposing_bn_select_active"
	bl_label = "Select corresponding bones"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Armature))
		return p

	def execute( self, context ):
		wpposeOpts = context.scene.wplPoseMBSettings
		scene = context.scene
		armatr = context.active_object
		if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
			return {'CANCELLED'}
		boneNames = armatr.pose.bones.keys()
		for boneName in boneNames:
			if boneName in MBArmatureBones_v02:
				boneProp = MBArmatureBones_v02[boneName]["prop"]
				if boneProp is not None:
					propProp = wpposeOpts.get(boneProp[0])
					if propProp is not None and propProp[boneProp[1]] == True:
						bone = armatr.data.bones[boneName]
						bone.select = True
		return {'FINISHED'}

class wplposing_bn_deselect_inactive( bpy.types.Operator ):
	bl_idname = "mesh.wplposing_bn_deselect_inactive"
	bl_label = "Select corresponding bones"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Armature))
		return p

	def execute( self, context ):
		wpposeOpts = context.scene.wplPoseMBSettings
		scene = context.scene
		armatr = context.active_object
		if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
			return {'CANCELLED'}
		boneNames = armatr.pose.bones.keys()
		for boneName in boneNames:
			need2deselect = True
			if boneName in MBArmatureBones_v02:
				boneProp = MBArmatureBones_v02[boneName]["prop"]
				if boneProp is not None:
					propProp = wpposeOpts.get(boneProp[0])
					if propProp is not None and propProp[boneProp[1]] == True:
						need2deselect = False
			if need2deselect:
				bone = armatr.data.bones[boneName]
				bone.select = False
		return {'FINISHED'}
#############################################################################
#############################################################################
#############################################################################
class WPLPosingMBArmBody_Panel(bpy.types.Panel):
	bl_label = "Posing: Body"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "posemode"
	bl_category = 'ManuelBastioniLAB'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		wpposeOpts = context.scene.wplPoseMBSettings

		# display the properties
		col = layout.column()
		row_ftt1 = col.row(align=True)
		row_ftt1.prop(wpposeOpts, "mbh_foldAngle", text="Fold")
		row_ftt1.prop(wpposeOpts, "mbh_twistAngle", text="Twist")
		row_ftt1.prop(wpposeOpts, "mbh_tiltAngle", text="Tilt")
		box_ftt1 = col.box()
		row_mbh_head = box_ftt1.row()
		row_mbh_head.prop(wpposeOpts, "mbh_head", text="Head")
		row_mbh_spine = box_ftt1.row()
		row_mbh_spine.prop(wpposeOpts, "mbh_spine", text="Spine")
		box_ftt2 = col.box()
		row_mbh_hands_L = box_ftt2.row()
		row_mbh_hands_L.prop(wpposeOpts, "mbh_hands_L", text="L:Hand")
		row_mbh_hands_R = box_ftt2.row()
		row_mbh_hands_R.prop(wpposeOpts, "mbh_hands_R", text="R:Hand")
		box_ftt3 = col.box()
		row_mbh_legs_L = box_ftt3.row()
		row_mbh_legs_L.prop(wpposeOpts, "mbh_legs_L", text="L:Leg")
		row_mbh_legs_R = box_ftt3.row()
		row_mbh_legs_R.prop(wpposeOpts, "mbh_legs_R", text="R:Leg")
		col.operator("mesh.wplposing_mbbn2zero", text="Reset to default")


class WPLPosingMBArmLHand_Panel(bpy.types.Panel):
	bl_label = "Posing: Left palm"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "posemode"
	bl_category = 'ManuelBastioniLAB'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		wpposeOpts = context.scene.wplPoseMBSettings

		# display the properties
		col = layout.column()

		row_ftt2 = col.row(align=True)
		row_ftt2.prop(wpposeOpts, "mbh_foldAngle", text="Fold")
		row_ftt2.prop(wpposeOpts, "mbh_twistAngle", text="Twist")
		row_ftt2.prop(wpposeOpts, "mbh_tiltAngle", text="Tilt")
		box_ftt4 = col.box()
		row_mbh_wrist_L = box_ftt4.row()
		row_mbh_wrist_L.prop(wpposeOpts, "mbh_wrist_L", text="Wrist")
		box_ftt5 = col.box()
		row_mbh_thumb_L = box_ftt5.row()
		row_mbh_thumb_L.prop(wpposeOpts, "mbh_thumb_L", text="=:-:-")
		row_mbh_index_L = box_ftt5.row()
		row_mbh_index_L.prop(wpposeOpts, "mbh_index_L", text="=:=:>")
		row_mbh_middle_L = box_ftt5.row()
		row_mbh_middle_L.prop(wpposeOpts, "mbh_middle_L", text="=:=:-")
		row_mbh_ring_L = box_ftt5.row()
		row_mbh_ring_L.prop(wpposeOpts, "mbh_ring_L", text="=:=:-")
		row_mbh_pinky_L = box_ftt5.row()
		row_mbh_pinky_L.prop(wpposeOpts, "mbh_pinky_L", text="=:-:-")
		col.operator("mesh.wplposing_mbbn2zero", text="Reset to default")

class WPLPosingMBArmRHand_Panel(bpy.types.Panel):
	bl_label = "Posing: Right palm"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "posemode"
	bl_category = 'ManuelBastioniLAB'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		wpposeOpts = context.scene.wplPoseMBSettings

		# display the properties
		col = layout.column()

		row_ftt3 = col.row(align=True)
		row_ftt3.prop(wpposeOpts, "mbh_foldAngle", text="Fold")
		row_ftt3.prop(wpposeOpts, "mbh_twistAngle", text="Twist")
		row_ftt3.prop(wpposeOpts, "mbh_tiltAngle", text="Tilt")
		box_ftt6 = col.box()
		row_mbh_wrist_R = box_ftt6.row()
		row_mbh_wrist_R.prop(wpposeOpts, "mbh_wrist_R", text="Wrist")
		box_ftt7 = col.box()
		row_mbh_thumb_R = box_ftt7.row()
		row_mbh_thumb_R.prop(wpposeOpts, "mbh_thumb_R", text="=:-:-")
		row_mbh_index_R = box_ftt7.row()
		row_mbh_index_R.prop(wpposeOpts, "mbh_index_R", text="=:=:>")
		row_mbh_middle_R = box_ftt7.row()
		row_mbh_middle_R.prop(wpposeOpts, "mbh_middle_R", text="=:=:-")
		row_mbh_ring_R = box_ftt7.row()
		row_mbh_ring_R.prop(wpposeOpts, "mbh_ring_R", text="=:=:-")
		row_mbh_pinky_R = box_ftt7.row()
		row_mbh_pinky_R.prop(wpposeOpts, "mbh_pinky_R", text="=:-:-")
		col.operator("mesh.wplposing_mbbn2zero", text="Reset to default")

class WPLPosingMBArmSettings_Panel(bpy.types.Panel):
	bl_label = "Opts and Utils"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "posemode"
	bl_category = 'ManuelBastioniLAB'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		wpposeOpts = context.scene.wplPoseMBSettings

		# display the properties
		col = layout.column()
		col.prop(wpposeOpts, "mbh_applyLimits", text="Apply physical rotation limits")
		col.operator("mesh.wplposing_clearchbx", text="Clear checkboxes")
		row1 = col.row()
		row1.operator("mesh.wplposing_bn_select_active", text="Select bones")
		row1.operator("mesh.wplposing_bn_deselect_inactive", text="Deselect others")

#############################################################################
#############################################################################
#############################################################################

def register():
	print("WPLPosingSt_Panel registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wplPoseMBSettings = PointerProperty(type=wplPoseMBSettings)

def unregister():
	del bpy.types.Scene.wplPoseMBSettings
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
