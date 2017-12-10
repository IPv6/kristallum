# Baking scene object into OSL script for later use in material nodes

# Used resources:
# https://blender.stackexchange.com/questions/27491/python-vertex-normal-according-to-world
import bpy
import bmesh
import math
import mathutils
from mathutils import Vector
from random import random, seed
from bpy_extras import view3d_utils
from bpy_extras.object_utils import world_to_camera_view
from datetime import datetime

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
	"name": "WPL Removed stuff",
	"author": "IPv6",
	"version": (1, 0, 0),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > WPL",
	"description" : "",
	"warning"	 : "",
	"wiki_url"	: "",
	"tracker_url" : "",
	"category"	: ""
	}
	
	
# class WPLbake_shpk_to_vc(bpy.types.Operator):
	# bl_idname = "object.wplbake_shpk_to_vc"
	# bl_label = "VC: Bake shapekey diff"
	# bl_options = {'REGISTER', 'UNDO'}

	# opt_r_infl = bpy.props.FloatProperty(
		# name		= "R: Positive shift influence",
		# min			= 0.0, max = 1000,
		# default	 	= 100.0
		# )
	# opt_b_infl = bpy.props.FloatProperty(
		# name		= "B: Negative shift influence",
		# min			= 0.0, max = 1000,
		# default	 	= 100.0
		# )
	# opt_g_infl = bpy.props.FloatProperty(
		# name		= "G: Normals influence",
		# min			= 0.0, max = 100,
		# default	 	= 1.0
		# )

	# @classmethod
	# def poll(self, context):
		# p = context.object and context.object.data and (isinstance(context.scene.objects.active, bpy.types.Object) and isinstance(context.scene.objects.active.data, bpy.types.Mesh))
		# return p

	# def execute(self, context):
		# print("execute ", self.bl_idname)
		# active_object = context.scene.objects.active
		# if active_object is None or active_object.data is None:
			# return {'CANCELLED'}
		# active_mesh = active_object.data
		# bpy.ops.object.mode_set(mode='OBJECT')
		# selectedVertsIdx = [v.index for v in active_mesh.vertices if v.select]
		# if len(selectedVertsIdx) < 3:
			# self.report({'ERROR'}, "Not enough selected vertices found")
			# return {'CANCELLED'}
		# active_object.data.use_paint_mask = True
		# vc_bakeOpts = context.scene.vc_bakeOpts
		# color_map = active_mesh.vertex_colors.get(vc_bakeOpts.bake_vcnm)
		# if color_map is None:
			# self.report({'ERROR'}, "Target VC not found")
			# return {'CANCELLED'}
		# shpk1 = active_mesh.shape_keys.key_blocks[vc_bakeOpts.bake_shk1]
		# shpk2 = active_mesh.shape_keys.key_blocks[vc_bakeOpts.bake_shk2]
		# if shpk1 is None or shpk2 is None:
			# self.report({'ERROR'}, "One of shapekeys not found")
			# return {'CANCELLED'}
		# for poly in active_mesh.polygons:
			# for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
				# vi = active_mesh.loops[loop_index].vertex_index
				# if (vi in selectedVertsIdx):
					# co1 = shpk1.data[vi].co
					# co2 = shpk2.data[vi].co
					# distP = (co1-co2).length
					# distN = distP
					# ndir = active_mesh.vertices[vi].normal.dot((co2-co1).normalized())
					# if ndir<=0:
						# distP = 0
					# else:
						# distN = 0
					# color_map.data[loop_index].color = (distP*self.opt_r_infl,abs(ndir*self.opt_g_infl),distN*self.opt_b_infl,1.0)
		# context.scene.update()
		# bpy.ops.object.mode_set(mode='VERTEX_PAINT')
		# return {'FINISHED'}
		

