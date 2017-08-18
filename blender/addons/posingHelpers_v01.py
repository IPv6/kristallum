# Creating Manuel Bastioni pose files from DAZ rigs (BVH), V8 is most ok
# TODO: rebase quaternion from donor roll to target Roll
# TODO: readjust from different rest poses

import bpy
import bmesh
import math
import mathutils
import json

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

boneMapV3 = [
	["pelvis", "pelvis"],
	["spine01", "abdomen"],
	["spine02", "abdomen2"],
	["spine03", "chest"],
	["neck", "neck"],
	["head", "head"],

	# hands
	["clavicle_L", "lCollar"], ["clavicle_R", "rCollar"],
	["upperarm_L", "lShldr"], ["upperarm_R", "rShldr"],
	["lowerarm_L", "lForeArm"], ["lowerarm_R", "rForeArm"],
	["hand_L", "lHand"], ["hand_R", "rHand"],

	["thumb01_L", "lThumb1"], ["thumb02_L", "lThumb2"], ["thumb03_L", "lThumb3"],
	["index00_L", "lCarpal1"], ["index01_L", "lIndex1"], ["index02_L", "lIndex2"], ["index03_L", "lIndex3"],
	["middle00_L", "lCarpal1"], ["middle01_L", "lMid1"], ["middle02_L", "lMid2"], ["middle03_L", "lMid3"],
	["ling00_L", "lCarpal2"], ["ling01_L", "lRing1"], ["ling02_L", "lRing2"], ["ling03_L", "lRing3"],
	["pinky00_L", "lCarpal2"], ["pinky01_L", "lPinky1"], ["pinky02_L", "lPinky2"], ["pinky03_L", "lPinky3"],

	["thumb01_R", "rThumb1"], ["thumb02_R", "rThumb2"], ["thumb03_R", "rThumb3"],
	["index00_R", "rCarpal1"], ["index01_R", "rIndex1"], ["index02_R", "rIndex2"], ["index03_R", "rIndex3"],
	["middle00_R", "rCarpal2"], ["middle01_R", "rMid1"], ["middle02_R", "rMid2"], ["middle03_R", "rMid3"],
	["ring00_R", "rCarpal3"], ["ring01_R", "rRing1"], ["ring02_R", "rRing2"], ["ring03_R", "rRing3"],
	["pinky00_R", "rCarpal4"], ["pinky01_R", "rPinky1"], ["pinky02_R", "rPinky2"], ["pinky03_R", "rPinky3"],

	# legs
	["thigh_L", "lThigh"],["thigh_R", "rThigh"],
	["calf_L", "lShin"],["calf_R", "rShin"],
	["foot_L", "lFoot"], ["foot_R", "rFoot"],
	["toes_L", "lSmallToe2"], ["toes_R", "rSmallToe2"]
]

