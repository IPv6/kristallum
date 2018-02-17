import math
import copy
import random
import mathutils
import numpy as np

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix

bl_info = {
	"name": "WPL Node helpers",
	"author": "IPv6",
	"version": (0, 0, 1),
	"location": "View 3D > Node Editor > Menu",
	"blender": (2, 7, 9),
	"description": "Adds hierarchical submenus for groups",
	"warning": "",
	"category": "Node",
	}

kWPL_HierarchyChar = '_'
class WPL_Gnt:
	ngstore = {}

######################### ######################### #########################
######################### ######################### #########################
class NODEVIEW_MT_WPL_Groups(bpy.types.Menu):
	bl_label = "WPL Groups"
	bl_idname = "NODEVIEW_MT_WPL_Groups"
	
	def draw(self, context):
		nameFilter = ""
		try:
			nameFilter = context.hier.value
		except:
			pass
		layout = self.layout
		all_ngroups = bpy.data.node_groups
		all_ngroups_mtt = []
		next_hiercounts = {}
		for ng in all_ngroups:
			ui_name = ng.name
			if ng.type != 'SHADER':
				# ignoring compositing, etc nodes
				continue
			if ng.library is not None:
				ui_name = "L: "+ng.name
			if len(nameFilter) > 0 and not ui_name.startswith(nameFilter):
				continue
			bpy.types.WindowManager.ngstore[ui_name] = ng
			
			ui_name_nofil = ui_name
			if len(nameFilter) > 0:
				ui_name_nofil = ui_name_nofil.replace(nameFilter,"")
			ng_hier = ui_name_nofil.split(kWPL_HierarchyChar)
			ng_hier_str = ""
			if len(ng_hier)>0:
				ng_hier_str = nameFilter+ng_hier[0]+kWPL_HierarchyChar
			if ng_hier_str not in next_hiercounts:
				next_hiercounts[ng_hier_str] = 0
			next_hiercounts[ng_hier_str] = next_hiercounts[ng_hier_str]+1
			item = {"item": ng, "ui_name": ui_name, "hier": ng_hier_str}
			all_ngroups_mtt.append(item)
		all_ngroups_mtt = sorted(all_ngroups_mtt, key=lambda k: k["ui_name"])
		
		if len(nameFilter) == 0:
			n_op_start = layout.operator("node.add_node", text = "Frame")
			n_op_start.type = "NodeFrame"
			n_op_start.use_transform = True
			n_op_start = layout.operator("node.add_node", text = "Reroute")
			n_op_start.type = "NodeReroute"
			n_op_start.use_transform = True
		else:
			n_op_start = layout.operator("node.add_node", text = nameFilter+"...")
			n_op_start.type = "NodeReroute"
			n_op_start.use_transform = True
		layout.separator()
		for item in all_ngroups_mtt:
			ng = item["item"]
			ng_ui = item["ui_name"]
			ng_hier = item["hier"]
			if len(ng_hier) == 0 or next_hiercounts[ng_hier] < 2:
				n_op = layout.operator("node.add_node", text = ng_ui) #bpy.ops.node.add_node
				n_op.type = "ShaderNodeGroup"
				n_op.use_transform = True
				n_op_set = n_op.settings.add()
				n_op_set.name = "node_tree"
				# !!!-->> not using node name here! Local and Library items can have EXACT THE SAME NAME <<--!!!
				n_op_set.value = "bpy.types.WindowManager.ngstore['"+ng_ui+"']" #"bpy.data.node_groups['"+item.name+"']"
			else:
				if next_hiercounts[ng_hier] < 999:
					next_hiercounts[ng_hier] = 999
					row = layout.row()
					n_op_set2 = n_op_start.settings.add()
					n_op_set2.name = "hier_"+ng_ui
					n_op_set2.value = ng_hier
					row.context_pointer_set("hier", n_op_set2)
					row.menu("NODEVIEW_MT_WPL_Groups", text = item["hier"]+"...")


######################### ######################### #########################
######################### ######################### #########################
class NODEVIEW_MT_WPL_Menu(bpy.types.Menu):
	bl_label = "WPL Groups"

	@classmethod
	def poll(cls, context):
		space = context.space_data
		#tree_type = context.space_data.tree_type
		return space.type == 'NODE_EDITOR' and space.tree_type == 'ShaderNodeTree'

	def draw(self, context):
		tree_type = context.space_data.tree_type
		if not tree_type in "ShaderNodeTree":
			return

		layout = self.layout
		layout.operator_context = 'INVOKE_REGION_WIN'
		layout.menu(NODEVIEW_MT_WPL_Groups.bl_idname)

def register():
	bpy.utils.register_module(__name__)
	try:
		ngstore = bpy.types.WindowManager.ngstore
	except:
		bpy.types.NODE_MT_add.append(bpy.types.NODEVIEW_MT_WPL_Menu.draw)
		bpy.types.WindowManager.ngstore = WPL_Gnt.store

def unregister():
	bpy.utils.unregister_module(__name__)
	try:
		ngstore = bpy.types.WindowManager.ngstore
		del bpy.types.WindowManager.ngstore
		bpy.types.NODE_MT_add.remove(bpy.types.NODEVIEW_MT_WPL_Menu.draw)
	except:
		pass

if __name__ == "__main__":
	register()