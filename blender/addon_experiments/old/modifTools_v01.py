import math
import copy
import mathutils
import time
import random
from mathutils import kdtree
from random import random, seed
import numpy as np
import datetime

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

bl_info = {
	"name": "WPL Armature tools",
	"author": "IPv6",
	"version": (1, 0, 0),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": ""}

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
def select_and_change_mode(obj, obj_mode):
	#print("select_and_change_mode",obj_mode)
	m = bpy.context.mode
	if obj_mode == "EDIT_MESH" or  obj_mode == "EDIT_CURVE":
		obj_mode = "EDIT"
	if obj_mode == "PAINT_VERTEX":
		obj_mode = "VERTEX_PAINT"
	if (obj is not None and bpy.context.scene.objects.active != obj) or m != 'OBJECT':
		# stepping out from currently active object mode, or switch may fail
		bpy.ops.object.mode_set(mode='OBJECT')
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

def copyBpyStructFields(bpyFrom, bpyTo, fieldsCopy, filedSkip):
	print("copyBpyStructFields", bpyFrom, bpyTo)
	if bpyTo is None:
		return
	if isinstance(bpyFrom,dict):
		bpyFromDirItems = bpyFrom.keys()
	else:
		bpyFromDirItems = dir(bpyFrom)
	for property in bpyFromDirItems:
		#print("copyBpyStructFields",property)
		if "__" in property:
			continue
		inPropChanged = 0
		if filedSkip is not None:
			for fld in filedSkip:
				if fld in property:
					inPropChanged = -1
					break
		if inPropChanged >= 0:
			for fld in fieldsCopy:
				if (fld in property):
					if isinstance(bpyFrom,dict):
						val = bpyFrom[property]
					else:
						val = getattr(bpyFrom,property)
					if val is None or isinstance(val, str) or isinstance(val, int) or isinstance(val, float) or isinstance(val, bool) or isinstance(val, bpy.types.Object):
						#print("- updating field",property,"to",val)
						if isinstance(bpyTo,dict):
							bpyTo[property] = val
						else:
							setattr(bpyTo, property, val)
						inPropChanged = inPropChanged+1
						break
					#else:
					#	print("- skipping by type",type(val))
		if inPropChanged <= 0:
			print("- skipping field",property)
########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class wplposing_ar_toggle( bpy.types.Operator ):
	bl_idname = "object.wplposing_ar_toggle"
	bl_label = "Toggle"
	bl_options = {'REGISTER', 'UNDO'}

	opt_postAction = EnumProperty(
		name="Action", default="XRAY",
		items=(("XRAY", "X-Ray", ""), ("LAYER", "Layer", ""), ("REST", "Rest/Pose", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		def boneLayers(l,mx):
			all = [False]*mx
			all[l]=True
			return all
		scene = context.scene
		armatr = context.scene.objects.active
		if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		if self.opt_postAction == "XRAY":
			armatr.show_x_ray = not armatr.show_x_ray
		if self.opt_postAction == "REST":
			if armatr.data.pose_position == 'REST':
				armatr.data.pose_position = 'POSE'
			else:
				armatr.data.pose_position = 'REST'
		if self.opt_postAction == "LAYER":
			curVis = 0
			maxLrs = 0 #len(armatr.data.layers)
			for bone in armatr.data.bones:
				for i,l in enumerate(bone.layers):
					if l and i > maxLrs:
						maxLrs = i
						break
			for i,l in enumerate(armatr.data.layers):
				if l:
					curVis = i
					break
			armatr.data.layers = boneLayers((curVis+1)%(maxLrs+1),len(armatr.data.layers))
		select_and_change_mode(armatr,'POSE')
		return {'FINISHED'}


# class wplposing_bn_boneenvs( bpy.types.Operator ):
# 	bl_idname = "object.wplposing_bn_boneenvs"
# 	bl_label = "Set bones envelopes"
# 	bl_options = {'REGISTER', 'UNDO'}
#
# 	opt_envelopeDist = FloatProperty(
# 		name = "Full distance",
# 		min = 0.0, max = 100.0,
# 		default = 0.0
# 	)
# 	opt_envelopeHard = FloatProperty(
# 		name = "Hard distance",
# 		min = 0.0, max = 1.0,
# 		default = 0.3
# 	)
#
# 	@classmethod
# 	def poll( cls, context ):
# 		p = (isinstance(context.scene.objects.active, bpy.types.Object))
# 		return p
#
# 	def execute( self, context ):
# 		if bpy.context.mode != 'EDIT_ARMATURE':
# 			self.report({'ERROR'}, "Works in EDIT mode only ("+bpy.context.mode+")")
# 			return {'CANCELLED'}
# 		scene = context.scene
# 		armaob = context.scene.objects.active
# 		if armaob is None or not isinstance(armaob.data, bpy.types.Armature):
# 			self.report({'ERROR'}, "Works on Armature only")
# 			return {'CANCELLED'}
# 		armatAR = bpy.data.armatures.get(armaob.data.name)
# 		boneNames = armaob.pose.bones.keys()
# 		select_and_change_mode(armaob,'EDIT')
# 		boneSelected = []
# 		for boneName in boneNames:
# 			bone = armatAR.edit_bones.get(boneName)
# 			if bone.select:
# 				boneSelected.append(boneName)
# 		okBones = 0
# 		for boneName in boneSelected:
# 			eb = armatAR.edit_bones.get(boneName)
# 			eb.head_radius = self.opt_envelopeDist*self.opt_envelopeHard
# 			eb.tail_radius = self.opt_envelopeDist*self.opt_envelopeHard
# 			eb.envelope_distance = self.opt_envelopeDist
# 			okBones = okBones+1
# 		self.report({'INFO'}, "Handled "+str(okBones)+" bones")
# 		return {'FINISHED'}


class wplposing_bn_hideunsel( bpy.types.Operator ):
	bl_idname = "object.wplposing_bn_hideunsel"
	bl_label = "Hide unselected"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		if bpy.context.mode != 'POSE':
			self.report({'ERROR'}, "Works in POSE mode only")
			return {'CANCELLED'}
		scene = context.scene
		armatr = context.scene.objects.active
		if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		#bpy.ops.pose.select_all(action='INVERT')
		bpy.ops.pose.hide(unselected=True)
		return {'FINISHED'}

class wplposing_bn_resetmods( bpy.types.Operator ):
	bl_idname = "object.wplposing_bn_resetmods"
	bl_label = "Reset mods"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		if bpy.context.mode != 'POSE':
			self.report({'ERROR'}, "Works in POSE mode only")
			return {'CANCELLED'}
		scene = context.scene
		armatr = context.scene.objects.active
		if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		boneNames = armatr.pose.bones.keys()
		okBones = 0;
		for boneName in boneNames:
			bone = armatr.data.bones[boneName]
			if bone.select:
				pbone = armatr.pose.bones[boneName]
				pbone.rotation_mode = "ZYX"
				okBones = okBones+1
		self.report({'INFO'}, "Handled "+str(okBones)+" bones")
		return {'FINISHED'}

class wplposing_bn_applyconstr( bpy.types.Operator ):
	bl_idname = "object.wplposing_bn_applyconstr"
	bl_label = "Apply constraints"
	bl_options = {'REGISTER', 'UNDO'}

	opt_postAction = EnumProperty(
		name="Action", default="CLEAR",
		items=(("CLEAR", "Drop constraints", ""), ("DISABLE", "Disable constraints", ""), ("ENABLE", "Enable constraints", ""))
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		if bpy.context.mode != 'POSE':
			self.report({'ERROR'}, "Works in POSE mode only")
			return {'CANCELLED'}
		scene = context.scene
		armatr = context.scene.objects.active
		if armatr is None or not isinstance(armatr.data, bpy.types.Armature):
			self.report({'ERROR'}, "Works on Armature only")
			return {'CANCELLED'}
		if self.opt_postAction != "ENABLE":
			bpy.ops.pose.visual_transform_apply()
		boneNames = armatr.pose.bones.keys()
		okBones = 0
		for boneName in boneNames:
			bone = armatr.data.bones[boneName]
			if bone.select:
				pbone = armatr.pose.bones[boneName]
				if len(pbone.constraints) > 0:
					constrs = []
					for constr in pbone.constraints:
						constrs.append(constr)
					for constr in constrs:
						okBones = okBones+1
						if self.opt_postAction == "CLEAR":
							pbone.constraints.remove(constr)
						if self.opt_postAction == "DISABLE":
							constr.mute = True
						if self.opt_postAction == "ENABLE":
							constr.mute = False
		self.report({'INFO'}, "Handled "+str(okBones)+" bones")
		return {'FINISHED'}

class wplprops_applytransf( bpy.types.Operator ):
	bl_idname = "object.wplprops_applytransf"
	bl_label = "Finalize objects"
	bl_options = {'REGISTER', 'UNDO'}
	opt_applyConstrs = bpy.props.BoolProperty(
		name		= "Remove constraints (if any)",
		default	 = True
		)
	opt_applyMirror = bpy.props.BoolProperty(
		name		= "Apply mirror (if any)",
		default	 = True
		)
	opt_applyArmat = bpy.props.BoolProperty(
		name		= "Apply armature (if any)",
		default	 = True
		)
	opt_applyHooks = bpy.props.BoolProperty(
		name		= "Apply hooks (if any)",
		default	 = True
		)

	@classmethod
	def poll( cls, context ):
		return ( context.object is not None)

	def execute( self, context ):
		sel_all = [o.name for o in bpy.context.selected_objects]
		if len(sel_all) == 0:
			self.report({'ERROR'}, "No objects selected")
			return {'CANCELLED'}
		changesCount = 0
		for i, sel_obj_name in enumerate(sel_all):
			active_obj = context.scene.objects.get(sel_obj_name)
			if active_obj.data.shape_keys is not None and len(active_obj.data.shape_keys.key_blocks):
				self.report({'ERROR'}, "Some objects has shapekeys: "+active_obj.name)
				return {'CANCELLED'}
		for i, sel_obj_name in enumerate(sel_all):
			active_obj = context.scene.objects.get(sel_obj_name)
			select_and_change_mode(active_obj,"OBJECT")
			if self.opt_applyConstrs == True and len(active_obj.constraints)>0:
				bpy.ops.object.visual_transform_apply()
				for c in active_obj.constraints:
					active_obj.constraints.remove(c)
			try:
				applMods = []
				changeOrigin = True
				for md in active_obj.modifiers:
					if self.opt_applyHooks == True and md.type == 'HOOK':
						applMods.append(md.name)
					if self.opt_applyHooks == True and md.type == 'MESH_DEFORM':
						applMods.append(md.name)
					if self.opt_applyHooks == True and md.type == 'LATTICE':
						applMods.append(md.name)
					if self.opt_applyHooks == True and md.type == 'SURFACE_DEFORM' and active_obj.type == 'MESH':
						applMods.append(md.name)
					if self.opt_applyMirror == True and md.type == 'MIRROR' and active_obj.type == 'MESH':
						applMods.append(md.name)
					if self.opt_applyArmat == True and md.type == 'CORRECTIVE_SMOOTH' and active_obj.type == 'MESH':
						applMods.append(md.name)
					if self.opt_applyArmat == True and md.type == 'ARMATURE':
						applMods.append(md.name)
				for mdname in applMods:
					md = active_obj.modifiers.get(mdname)
					bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mdname)
				changesCount = changesCount+1
			except:
				pass
		self.report({'INFO'}, "Objects updated: "+str(changesCount)+" of "+str(len(sel_all)))
		return {'FINISHED'}

class wplprops_stepphysics( bpy.types.Operator ):
	bl_idname = "object.wplprops_stepphysics"
	bl_label = "Step and Apply physics"
	bl_options = {'REGISTER', 'UNDO'}

	opt_framesToSim = IntProperty(
		name = "Frames",
		default = 10
	)

	@classmethod
	def poll( cls, context ):
		p = (isinstance(context.scene.objects.active, bpy.types.Object))
		return p

	def execute( self, context ):
		active_obj = context.scene.objects.active
		if active_obj is None:
			self.report({'ERROR'}, "No active object found")
			return {'CANCELLED'}
		active_mesh = active_obj.data
		cur_frame = context.scene.frame_current
		end_frame = cur_frame+self.opt_framesToSim
		print("Saving modifiers...")
		phys_mod = None
		phys_mod_params = {}
		for md in active_obj.modifiers:
			if md.type == 'CLOTH':
				phys_mod = md
				phys_mod_params["name"] = phys_mod.name
				phys_mod_params["type"] = phys_mod.type
				phys_mod_params["settings"] = {}
				phys_mod_params["settings_list"] = ["damping","stiffness","friction","density","goal","gravity","mass","quality","rest_shape_key","force","shrink","time_scale","use","group","voxel_cell_size"]
				phys_mod_params["collision_settings"] = {}
				phys_mod_params["collision_settings_list"] = ["collision","distance","self","use","damping","friction","group","repel_force"]
				phys_mod_params["effector_weights"] = {}
				phys_mod_params["effector_weights_list"] = ["all","apply","boid","charge","curve_guide","drag","force","gravity","group","harmonic","lennardjones","magnetic","smokeflow","texture","turbulence","vortex","wind"]
				copyBpyStructFields(phys_mod.settings, phys_mod_params["settings"], phys_mod_params["settings_list"],None) #["effector_weights"]
				copyBpyStructFields(phys_mod.collision_settings, phys_mod_params["collision_settings"], phys_mod_params["collision_settings_list"], None)
				copyBpyStructFields(phys_mod.settings.effector_weights, phys_mod_params["effector_weights"], phys_mod_params["effector_weights_list"], None)
				break
			if md.type == 'SOFT_BODY':
				phys_mod = md
				phys_mod_params["name"] = phys_mod.name
				phys_mod_params["type"] = phys_mod.type
				phys_mod_params["settings"] = {}
				phys_mod_params["settings_list"] = ["aero","aerodynamics_type","ball","bend","choke","collision","damping","error_threshold","friction","fuzzy","goal","gravity","mass","plastic","pull","push","estimate","shear","speed","spring","step","use","vertex"]
				phys_mod_params["effector_weights"] = {}
				phys_mod_params["effector_weights_list"] = ["all","apply","boid","charge","curve_guide","drag","force","gravity","group","harmonic","lennardjones","magnetic","smokeflow","texture","turbulence","vortex","wind"]
				copyBpyStructFields(phys_mod.settings, phys_mod_params["settings"], phys_mod_params["settings_list"], None)
				copyBpyStructFields(phys_mod.settings.effector_weights, phys_mod_params["effector_weights"], phys_mod_params["effector_weights_list"], None)
				break
		if phys_mod is not None:
			print("Baking physics... ","-frames:",(end_frame-cur_frame),"-time:",datetime.datetime.now())
			bpy.context.scene.frame_set(cur_frame)
			phys_mod.point_cache.frame_start = cur_frame
			phys_mod.point_cache.frame_end = end_frame
			bpy.ops.ptcache.bake_all(bake=True)
			print("Baking done!... ","-time:",datetime.datetime.now())
		print("Switching frame...")
		bpy.context.scene.frame_set(end_frame)
		bpy.context.scene.update()
		if phys_mod is not None:
			#if phys_mod.type == 'CLOTH':
			#bpy.ops.object.convert(target='MESH', keep_original=False)
			#if phys_mod.type == 'SOFT_BODY':
			bpy.ops.object.modifier_apply(apply_as='DATA', modifier=phys_mod.name)
		else:
			bpy.ops.object.convert(target='MESH', keep_original=False)
		new_mat = active_obj.matrix_world
		print("Going back...")
		bpy.context.scene.frame_set(cur_frame)
		bpy.context.scene.update()
		print("Restoring modifiers...")
		active_obj.matrix_world = new_mat
		if phys_mod is not None:
			newphys_modifier = active_obj.modifiers.new(phys_mod_params["name"], phys_mod_params["type"])
			if phys_mod_params["type"] == 'CLOTH':
				copyBpyStructFields(phys_mod_params["settings"], newphys_modifier.settings, phys_mod_params["settings_list"], None) #["effector_weights"]
				copyBpyStructFields(phys_mod_params["collision_settings"], newphys_modifier.collision_settings, phys_mod_params["collision_settings_list"], None)
				copyBpyStructFields(phys_mod_params["effector_weights"], newphys_modifier.settings.effector_weights, phys_mod_params["effector_weights_list"], None)
			if phys_mod_params["type"] == 'SOFT_BODY':
				copyBpyStructFields(phys_mod_params["settings"], newphys_modifier.settings, phys_mod_params["settings_list"], None)
				copyBpyStructFields(phys_mod_params["effector_weights"], newphys_modifier.settings.effector_weights, phys_mod_params["effector_weights_list"], None)
			bpy.ops.ptcache.free_bake_all()
		print("Done!")
		return {'FINISHED'}

########### ############ ########### ############ ########### ############ ########### ############
########### ############ ########### ############ ########### ############ ########### ############
class WPLArmaTools_Panel1(bpy.types.Panel):
	bl_label = "Modf tools"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		col = layout.column()
		box1 = col.box()
		box1.label("Armature")
		box1.operator("object.wplposing_ar_toggle", text="Toggle Layer").opt_postAction = 'LAYER'
		box1.operator("object.wplposing_ar_toggle", text="Toggle Rest/Pose").opt_postAction = 'REST'
		box1.separator()
		box1.operator("object.wplposing_ar_toggle", text="Toggle X-Ray").opt_postAction = 'XRAY'
		col.separator()
		box2 = col.box()
		box2.label("Selected Bones")
		box2.operator("object.wplposing_bn_applyconstr", text="Disable constraints").opt_postAction = 'DISABLE'
		box2.operator("object.wplposing_bn_applyconstr", text="Enable constraints").opt_postAction = 'ENABLE'
		row1 = box2.row()
		box2.operator("object.wplposing_bn_resetmods", text="Reset to ZYX")
		box2.operator("object.wplposing_bn_hideunsel", text="Hide unselected")
		#box2.operator("object.wplposing_bn_boneenvs", text="Set envelops")
		box2.separator()
		box2.operator("object.wplposing_bn_applyconstr", text="Drop constraints").opt_postAction = 'CLEAR'
		col.separator()
		box3 = col.box()
		box3.label("Selected objects")
		box3.operator("object.wplprops_applytransf")
		box3.separator()
		box3.label("Physics")
		box3.operator("object.wplprops_stepphysics", text="Roll bpy-physics")

def register():
	print("WPLArmaTools_Panel1 register")
	bpy.utils.register_module(__name__)

def unregister():
	print("WPLArmaTools_Panel1 unregister")
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
