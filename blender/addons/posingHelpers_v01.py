# Align Manuel Bastioni pose to DAZ-based pose (BVH)
# V8 is ok except hands (fingers ignored)

import bpy
import bmesh
import math
import mathutils
from math import radians
from mathutils import Vector
import numpy as np
#import json

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
	"name": "WPL Posing tools",
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

boneBrutDeepness = 0.05
boneMapV8 = [
	["pelvis", "pelvis", "000", (radians(25),radians(0),radians(-10))],
	["spine01", "abdomenLower", "ZYX"],
	["spine02", "abdomenUpper", "ZYX"],
	["spine03", "chestUpper", "ZYX"],
	["neck", "neckLower", "ZYX"],
	["head", "head", "ZYX"],

	# hands
	["clavicle_L", "lCollar", "BRUT_ZX"], ["clavicle_R", "rCollar", "BRUT_ZX"],
	["upperarm_L", "lShldrBend", "BRUT_ZYX"], ["upperarm_R", "rShldrBend", "BRUT_ZYX",],
	["lowerarm_L", "lForearmBend", "BRUT_ZYX"], ["lowerarm_R", "rForearmBend", "BRUT_ZYX"],
	["hand_L", "lHand", "BRUT_ZX"], ["hand_R", "rHand", "BRUT_ZX"],

	# palms
	["thumb01_L", "lThumb1", "BRUT_ZX"], ["thumb02_L", "lThumb2", "BRUT_X"], ["thumb03_L", "lThumb3", "000"],
	["index00_L", "lCarpal1", "000"],
	["middle00_L", "lCarpal2", "000"],
	["ring00_L", "lCarpal3", "000"],
	["pinky00_L", "lCarpal4", "000"],
	["index01_L", "lIndex1", "BRUT_X"], ["index02_L", "lIndex2", "BRUT_X"], ["index03_L", "lIndex3", "000"],
	["middle01_L", "lMid1", "BRUT_X"], ["middle02_L", "lMid2", "BRUT_X"], ["middle03_L", "lMid3", "000"],
	["ring01_L", "lRing1", "BRUT_X"], ["ring02_L", "lRing2", "BRUT_X"], ["ring03_L", "lRing3", "000"],
	["pinky01_L", "lPinky1", "BRUT_X"], ["pinky02_L", "lPinky2", "BRUT_X"], ["pinky03_L", "lPinky3", "000"],

	["thumb01_R", "rThumb1", "BRUT_ZX"], ["thumb02_R", "rThumb2", "BRUT_X"], ["thumb03_R", "rThumb3", "000"],
	["index00_R", "rCarpal1", "000"],
	["middle00_R", "rCarpal2", "000"],
	["ring00_R", "rCarpal3", "000"],
	["pinky00_R", "rCarpal4", "000"],
	["index01_R", "rIndex1", "BRUT_X"], ["index02_R", "rIndex2", "BRUT_X"], ["index03_R", "rIndex3", "000"],
	["middle01_R", "rMid1", "BRUT_X"], ["middle02_R", "rMid2", "BRUT_X"], ["middle03_R", "rMid3", "000"],
	["ring01_R", "rRing1", "BRUT_X"], ["ring02_R", "rRing2", "BRUT_X"], ["ring03_R", "rRing3", "000"],
	["pinky01_R", "rPinky1", "BRUT_X"], ["pinky02_R", "rPinky2", "BRUT_X"], ["pinky03_R", "rPinky3", "000"],

	# legs
	["thigh_L", "lThighBend", "-BRUT_ZX"],["thigh_R", "rThighBend", "-BRUT_ZX"],
	["calf_L", "lShin", "BRUT_ZX"],["calf_R", "rShin", "BRUT_ZX"],
	["foot_L", "lMetatarsals", "BRUT_ZX"], ["foot_R", "rMetatarsals", "BRUT_ZX"],
	["toes_L", "lSmallToe2", "BRUT_X"], ["toes_R", "rSmallToe2", "BRUT_X"]
]