boneMapV8 = [
	["pelvis", "pelvis"],
	["spine01", "abdomenLower"],
	["spine02", "abdomenUpper"],
	["spine03", "chestLower"],
	["neck", "neckLower"],
	["head", "head"],

	# hands
	["clavicle_L", "lCollar"], ["clavicle_R", "rCollar"],
	["upperarm_L", "lShldrBend"], ["upperarm_R", "rShldrBend"],
	#["upperarm_twist_L", "lShldrTwist"], ["upperarm_twist_R", "rShldrTwist"],
	["lowerarm_L", "lForearmBend"], ["lowerarm_R", "rForearmBend"],
	#["lowerarm_twist_L", "lForearmTwist"], ["lowerarm_twist_R", "rForearmTwist"],
	["hand_L", "lHand"], ["hand_R", "rHand"],

	["thumb01_L", "lThumb1"], ["thumb02_L", "lThumb2"], ["thumb03_L", "lThumb3"],
	["index00_L", "lCarpal1"], ["index01_L", "lIndex1"], ["index02_L", "lIndex2"], ["index03_L", "lIndex3"],
	["middle00_L", "lCarpal2"], ["middle01_L", "lMid1"], ["middle02_L", "lMid2"], ["middle03_L", "lMid3"],
	["ling00_L", "lCarpal3"], ["ling01_L", "lRing1"], ["ling02_L", "lRing2"], ["ling03_L", "lRing3"],
	["pinky00_L", "lCarpal4"], ["pinky01_L", "lPinky1"], ["pinky02_L", "lPinky2"], ["pinky03_L", "lPinky3"],

	["thumb01_R", "rThumb1"], ["thumb02_R", "rThumb2"], ["thumb03_R", "rThumb3"],
	["index00_R", "rCarpal1"], ["index01_R", "rIndex1"], ["index02_R", "rIndex2"], ["index03_R", "rIndex3"],
	["middle00_R", "rCarpal2"], ["middle01_R", "rMid1"], ["middle02_R", "rMid2"], ["middle03_R", "rMid3"],
	["ring00_R", "rCarpal3"], ["ring01_R", "rRing1"], ["ring02_R", "rRing2"], ["ring03_R", "rRing3"],
	["pinky00_R", "rCarpal4"], ["pinky01_R", "rPinky1"], ["pinky02_R", "rPinky2"], ["pinky03_R", "rPinky3"],

	# legs
	["thigh_L", "lThighBend"],["thigh_R", "rThighBend"],
	#["thigh_twist_L", "lThighTwist"],["thigh_twist_R", "rThighTwist"],
	["calf_L", "lShin"],["calf_R", "rShin"],
	#["calf_twist_L", "lShin"],["calf_twist_R", "rShin"],
	["foot_L", "lMetatarsals"], ["foot_R", "rMetatarsals"],
	["toes_L", "lSmallToe2"], ["toes_R", "rSmallToe2"]
]

def getBMStepsForArmt(donor_armt):
	bonenames = donor_armt.pose.bones.keys()
	if "chest" in bonenames:
		print("getBMStepsForArmt: V3 armature detected")
		return boneMapV3
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

def remove_copy_constr(target_armat):
	for b in target_armat.pose.bones:
		if len(b.constraints) > 0:
			for cstr in b.constraints:
				if "wpltt" in cstr.name:
					b.constraints.remove(cstr)

def add_copy_constr(target_armat, donor_armat, bone_to_rotate, bone_from_rotate, transf_mod = 'COPY_TRANSFORMS', transf_space="WORLD"):
	for b in target_armat.pose.bones:
		if (bone_to_rotate is None) or (b.name == bone_to_rotate):
			if "wpltt" not in b.constraints:
				#cstr = b.constraints.new('COPY_ROTATION')
				#cstr = b.constraints.new('COPY_TRANSFORMS')
				cstr = b.constraints.new(transf_mod)
				cstr.target = donor_armat
				if bone_from_rotate is None:
					cstr.subtarget =  b.name
				else:
					cstr.subtarget =  bone_from_rotate
				cstr.target_space = transf_space
				cstr.owner_space = transf_space
				cstr.name = "wpltt"

