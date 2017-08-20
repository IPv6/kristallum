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

ArmatureLimitsPerBone = {
	"hand_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-50, -50, -50)), "max": Vector((50, 50, 50)),
		"spd": Vector((1, 1, 1)),
		"prop": ["mbh_wrist_L",0]
	},
	"thumb01_L" : {
		"def": Vector((0, 0, 0)), "min": Vector((-20, -20, -10)), "max": Vector((30, 60, 20)),
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

def restoreRightBones():
	bones = list(ArmatureLimitsPerBone.keys())
	for boneName_L in bones:
		boneName_R = boneName_L.replace("_L","_R")
		propName_L = ArmatureLimitsPerBone[boneName_L]["prop"][0]
		propName_R = propName_L.replace("_L","_R")
		ArmatureLimitsPerBone[boneName_R] = copy.deepcopy(ArmatureLimitsPerBone[boneName_L])
		ArmatureLimitsPerBone[boneName_R]["prop"][0] = propName_R
restoreRightBones()

def mixBone(context, boneName, curMuls, addVal, rememAfter):
	scene = context.scene
	armatr = context.active_object
	if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
		return
	boneNames = armatr.pose.bones.keys()
	if boneName in boneNames:
		bone = armatr.pose.bones[boneName]
		bone.rotation_mode = "ZYX"
		minVal = ArmatureLimitsPerBone[boneName]["min"]
		maxVal = ArmatureLimitsPerBone[boneName]["max"]
		curVal = bone.rotation_euler
		newX = curMuls[0]*curVal[0]+addVal[0]
		newY = curMuls[1]*curVal[1]+addVal[1]
		newZ = curMuls[2]*curVal[2]+addVal[2]
		newX = np.clip(newX,radians(minVal[0]),radians(maxVal[0]))
		newY = np.clip(newY,radians(minVal[1]),radians(maxVal[1]))
		newZ = np.clip(newZ,radians(minVal[2]),radians(maxVal[2]))
		newVal = Vector((newX,newY,newZ))
		bone.rotation_euler = newVal
		if rememAfter:
			ArmatureLimitsPerBone[boneName]["rest"] = newVal
		print("Updating bone",boneName,newVal)

def applyAngls(self,context):
	wpposeOpts = context.scene.wplPoseMBSettings
	for boneName in ArmatureLimitsPerBone:
		defSpd = ArmatureLimitsPerBone[boneName]["spd"]
		defVal = ArmatureLimitsPerBone[boneName]["def"]
		boneProp = ArmatureLimitsPerBone[boneName]["prop"]
		propProp = wpposeOpts.get(boneProp[0])
		isEnabled = 0
		if propProp is not None:
			isEnabled = propProp[boneProp[1]]
		if isEnabled > 0:
			refVal = defVal
			if "rest" in ArmatureLimitsPerBone[boneName]:
				refVal = ArmatureLimitsPerBone[boneName]["rest"]
			newX = refVal[0]+wpposeOpts.mbh_foldAngle*defSpd[0]
			newY = refVal[1]+wpposeOpts.mbh_twistAngle*defSpd[1]
			newZ = refVal[2]+wpposeOpts.mbh_tiltAngle*defSpd[2]
			mixBone(context, boneName, Vector((0,0,0)), Vector((newX,newY,newZ)), False)
	bpy.context.scene.update()
	return None

def restAngls(self,context):
	wpposeOpts = context.scene.wplPoseMBSettings
	for boneName in ArmatureLimitsPerBone:
		# isEnabled = 0
		# boneProp = ArmatureLimitsPerBone[boneName]["prop"]
		# propProp = wpposeOpts.get(boneProp[0])
		# if propProp is not None:
			# isEnabled = propProp[boneProp[1]]
			# print("restAngls",boneName,isEnabled,boneProp[0],boneProp[1])
		mixBone(context, boneName, Vector((1,1,1)), Vector((0,0,0)), True)
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
	
	for boneName in ArmatureLimitsPerBone:
		defVal = ArmatureLimitsPerBone[boneName]["def"]
		boneProp = ArmatureLimitsPerBone[boneName]["prop"]
		propProp = wpposeOpts.get(boneProp[0])
		isEnabled = 0
		if propProp is not None:
			isEnabled = propProp[boneProp[1]]
		if isEnabled > 0:
			mixBone(context, boneName, Vector((0,0,0)), Vector((defVal[0],defVal[1],defVal[2])), True)
	bpy.context.scene.update()
	return None
#############################################################################
#############################################################################
#############################################################################

def unselect_all():
	for obj in bpy.data.objects:
		obj.select = False

def force_visible_object(obj):
	if obj:
		if obj.hide == True:
			obj.hide = False
		for n in range(len(obj.layers)):
			obj.layers[n] = False
		current_layer_index = bpy.context.scene.active_layer
		obj.layers[current_layer_index] = True

def select_and_change_mode(obj,obj_mode,hidden=False):
	unselect_all()
	if obj:
		obj.select = True
		bpy.context.scene.objects.active = obj
		force_visible_object(obj)
		try:
			m=bpy.context.mode
			if bpy.context.mode!='OBJECT':
				bpy.ops.object.mode_set(mode='OBJECT')
			bpy.context.scene.update()
			bpy.ops.object.mode_set(mode=obj_mode)
			#print("Mode switched to ", obj_mode)
		except:
			pass
		obj.hide = hidden
	return m

#############################################################################
#############################################################################
#############################################################################
class wplPoseMBSettings(PropertyGroup):
	mbh_wrist_L = BoolVectorProperty(
		name="*L",
		size=1,
		default=[False], update=restAngls)
	mbh_thumb_L = BoolVectorProperty(
		name="L==",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_index_L = BoolVectorProperty(
		name="L== >",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_middle_L = BoolVectorProperty(
		name="L==-",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_ring_L = BoolVectorProperty(
		name="L==-",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_pinky_L = BoolVectorProperty(
		name="L==-",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_wrist_R = BoolVectorProperty(
		name="*R",
		size=1,
		default=[False], update=restAngls)
	mbh_thumb_R = BoolVectorProperty(
		name="R==",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_index_R = BoolVectorProperty(
		name="R== >",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_middle_R = BoolVectorProperty(
		name="R==-",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_ring_R = BoolVectorProperty(
		name="R==-",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_pinky_R = BoolVectorProperty(
		name="R==-",
		size=3,
		default=[False,False,False], update=restAngls)
	mbh_foldAngle = FloatProperty(
		name = "Fold",
		min = -1.57,
		max = 1.57,
		#step = 0.3,
		unit = 'ROTATION',
		default = 0, 
		update=applyAngls
	)
	mbh_tiltAngle = FloatProperty(
		name = "Tilt",
		min = -1.57,
		max = 1.57,
		#step = 1.0,
		unit = 'ROTATION',
		default = 0,
		update=applyAngls
	)
	mbh_twistAngle = FloatProperty(
		name = "Twist",
		min = -1.57,
		max = 1.57,
		#step = 1.0,
		unit = 'ROTATION',
		default = 0,
		update=applyAngls
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
	
class WPLPosingMBArm_Panel(bpy.types.Panel):
	bl_label = "MB Posing"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "posemode"
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		wpposeOpts = context.scene.wplPoseMBSettings

		# display the properties
		col = layout.column()
		col.label(text = "Left palm")
		col.prop(wpposeOpts, "mbh_foldAngle")
		col.prop(wpposeOpts, "mbh_twistAngle")
		col.prop(wpposeOpts, "mbh_tiltAngle")
		row_mbh_wrist_L = col.row()
		row_mbh_wrist_L.prop(wpposeOpts, "mbh_wrist_L")
		row_mbh_thumb_L = col.row()
		row_mbh_thumb_L.prop(wpposeOpts, "mbh_thumb_L")
		row_mbh_index_L = col.row()
		row_mbh_index_L.prop(wpposeOpts, "mbh_index_L")
		row_mbh_middle_L = col.row()
		row_mbh_middle_L.prop(wpposeOpts, "mbh_middle_L")
		row_mbh_ring_L = col.row()
		row_mbh_ring_L.prop(wpposeOpts, "mbh_ring_L")
		row_mbh_pinky_L = col.row()
		row_mbh_pinky_L.prop(wpposeOpts, "mbh_pinky_L")
		col.operator("mesh.wplposing_mbbn2zero", text="Reset to default")
		
		col.separator()
		col.label(text = "Right palm")
		col.prop(wpposeOpts, "mbh_foldAngle")
		col.prop(wpposeOpts, "mbh_twistAngle")
		col.prop(wpposeOpts, "mbh_tiltAngle")
		row_mbh_wrist_R = col.row()
		row_mbh_wrist_R.prop(wpposeOpts, "mbh_wrist_R")
		row_mbh_thumb_R = col.row()
		row_mbh_thumb_R.prop(wpposeOpts, "mbh_thumb_R")
		row_mbh_index_R = col.row()
		row_mbh_index_R.prop(wpposeOpts, "mbh_index_R")
		row_mbh_middle_R = col.row()
		row_mbh_middle_R.prop(wpposeOpts, "mbh_middle_R")
		row_mbh_ring_R = col.row()
		row_mbh_ring_R.prop(wpposeOpts, "mbh_ring_R")
		row_mbh_pinky_R = col.row()
		row_mbh_pinky_R.prop(wpposeOpts, "mbh_pinky_R")
		col.operator("mesh.wplposing_mbbn2zero", text="Reset to default")

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
