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
	"name": "Welder",
	"author": "Łukasz Hoffmann",
	"version": (0,0, 3),
	"location": "View 3D > Object Mode > Tool Shelf",
	"blender": (2, 7, 9),
	"description": "Generate weld along the edge of intersection of two objects",
	"warning": "",
	"category": "Object",
	}

kWPLSystemEmpty = "zzz"
kWPLWeldMods = "Weld"
######################### ######################### #########################
######################### ######################### #########################
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
		context.scene.update()
		if len(subname) > 0:
			empty.parent = getSysEmpty(context,"")
	return empty

######################### ######################### #########################
######################### ######################### #########################
class WPL_addweld(bpy.types.Operator):
	bl_idname = "mesh.add_weld"
	bl_label = "Weld selection"

	def execute(self, context):
		def is_inside(p, obj):
			max_dist = 1.84467e+19
			found, point, normal, face = obj.closest_point_on_mesh(p, max_dist)
			p2 = point-p
			v = p2.dot(normal)
			#print(v)
			return not(v < 0.0001)

		if len(bpy.context.selected_objects)<2:
			self.report({'INFO'}, 'Select two objects')
			return {"CANCELLED"}
		OBJ_WELD = None
		weldObjName = context.scene.wpl_weldOpts.weld_object
		if weldObjName in bpy.data.objects.keys():
			OBJ_WELD = bpy.data.objects[weldObjName]
		print("OBJ_WELD", weldObjName, OBJ_WELD)
		bpy.ops.object.transform_apply(location=True, rotation=True, scale=True) 
		OBJ1=bpy.context.selected_objects[0]
		matrix=OBJ1.matrix_world
		OBJ2=bpy.context.selected_objects[1]
		bpy.ops.object.duplicate()
		OBJ3=bpy.context.selected_objects[0]
		OBJ4=bpy.context.selected_objects[1]
		bool_two = OBJ1.modifiers.new(type="BOOLEAN", name=kWPLWeldMods+"_bool2")
		bool_two.object = OBJ2
		bool_two.operation = 'INTERSECT'
		bpy.context.scene.objects.active = OBJ1
		bpy.ops.object.modifier_apply(modifier=kWPLWeldMods+"_bool2")
		bpy.ops.object.select_all(action = 'DESELECT')
		OBJ2.select = True
		bpy.ops.object.delete()
		bpy.context.scene.objects.active = OBJ1
		OBJ1.select = True
		vertices1 = OBJ1.data.vertices
		#poczatek sprawdzania kolizji z pierwszym obiektem
		list=[]
		for v in vertices1:
			#print (is_inside(mathutils.Vector(v.co), OBJ3))
			#print (v.index)
			if (is_inside(mathutils.Vector(OBJ3.matrix_world*v.co), OBJ3)==True):
				list.append(v.index)
			if (is_inside(mathutils.Vector(OBJ4.matrix_world*v.co), OBJ4)==True):
				list.append(v.index)
			continue
		#print ("Koniec liczenia")
		
		bpy.ops.object.mode_set(mode = 'EDIT')
		bm1 = bmesh.from_edit_mesh(OBJ1.data)
		vertices2 = bm1.verts

		for vert in vertices2:
			vert.select=False
			continue
		 
		bm1.verts.ensure_lookup_table()	
		for vert2 in list:
			vertices2[vert2].select=True
		#koniec sprawdzania kolizji z pierwszym obiektem
		bpy.ops.mesh.delete(type='VERT') # usuwanie wierzcholkow
		bpy.ops.mesh.select_mode(type="EDGE")
		for f in bm1.faces:
			f.select=False
		#bpy.ops.mesh.delete(type='FACE') # usuwanie wierzcholkow 
		def search(mymesh):
			culprits=[]
			for e in mymesh.edges:
				e.select = False
				shared = 0
				for f in mymesh.faces:
					for vf1 in f.verts:
						if vf1 == e.verts[0]:
							for vf2 in f.verts:
								if vf2 == e.verts[1]:
									shared = shared + 1
				if (shared > 2):
					#Manifold
					culprits.append(e)
					e.select = True
				if (shared < 2):
					#Open
					culprits.append(e)
					e.select = True
			return culprits

		search(bm1)
		for f in bm1.edges:
			f.select=not f.select

		bpy.ops.mesh.delete(type='EDGE') # usuwanie wielokątow
		#POPRAWKA DO SKRYPTU MANIFOLD - USUWANIE TROJKATOW PRZY KRAWEDZIACH
		bpy.ops.mesh.select_mode(type="EDGE")

		for e in bm1.edges:
			e.select=False
			shared=0
			for v in e.verts:
				for ed in v.link_edges:
					shared=shared+1
			if (shared==6):
				e.select=True
		bpy.ops.mesh.delete(type='EDGE') # usuwanie wielokątow 

		for v in bm1.edges:
			v.select=True
		
		bpy.ops.object.mode_set(mode = 'OBJECT')
		_data = bpy.context.active_object.data
		edge_length = 0
		for edge in _data.edges:
			vert0 = _data.vertices[edge.vertices[0]].co
			vert1 = _data.vertices[edge.vertices[1]].co
			edge_length += (vert0-vert1).length

		#edge_length = '{:.6f}'.format(edge_length)
		OBJ1.name = kWPLWeldMods+OBJ1.name
		OBJ1.parent = getSysEmpty(context,"")
		bpy.ops.object.convert(target="CURVE")
		bpy.ops.object.scale_clear()
		bpy.ops.object.select_all()

		if OBJ_WELD is not None:
			weldInsetFrac = 0.83
			OBJ_WELD.matrix_world=matrix
			array_mod = OBJ_WELD.modifiers.new(type="ARRAY", name=kWPLWeldMods+"_array")
			array_mod.use_merge_vertices=True
			#count=int(int(float(edge_length))*2)
			count = int(0.5*float(edge_length)/(OBJ_WELD.dimensions[0]*weldInsetFrac))+1
			array_mod.count=count
			array_mod.relative_offset_displace[0]=weldInsetFrac
			curve_mod=OBJ_WELD.modifiers.new(type="CURVE", name=kWPLWeldMods+"_curve")
			curve_mod.object=OBJ1
			#bpy.data.objects[OBJ_WELD.name].select=True
			#bpy.context.scene.objects.active = OBJ1
			#bpy.ops.object.modifier_apply(modifier=kWPLWeldMods+"_array")
			bpy.ops.object.select_all(action = 'DESELECT')
		OBJ1.select = True
		bpy.ops.object.mode_set(mode = 'EDIT')
		return {'FINISHED'}

class WPLWeldToolsSettings(bpy.types.PropertyGroup):
	weld_object = StringProperty(
		name="Weld object",
		default = ""
	)

class WPLWelderTools_Panel1(bpy.types.Panel):
	bl_label = "Welder"
	bl_space_type = "VIEW_3D"
	bl_region_type = "TOOLS"
	bl_category = "Welder"
 
	def draw(self, context):
		obj = context.active_object
		if obj is None:
			return
		wpl_weldOpts = context.scene.wpl_weldOpts
		layout = self.layout
		col = layout.column()
		col.prop_search(wpl_weldOpts, "weld_object", context.scene, "objects", icon="SNAP_NORMAL")
		self.layout.operator("mesh.add_weld")

def register():
	print("WPLWelderTools_Panel1 registered")
	bpy.utils.register_module(__name__)
	bpy.types.Scene.wpl_weldOpts = PointerProperty(type=WPLWeldToolsSettings)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.utils.unregister_class(WPLWeldToolsSettings)

if __name__ == "__main__":
	register()