# class WPLbridge_mesh_islands( bpy.types.Operator ):
# 	# Operator get all selected faces, extracts bounds and then make faces BETWEEN mesh-selection islands, basing on distance between vertices
# 	bl_idname = "mesh.wplbridge_mesh_islands"
# 	bl_label = "Bridge edges of selected islands"
# 	bl_options = {'REGISTER', 'UNDO'}
# 	opt_flatnFac = bpy.props.FloatProperty(
# 		name		= "Minimal distance",
# 		description = "Distance to merge",
# 		default	 = 0.3,
# 		min		 = 0,
# 		max		 = 100
# 		)
#
# 	@classmethod
# 	def poll( cls, context ):
# 		return ( context.object is not None  and
# 				context.object.type == 'MESH' )
#
# 	def execute( self, context ):
# 		active_object = context.scene.objects.active
# 		active_mesh = active_object.data
# 		selvertsAll = get_selected_vertsIdx(active_mesh)
# 		bpy.ops.object.mode_set( mode = 'EDIT' )
# 		bpy.ops.mesh.region_to_loop()
# 		selvertsBnd = get_selected_vertsIdx(active_mesh)
# 		seledgesBnd = get_selected_edgesIdx(active_mesh)
# 		if len(seledgesBnd) == 0:
# 			self.report({'ERROR'}, "No bounds found")
# 			#print("All: ",selvertsAll," outer:", selvertsBnd)
# 			return {'CANCELLED'}
# 		bpy.ops.object.mode_set( mode = 'EDIT' )
# 		bm = bmesh.from_edit_mesh(active_mesh)
# 		bm.verts.ensure_lookup_table()
# 		bm.faces.ensure_lookup_table()
# 		bm.verts.index_update()
# 		islandVerts = {}
# 		islandNum = 1
# 		for v in bm.verts:
# 			if v.tag == False:
# 				meshlist = []
# 				add_connected_bmverts(v,meshlist,selvertsAll)
# 				for vv in meshlist:
# 					islandVerts[vv.index] = islandNum
# 				islandNum = islandNum+1
# 		if islandNum < 3:
# 			self.report({'ERROR'}, "No islands found, need at least 2 islands")
# 			#print("All: ",selvertsAll," outer:", selvertsBnd)
# 			return {'CANCELLED'}
# 		#nearest vertices for each boundary vertice
# 		for v in bm.verts:
# 			v.tag = False
# 		islandVertsUsed = {}
# 		for isl1 in range(1,islandNum):
# 			for isl2 in range(1,islandNum):
# 				if isl1 != isl2:
# 					hull_edges = []
# 					for bndIdx1 in selvertsBnd:
# 						if islandVerts[bndIdx1] == isl1 and bndIdx1 not in islandVertsUsed:
# 							bndV1 = bm.verts[bndIdx1]
# 							bndNearest = None
# 							bndNearestDist = 99999
# 							for bndIdx2 in selvertsBnd:
# 								if islandVerts[bndIdx2] == isl2:#!!! and bndIdx2 not in islandVertsUsed:
# 									bndV2 = bm.verts[bndIdx2]
# 									dst = (bndV2.co-bndV1.co).length
# 									if dst < self.opt_flatnFac and dst < bndNearestDist:
# 										bndNearestDist = dst
# 										bndNearest = bndV2
# 							if bndNearest is not None:
# 								# selecting edges
# 								islandVertsUsed[bndIdx1]=bndIdx2
# 								islandVertsUsed[bndIdx2]=bndIdx1
# 								verts2join = []
# 								verts2join.append(bndV1)
# 								verts2join.append(bndNearest)
# 								crtres = bmesh.ops.contextual_create(bm, geom=verts2join)
# 								hull_edges.extend(crtres["edges"])
# 								hull_edges.extend(bndV1.link_edges)
# 								hull_edges.extend(bndNearest.link_edges)
# 					hull_edges_pack = list(set(hull_edges))
# 					if len(hull_edges_pack)>2:
# 						bmesh.ops.holes_fill(bm, edges=hull_edges_pack,sides=4)
# 						#bmesh.ops.edgeloop_fill(bm, edges=hull_edges)
# 						#bmesh.ops.bridge_loops(bm, edges=hull_edges)
# 						#bmesh.ops.contextual_create(bm, geom=(edg1,edg2))
# 		bmesh.update_edit_mesh(active_mesh)
# 		bm.free()
# 		return {'FINISHED'}