def getBMStepsForArmt(donor_armt):
	bonenames = donor_armt.pose.bones.keys()
	#if "chest" in bonenames:
	#	print("getBMStepsForArmt: V3 armature detected")
	#	return boneMapV3
	if "abdomenUpper" in bonenames:
		print("getBMStepsForArmt: V8 armature detected")
		return boneMapV8
	return None

def get_object_by_name(name):
	if name in bpy.data.objects:
		return bpy.data.objects[name]
	return None

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

def remove_copy_constr(target_armat, transf_mod = 'COPY_TRANSFORMS'):
	constr_name = "wpltt_"+transf_mod
	for b in target_armat.pose.bones:
		if len(b.constraints) > 0:
			for cstr in b.constraints:
				if constr_name == cstr.name:
					b.constraints.remove(cstr)

def add_copy_constr(target_armat, donor_armat, bone_to_rotate, bone_from_rotate, transf_mod = 'COPY_TRANSFORMS', transf_space_own="WORLD", transf_space_targ=None):
	constr_name = "wpltt_"+transf_mod
	for b in target_armat.pose.bones:
		if (bone_to_rotate is None) or (b.name == bone_to_rotate):
			if constr_name not in b.constraints:
				cstr = b.constraints.new(transf_mod)
				cstr.target = donor_armat
				if bone_from_rotate is None:
					cstr.subtarget =  b.name
				else:
					cstr.subtarget =  bone_from_rotate
				if transf_space_targ is None:
					transf_space_targ = transf_space_own
				cstr.target_space = transf_space_targ
				cstr.owner_space = transf_space_own
				cstr.name = constr_name

def getActiveQuaternionRotation(armat, boneName):
	# another: https://blender.stackexchange.com/questions/44637/how-can-i-manually-calculate-bpy-types-posebone-matrix-using-blenders-python-ap
	# returns visual rotation of this bone, relative to rest pose, as a quaternion
	# after channels and constraints are applied
	armatureName = armat.name #find_armature().name
	bone = bpy.data.armatures[armatureName].bones[boneName]
	bone_ml = bone.matrix_local
	bone_pose = bpy.data.objects[armatureName].pose.bones[boneName]
	bone_pose_m = bone_pose.matrix
	if bone.parent:
		parent = bone.parent
		parent_ml = parent.matrix_local
		parent_pose = bone_pose.parent
		parent_pose_m = parent_pose.matrix
		object_diff = parent_ml.inverted() * bone_ml
		pose_diff = parent_pose_m.inverted() * bone_pose_m
		local_diff = object_diff.inverted() * pose_diff
	else:
		local_diff = bone_ml.inverted() * bone_pose_m
	return local_diff.to_quaternion()