def getActiveQuaternionRotation(armat, boneName):
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
		bakeOpts = context.scene.wplPosingSettings
		finalRoll = 0
		scene = context.scene
		targt_arm = context.active_object
		if targt_arm is None or not isinstance(targt_arm.data, bpy.types.Armature):
			operator.report({'ERROR'}, "No Armature selected, select armature first")
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
		remove_copy_constr(cloned_arm)

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

	def execute( self, context ):
		bakeOpts = context.scene.wplPosingSettings
		scene = context.scene
		donor_obj = context.active_object
		if donor_obj is None or not isinstance(donor_obj.data, bpy.types.Armature):
			operator.report({'ERROR'}, "No Armature selected, select armature first")
			return {'CANCELLED'}
		targt_arm = get_object_by_name(bakeOpts.mbArmatName)
		if targt_arm is None:
			operator.report({'ERROR'}, "No MB-Armature found")
			return {'CANCELLED'}
		force_visible_object(donor_obj)
		force_visible_object(targt_arm)
		#select_and_change_mode(targt_arm,"OBJECT")

		bone_rolls_donor = {}
		bone_rolls_targt = {}
		matrix_data = {}
		bones_names_donor = donor_obj.pose.bones.keys()
		bones_names_targ = targt_arm.pose.bones.keys()
		bones_mapping_steps = getBMStepsForArmt(donor_obj)
		if bones_mapping_steps is None:
			operator.report({'ERROR'}, "No Arm-Mapping found")
			return {'CANCELLED'}

		# getting Roll values from original armature
		select_and_change_mode(donor_obj,"EDIT")
		#print("Donor bones",bones_names_donor)
		for bnn in bones_names_donor:
			donor_bn = donor_obj.data.edit_bones.get(bnn)
			if donor_bn is not None:
				bone_rolls_donor[bnn] = donor_bn.roll
				#print("Donor roll",bnn,donor_bn.roll)
		#print("bone_rolls_donor",bone_rolls_donor)

		# getting Roll values from target armature
		select_and_change_mode(targt_arm,"OBJECT")
		bpy.ops.object.editmode_toggle()
		select_and_change_mode(targt_arm,"EDIT")
		#print("Target bones",bones_names_targ)
		for bnn in bones_names_targ:
			targ_bn = targt_arm.data.edit_bones.get(bnn)
			if targ_bn is not None:
				bone_rolls_targt[bnn] = targ_bn.roll
				#print("Target roll",bnn,targ_bn.roll)
		#print("bone_rolls_targt",bone_rolls_targt)
		bones_ok = 0
		bones_err = 0
		for step in bones_mapping_steps:
			donor_bn_name = step[1]
			targt_bn_name = step[0]
			if donor_obj.pose.bones.get(donor_bn_name):
				bones_ok = bones_ok+1
				bone = donor_obj.pose.bones[donor_bn_name]
				#print("Reading bone",donor_bn_name,bone)
				bone.rotation_mode = 'QUATERNION'
				bone_quat = mathutils.Quaternion(bone.rotation_quaternion)
				if donor_bn_name in bone_rolls_donor:
					targ_bn = targt_arm.data.edit_bones.get(targt_bn_name)
					if targ_bn is not None:
						roll_donor = bone_rolls_donor[donor_bn_name]
						targ_bn.roll = roll_donor
				matrix_data[targt_bn_name] = [bone_quat[0], bone_quat[1], bone_quat[2], bone_quat[3]]
			else:
				bones_err = bones_err+1

		# applying rotation_quaternion to target armature
		select_and_change_mode(targt_arm,"POSE")
		for bnn in bones_names_targ:
			if bnn in matrix_data:
				bone = targt_arm.pose.bones.get(bnn)
				bone.rotation_mode = 'QUATERNION'
				bone.rotation_quaternion = mathutils.Quaternion(matrix_data[bnn])
		select_and_change_mode(targt_arm,"OBJECT")
		self.report({'INFO'}, "Pose transferred, bones="+str(bones_ok)+", skipped="+str(bones_err))
		return {'FINISHED'}

class wplPosingSettings(PropertyGroup):
	mbArmatName = StringProperty(
		name="",
		description="Target Armature (MB)",
		default="human_skeleton")

class WPLPosingSt_Panel(bpy.types.Panel):
	bl_label = "DAZ armature -> MB skeleton"
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
		bakeOpts = context.scene.wplPosingSettings

		# display the properties
		col = layout.column()
		col.prop_search(bakeOpts, "mbArmatName", scene, "objects")
		col.operator("mesh.wplposing_arm2mbp", text="DAZ -> MB")
		col.separator()
		col.operator("mesh.wplposing_unrollclon", text="Reset Armature Roll")

def register():
	print("WPLPosingSt_Panel registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wplPosingSettings = PointerProperty(type=wplPosingSettings)

def unregister():
	del bpy.types.Scene.wplPosingSettings
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