# class WPLuv_flatten( bpy.types.Operator ):
	# bl_idname = "mesh.wpluv_flatten"
	# bl_label = "Flatten toward active UVMap"
	# bl_options = {'REGISTER', 'UNDO'}
	# opt_flatnFac = bpy.props.FloatProperty(
		# name		= "Flatness",
		# description = "Flatness applied",
		# default	 = 1.0,
		# min		 = -100,
		# max		 = 100
		# )

	# @classmethod
	# def poll( cls, context ):
		# return ( context.object is not None  and
				# context.object.type == 'MESH' )

	# def execute( self, context ):
		# active_object = context.scene.objects.active
		# active_mesh = active_object.data
		# active_uvmap = active_mesh.uv_textures.active
		# selvertsAll = get_selected_vertsIdx(active_mesh)
		# bpy.ops.object.mode_set( mode = 'EDIT' )
		# if len(selvertsAll) == 0:
			# self.report({'ERROR'}, "No inner vertices found")
			# return {'CANCELLED'}
		# if active_uvmap is None:
			# self.report({'ERROR'}, "No active UVMap found, unwrap mesh first")
			# return {'CANCELLED'}

		# bm = bmesh.from_edit_mesh(active_mesh)
		# bm.verts.ensure_lookup_table()
		# bm.faces.ensure_lookup_table()
		# bm.verts.index_update()
		# uv_layer = bm.loops.layers.uv.verify()
		# bm.faces.layers.tex.verify()  # currently blender needs both layers.
		##sorting vertex list on Z coord
		# selvertsAll = sorted(selvertsAll, key=lambda plt: (-active_mesh.vertices[plt].co[2]))
		# anchor_vertIdx = selvertsAll[0]
		# anchor_p1 = mathutils.Vector((1,0,0))
		# anchor_p2 = mathutils.Vector((0,1,0))
		# for elem in reversed(bm.select_history):
			# if isinstance(elem, bmesh.types.BMFace):
				# anchor_vertIdx = elem.verts[0].index
				# facen = elem.normal
				# if facen.dot(mathutils.Vector((0,0,1))) > 0.99:
					# anchor_p1 = facen.cross(mathutils.Vector((1,0,0)))
				# else:
					# anchor_p1 = facen.cross(mathutils.Vector((0,0,1)))
				# anchor_p2 = facen.cross(anchor_p1)
				# tmp = anchor_p2
				# anchor_p2 = anchor_p1
				# anchor_p1 = -tmp
				# break
			# if isinstance(elem, bmesh.types.BMVert):
				# anchor_vertIdx = elem.index
				# break
		# first_co = active_mesh.vertices[anchor_vertIdx].co
		# first_uv = mathutils.Vector((0,0))
		##searching for first_co_uv
		# for face in bm.faces:
			# for loop in face.loops:
				# vert = loop.vert
				# if vert.index == anchor_vertIdx:
					# first_uv = loop[uv_layer].uv
		# for face in bm.faces:
			# for loop in face.loops:
				# vert = loop.vert
				# if (vert.index in selvertsAll):
					# rel_uv = loop[uv_layer].uv - first_uv
					# new_co = first_co+anchor_p1*rel_uv[0]+anchor_p2*rel_uv[1]
					# vert.co = vert.co.lerp(new_co,self.opt_flatnFac)
					# selvertsAll.remove(vert.index) #to avoid double-effect when vert in several loops
		# bmesh.update_edit_mesh(active_mesh)
		# return {'FINISHED'}

class WPLVCBakeSettings(PropertyGroup):
	bake_uvbase = StringProperty(
		name="Target UV",
		description="Bake into set of UVMaps",
		default = "Eye_XZ"
		)
	bake_vcnm = StringProperty(
		name="Target VC",
		description="Target VC",
		default = ""
		)
	# bake_shk1 = StringProperty(
		# name="Base shapekey",
		# description="Base shapekey",
		# default = ""
		# )
	# bake_shk2 = StringProperty(
		# name="Diff shapekey",
		# description="Diff shapekey",
		# default = ""
		# )
		
class WPLBakeMeshFeatures_Panel2(bpy.types.Panel):
	bl_label = "UV/VC bake"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw(self, context):
		layout = self.layout
		vc_bakeOpts = context.scene.vc_bakeOpts
		active_object = context.scene.objects.active
		col = layout.column()
		if active_object is not None and active_object.data is not None:
			#col.operator("mesh.wplbridge_mesh_islands", text="Bridge islands")
			#col.operator("mesh.wpluv_flatten", text="UV-flatten")
			obj_data = active_object.data
			if obj_data is not None:
				col.prop_search(vc_bakeOpts, "bake_vcnm", obj_data, "vertex_colors", icon='GROUP_VCOL')
				# shape_keys_d = active_object.data.shape_keys
				# if shape_keys_d is not None:
					# col.separator()
					# col.label("VC: Shapekey diffs")
					# col.prop_search(vc_bakeOpts, "bake_shk1", shape_keys_d, "key_blocks", icon='SHAPEKEY_DATA')
					# col.prop_search(vc_bakeOpts, "bake_shk2", shape_keys_d, "key_blocks", icon='SHAPEKEY_DATA')
					# col.operator("object.wplbake_shpk_to_vc", text="Bake Shapekey diff")
		
def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.vc_bakeOpts = PointerProperty(type=WPLVCBakeSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	del bpy.types.Scene.vc_bakeOpts
	bpy.utils.unregister_class(WPLVCBakeSettings)

if __name__ == "__main__":
	register()