class wplposing_unrollclon( bpy.types.Operator ):
	bl_idname = "mesh.wplposing_unrollclon"
	bl_label = "Reset bone roll to 0 without affecting pose"
	bl_options = {'REGISTER', 'UNDO'}
	@classmethod
	def poll( cls, context ):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Armature))
		return p

	def execute( self, context ):
		wpposeOpts = context.scene.wplPosingSettings
		finalRoll = 0
		scene = context.scene
		targt_arm = context.active_object
		if targt_arm is None or not isinstance(targt_arm.data, bpy.types.Armature):
			self.report({'ERROR'}, "No Armature selected, select armature first")
			return {'CANCELLED'}
		force_visible_object(targt_arm)

		cloned_arm = targt_arm.copy()
		cloned_arm.data = cloned_arm.data.copy()
		scene.objects.link(cloned_arm)
		add_copy_constr(cloned_arm,targt_arm, None, None, 'COPY_ROTATION', 'WORLD')

		select_and_change_mode(cloned_arm,"EDIT")
		for cl_bn in cloned_arm.pose.bones:
			edit_bn = cloned_arm.data.edit_bones.get(cl_bn.name)
			if edit_bn is not None:
				edit_bn.roll = finalRoll

		# Applying contraints to clone to get REAL tranforms with constrains in local space
		select_and_change_mode(cloned_arm,"POSE")
		# Apply Visual Transform to Pose
		bpy.ops.pose.select_all(action='SELECT')
		bpy.ops.pose.visual_transform_apply()
		remove_copy_constr(cloned_arm, 'COPY_ROTATION')

		# getting corrected values back
		matrix_data = {}
		select_and_change_mode(cloned_arm,"OBJECT")
		for cl_bn in cloned_arm.pose.bones:
			cl_bn.rotation_mode = 'QUATERNION'
			quat = cl_bn.rotation_quaternion
			#quat = getActiveQuaternionRotation(cloned_arm,cl_bn.name)
			#quat = cl_bn.matrix.to_quaternion()
			matrix_data[cl_bn.name] = [quat[0],quat[1], quat[2],quat[3]]

		select_and_change_mode(targt_arm,"EDIT")
		for cl_bn in targt_arm.pose.bones:
			edit_bn = targt_arm.data.edit_bones.get(cl_bn.name)
			if edit_bn is not None:
				edit_bn.roll = finalRoll

		select_and_change_mode(targt_arm,"POSE")
		for cl_bn in targt_arm.pose.bones:
			cl_bn.rotation_mode = 'QUATERNION'
			cl_bn.rotation_quaternion = matrix_data[cl_bn.name]

		select_and_change_mode(targt_arm,"OBJECT")
		scene.objects.unlink(cloned_arm)
		bpy.data.objects.remove(cloned_arm)
		return {'FINISHED'}


class wplposing_arm2mbp( bpy.types.Operator ):
	bl_idname = "mesh.wplposing_arm2mbp"
	bl_label = "Create Pose file for Manuel Bastioni rig"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Armature))
		return p

	def miniminizerValue(self, vec, axis):
		axis.normalize()
		weiquat = vec.rotation_difference(axis)
		#axis2 = axis.cross(Vector((0,0,1)))
		#axis3 = axis.cross(axis2)
		#mat = mathutils.Matrix.Identity(3)
		#mat.col[0] = axis3
		#mat.col[1] = axis2
		#mat.col[2] = axis
		#vec = vec*mat
		return weiquat
	def execute( self, context ):
		wpposeOpts = context.scene.wplPosingSettings
		scene = context.scene
		donor_obj = context.active_object
		if donor_obj is None or not isinstance(donor_obj.data, bpy.types.Armature):
			operator.report({'ERROR'}, "No Armature selected, select armature first")
			return {'CANCELLED'}
		targt_arm = get_object_by_name(wpposeOpts.mbArmatName)
		if targt_arm is None:
			operator.report({'ERROR'}, "No MB-Armature found")
			return {'CANCELLED'}
		force_visible_object(donor_obj)
		force_visible_object(targt_arm)
		#select_and_change_mode(targt_arm,"OBJECT")

		targt_editbone_snap = {}
		matrix_data = {}
		bones_mapping_steps = getBMStepsForArmt(donor_obj)
		if bones_mapping_steps is None:
			self.report({'ERROR'}, "No Arm-Mapping found")
			return {'CANCELLED'}

		bones_ok = 0
		bones_err = 0
		donor2targ_map = {}
		targ2donor_map = {}
		bones_names_donor = donor_obj.pose.bones.keys()
		bones_names_targ = targt_arm.pose.bones.keys()
		for step in bones_mapping_steps:
			targt_bn_name = step[0]
			donor_bn_name = step[1]
			donor2targ_map[donor_bn_name] = targt_bn_name
			targ2donor_map[targt_bn_name] = donor_bn_name
		#getting Roll values from target armature
		select_and_change_mode(targt_arm,"OBJECT")
		bpy.ops.object.editmode_toggle()
		select_and_change_mode(targt_arm,"EDIT")
		for bnn in bones_names_targ:
			targ_bn = targt_arm.data.edit_bones.get(bnn)
			if targ_bn is not None:
				targt_editbone_snap[bnn] = [targ_bn.roll, Vector(targ_bn.head), Vector(targ_bn.tail)]
		#do the transfer
		cloned_arm = donor_obj.copy()
		cloned_arm.data = cloned_arm.data.copy()
		scene.objects.link(cloned_arm)
		select_and_change_mode(cloned_arm,"OBJECT")
		add_copy_constr(cloned_arm,donor_obj, None, None, 'COPY_TRANSFORMS', 'WORLD')
		add_copy_constr(cloned_arm,donor_obj, None, None, 'COPY_ROTATION', 'WORLD')
		bpy.ops.object.editmode_toggle()
		select_and_change_mode(cloned_arm,"EDIT")
		cl_bns = cloned_arm.data.edit_bones.keys()
		for cl_bname in cl_bns:
			cl_vn = cloned_arm.data.edit_bones.get(cl_bname)
			if cl_bname not in donor2targ_map:
				# unused bone. deleting to make Blender recalc hierarchy
				bones_err = bones_err+1
				cloned_arm.data.edit_bones.remove(cl_vn)
			else:
				targbname = donor2targ_map[cl_bname]
				targsnap = targt_editbone_snap[targbname]
				cl_vn.roll = targsnap[0]

		# Applying contraints to clone to get REAL tranforms with constrains in local space
		select_and_change_mode(cloned_arm,"POSE")
		# Apply Visual Transform to Pose
		bpy.ops.pose.select_all(action='SELECT')
		bpy.ops.pose.visual_transform_apply()
		remove_copy_constr(cloned_arm, 'COPY_TRANSFORMS')
		remove_copy_constr(cloned_arm, 'COPY_ROTATION')

		bpy.context.scene.update()
		select_and_change_mode(targt_arm,"POSE")

		# preparing some walklists
		tx = 0
		ty = 0
		tz = 0
		brut_vecX = []
		brut_vecZX = []
		brut_vecZYX = []
		for tx in np.arange(-math.pi*0.5,math.pi*0.5,math.pi*boneBrutDeepness):
			brut_vecX.append(Vector((tx,0,0)))
			for tz in np.arange(-math.pi*0.2,math.pi*0.2,math.pi*boneBrutDeepness):
				brut_vecZX.append(Vector((tx,0,tz)))
				for ty in np.arange(-math.pi*0.5,math.pi*0.5,math.pi*boneBrutDeepness):
					brut_vecZYX.append(Vector((tx,ty,tz)))
		for step in bones_mapping_steps:
			donor_bn_name = step[1]
			targt_bn_name = step[0]
			meth = None
			if len(step) > 2:
				meth = step[2]
			targt_bnn = targt_arm.pose.bones.get(targt_bn_name)
			cloned_bnn = cloned_arm.pose.bones.get(donor_bn_name)
			if cloned_arm is not None and targt_bnn is not None:
				bones_ok = bones_ok+1
				walklist = brut_vecZX
				clone_prel = 1.0
				if meth == "BRUT_X":
					walklist = brut_vecX
					meth = "BRUT"
				if meth == "BRUT_ZX":
					walklist = brut_vecZX
					meth = "BRUT"
				if meth == "-BRUT_ZX":
					clone_prel = -1
					walklist = brut_vecZX
					meth = "BRUT"
				if meth == "BRUT_ZYX":
					walklist = brut_vecZYX
					meth = "BRUT"
				if meth == "-BRUT_ZYX":
					clone_prel = -1
					walklist = brut_vecZYX
					meth = "BRUT"
				if meth == "BRUT":
					#clone_mnm = cloned_bnn.tail
					clone_prn = Vector((0,0,1))
					if cloned_bnn.parent:
						clone_prn = clone_prel*(cloned_bnn.parent.tail-cloned_bnn.parent.head)
					clone_mnm = self.miniminizerValue((cloned_bnn.tail-cloned_bnn.head), clone_prn)
					min_mnm = 999
					min_val = Vector((0,0,0))
					tx = 0
					ty = 0
					tz = 0
					targt_bnn.rotation_mode = "ZYX"
					targt_bnn.rotation_euler = Vector((tx,ty,tz))
					bpy.context.scene.update()
					for this_v in walklist:
						targt_bnn.rotation_euler = this_v
						bpy.context.scene.update()
						this_prn = Vector((0,0,1))
						if targt_bnn.parent:
							this_prn = (targt_bnn.parent.tail-targt_bnn.parent.head)
						this_mnm = self.miniminizerValue((targt_bnn.tail-targt_bnn.head),this_prn)
						actual_mnm = (Vector(this_mnm)-Vector(clone_mnm)).length
						if actual_mnm < min_mnm:
							min_mnm = actual_mnm
							min_val = this_v
					targt_bnn.rotation_euler = min_val
				elif meth == "Z0X":
					targt_bnn.rotation_mode = "ZYX"
					targt_bnn.rotation_euler = Vector((cloned_bnn.rotation_euler[0],0,cloned_bnn.rotation_euler[2]))
				elif meth == "000":
					targt_bnn.rotation_mode = "ZYX"
					targt_bnn.rotation_euler = Vector((0,0,0))
					if len(step) > 3:
						targt_bnn.rotation_euler = Vector(step[3])
				elif meth == "CONST":
					add_copy_constr(targt_arm, cloned_arm, targt_bn_name, donor_bn_name, 'COPY_ROTATION', 'WORLD')
				elif meth == "CONTS_L":
					add_copy_constr(targt_arm, cloned_arm, targt_bn_name, donor_bn_name, 'COPY_ROTATION', 'LOCAL')
				elif (meth == 'QUAT') or (meth is None):
					cloned_bnn.rotation_mode = 'QUATERNION'
					targt_bnn.rotation_mode = 'QUATERNION'
					targt_bnn.rotation_quaternion = cloned_bnn.rotation_quaternion
				elif (meth == 'AXIS'):
					cloned_bnn.rotation_mode = 'AXIS_ANGLE'
					targt_bnn.rotation_mode = 'AXIS_ANGLE'
					targt_bnn.rotation_axis_angle = cloned_bnn.rotation_axis_angle
				else:
					cloned_bnn.rotation_mode = meth
					targt_bnn.rotation_mode = meth
					targt_bnn.rotation_euler = cloned_bnn.rotation_euler
				print(meth,": done for ",targt_bnn.name)

		# Applying contraints to get REAL tranforms
		select_and_change_mode(targt_arm,"POSE")
		bpy.ops.pose.select_all(action='SELECT')
		bpy.ops.pose.visual_transform_apply()
		remove_copy_constr(targt_arm, 'COPY_TRANSFORMS')
		remove_copy_constr(targt_arm, 'COPY_ROTATION')
		#scene.objects.unlink(cloned_arm)
		#bpy.data.objects.remove(cloned_arm)
		select_and_change_mode(targt_arm,"OBJECT")

		self.report({'INFO'}, "Pose transferred, bones="+str(bones_ok)+", skipped="+str(bones_err))
		return {'FINISHED'}

#############################################################################
#############################################################################
#############################################################################

class wplPosingSettings(PropertyGroup):
	mbArmatName = StringProperty(
		name="",
		description="Target Armature (MB)",
		default="human_skeleton")

class WPLPosingSt_Panel(bpy.types.Panel):
	bl_label = "MB skeleton helpers"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "objectmode"
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		wpposeOpts = context.scene.wplPosingSettings

		# display the properties
		col = layout.column()
		col.prop_search(wpposeOpts, "mbArmatName", scene, "objects")
		col.operator("mesh.wplposing_arm2mbp", text="Brutforce DAZ -> MB")
		#col.separator()
		#col.operator("mesh.wplposing_unrollclon", text="Reset Arm-Rolls")

#############################################################################
#############################################################################
#############################################################################

def register():
	print("WPLPosingSt_Panel registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wplPosingSettings = PointerProperty(type=wplPosingSettings)

def unregister():
	del bpy.types.Scene.wplPosingSettings
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
