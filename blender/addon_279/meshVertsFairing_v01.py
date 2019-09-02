import math
import copy
import mathutils
import time
from mathutils import kdtree
from bpy_extras import view3d_utils
import numpy as np
import datetime

import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from bpy.props import *
import bpy.types
import bmesh
import collections
import math
import mathutils
import sys
import threading
from typing import Dict, List, Optional, Set, Tuple


# stripped from https://github.com/fedackb/mesh-fairing to work on 2.79b
# stripped from https://github.com/jeacom25b/blender-boundary-aligned-remesh to work on 2.79b

bl_info = {
	"name": "Fairing Tools",
	"author": "Various",
	"version": (1, 1, 5),
	"blender": (2, 7, 9),
	"location": "View3D > T-panel > Misc",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Misc"}

###########################
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

###########################
class Solver():
	"""
	Linear system solver interface
	"""

	def solve(self, A: Dict[Tuple[int], float], b: List[List[float]]):
		"""
		Solves the Ax=b linear system of equations

		Parameters:
			A (Dict[Tuple[int], float]): Coefficient matrix A
			b (List<List<float>>): Right hand side of the linear system

		Returns:
			numpy.ndarray: Variables matrix (x); None if unsuccessful

		Raises: NotImplementedError
		"""
		raise NotImplementedError


class NumPySolver(Solver):
	"""
	Linear system solver implemented with NumPy library

	Attributes:
		numpy (importlib.type.ModuleType): NumPy library
	"""

	def __init__(self, *args, **kwargs):
		"""
		Initializes this linear system solver
		"""
		super().__init__(*args, **kwargs)
		self.numpy = np #importlib.import_module('numpy')

	def solve(self, A: Dict[Tuple[int], float], b: List[List[float]]):
		"""
		Solves the Ax=b linear system of equations using NumPy library

		Parameters:
			A (Dict[Tuple[int], float]): Coefficient matrix A
			b (List[List[float]]): Right hand side of the linear system

		Returns:
			numpy.ndarray: Variables matrix (x); None if unsuccessful
		"""
		x = None
		n = len(b)

		# Attempt to solve the linear system with NumPy library.
		try:
			A_numpy = self.numpy.zeros((n, n), dtype = 'd')
			b = self.numpy.asarray(b, dtype = 'd')
			for key, val in A.items():
				A_numpy[key] = val
			x = self.numpy.linalg.solve(A_numpy, b)
		except Exception as e:
			print(e)

		return x

solver = NumPySolver()


class Cache(dict):
	"""
	Data structure for caching values, essentially functioning as a dictionary
	where values can be calculated for keys not present in the collection

	Attributes:
		_calc (typing.Callable): Caching function to calculate values
	"""

	def __init__(self, calc, *args, **kwargs):
		"""
		Initializes this cache

		Parameters:
			calc (callable): Caching function to calculate values
		"""
		super().__init__(*args, **kwargs)
		if calc is None:
			raise TypeError('A caching function is required')
		else:
			self._calc = calc

	def __getitem__(self, key):
		"""
		Gets cached value or calculates a value if not already cached

		Returns:
			Any: Cached value
		"""
		if key not in self:
			self[key] = self._calc(key)
		return super().__getitem__(key)

	def get(self, key):
		"""
		Gets cached value or calculates a value if not already cached

		Returns:
			Any: Cached value
		"""
		return self[key]
############################



def calc_circumcenter(a: mathutils.Vector,
					  b: mathutils.Vector,
					  c: mathutils.Vector) -> float:
	"""
	Calculates the 3-dimensional circumcenter of three points

		https://gamedev.stackexchange.com/a/60631

	Parameters:
		a, b, c (mathutils.Vector): Points of a triangle

	Returns:
		mathutils.Vector: Circumcenter point
	"""
	ab = b - a
	ac = c - a
	ab_cross_ac = ab.cross(ac)
	if ab_cross_ac.length_squared > 0:
		d = ac.length_squared * ab_cross_ac.cross(ab)
		d += ab.length_squared * ac.cross(ab_cross_ac)
		d /= 2 * ab_cross_ac.length_squared
		return a + d
	else:
		return a


def calc_uniform_vertex_weight(v: bmesh.types.BMVert) -> float:
	"""
	Calculates uniform weight of the given vertex

	Parameters:
		v (bmesh.types.BMVert): Vertex for which to calculate the weight

	Returns:
		float: Uniform vertex weight
	"""
	n = len(v.link_edges)
	return 1 / n if n != 0 else sys.maxsize


def calc_barycentric_vertex_weight(v: bmesh.types.BMVert) -> float:
	"""
	Calculates inverse Barycentric area weight of the given vertex

	Parameters:
		v (bmesh.types.BMVert): Vertex

	Returns:
		float: Inverse Barycentric area vertex weight
	"""
	area = 0
	a = v.co
	for l in v.link_loops:
		b = l.link_loop_next.vert.co
		c = l.link_loop_prev.vert.co
		area += mathutils.geometry.area_tri(a, b, c) / 3
	return 1 / area if area != 0 else 1e12


def calc_voronoi_vertex_weight(v: bmesh.types.BMVert) -> float:
	"""
	Calculates inverse Voronoi area weight of the given vertex

	Parameters:
		v (bmesh.types.BMVert): Vertex

	Returns:
		float: Inverse Voronoi area vertex weight
	"""
	area = 0
	a = v.co
	acute_threshold = math.pi / 2
	for l in v.link_loops:
		b = l.link_loop_next.vert.co
		c = l.link_loop_prev.vert.co
		if l.calc_angle() < acute_threshold:
			d = calc_circumcenter(a, b, c)
		else:
			d = (b + c) / 2
		area += mathutils.geometry.area_tri(a, (a + b) / 2, d)
		area += mathutils.geometry.area_tri(a, d, (a + c) / 2)
	return 1 / area if area != 0 else 1e12


def calc_cotangent_loop_weight(l: bmesh.types.BMLoop) -> float:
	"""
	Calculates cotangent weight of the given loop

	Parameters:
		l (bmesh.types.BMLoop): Loop

	Returns:
		float: Cotangent loop weight
	"""
	weight = 0
	co_a = l.vert.co
	co_b = l.link_loop_next.vert.co
	coords = [l.link_loop_prev.vert.co]
	if not l.edge.is_boundary:
		coords.append(
			l.link_loop_radial_next.link_loop_next.link_loop_next.vert.co)
	for co_c in coords:
		try:
			angle = (co_a - co_c).angle(co_b - co_c)
			weight += 1 / math.tan(angle)
		except (ValueError, ZeroDivisionError):
			weight += 1e-4
	weight /= 2
	return weight


def calc_mvc_loop_weight(l: bmesh.types.BMLoop) -> float:
	"""
	Calculates mean value coordinate weight of the given loop

	Parameters:
		l (bmesh.types.BMLoop): Loop

	Returns:
		float: Mean value coordinate loop weight
	"""
	weight = 0
	length = l.edge.calc_length()
	if length > 0:
		weight += math.tan(l.calc_angle() / 2)
		if not l.edge.is_boundary:
			weight += math.tan(
				l.link_loop_radial_next.link_loop_next.calc_angle() / 2)
		weight /= length
	return weight


def calc_mean_curvature(v: bmesh.types.BMVert,
						vert_weights: Dict[bmesh.types.BMVert, float],
						loop_weights: Dict[bmesh.types.BMLoop, float]) -> float:
	"""
	Calculates signed mean curvature of the given vertex

	Parameters:
		v (bmesh.types.BMVert):							Vertex
		vert_weights (Dict[bmesh.types.BMVert, float]): Vertex weights
		loop_weights (Dict[bmesh.types.BMLoop, float]): Loop weights

	Returns:
		float: Signed mean curvature (valleys < 0; flats == 0; ridges > 0)
	"""
	curvature = 0
	normal = mathutils.Vector((0, 0, 0))
	for l in v.link_loops:
		normal += loop_weights[l] * (v.co - l.edge.other_vert(v).co)
	normal *= vert_weights[v]
	curvature = normal.length / 2
	if v.normal.dot(normal) < 1:
		curvature *= -1
	return curvature


def calc_gaussian_curvature(v: bmesh.types.BMVert,
							vert_weights: Dict[bmesh.types.BMVert, float]) -> float:
	"""
	Calculates Gaussian curvature of the given vertex

	Parameters:
		v (bmesh.types.BMVert):							Vertex
		vert_weights (Dict[bmesh.types.BMVert, float]): Vertex weights

	Returns:
		float: Gaussian curvature
	"""
	a = v.co
	angle_sum = 0
	acute_threshold = math.pi / 2
	for l in v.link_loops:
		angle = l.calc_angle()
		if angle < acute_threshold:
			angle_sum += angle
		else:
			b = l.link_loop_next.vert.co
			c = l.link_loop_prev.vert.co
			d = (b + c) / 2
			try:
				angle_sum += math.pi - (b - d).angle(c - d)
			except ValueError:
				angle_sum += 1e-4
	return vert_weights[v] * (2 * math.pi - angle_sum)


def fair(verts: List[bmesh.types.BMVert],
		 order: int,
		 vert_weights: Dict[bmesh.types.BMVert, float],
		 loop_weights: Dict[bmesh.types.BMLoop, float],
		 status = None) -> bool:
	"""
	Displaces given vertices to form a smooth-as-possible mesh patch

	Parameters:
		verts (List[bmesh.types.BMVert]):				Vertices to act upon
		order (int):									Laplace-Beltrami
														operator order
		vert_weights (Dict[bmesh.types.BMVert, float]): Vertex weights
		loop_weights (Dict[bmesh.types.BMLoop, float]): Loop weights
		status (Optional[types.Property]):				Status message

	Returns:
		bool: True if fairing succeeded; False otherwise
	"""
	# Setup the linear system.
	interior_verts = (v for v in verts if not v.is_boundary and not v.is_wire)
	vert_col_map = {v: col for col, v in enumerate(interior_verts)}
	A = dict()
	b = [[0 for i in range(3)] for j in range(len(vert_col_map))]
	for v, col in vert_col_map.items():
		if status is not None:
			status.set('Setting up linear system ({:>3}%)'.format(
				int((col + 1) / len(vert_col_map) * 100)))
		setup_fairing(v, col, A, b, 1, order, vert_col_map, vert_weights, loop_weights)

	# Solve the linear system.
	if status is not None:
		status.set('Solving linear system')
	x = solver.solve(A, b)

	# Apply results.
	if x is not None:
		if status is not None:
			status.set('Applying results')
		for v, col in vert_col_map.items():
			v.co = x[col]
		return True

	return False


def setup_fairing(v: bmesh.types.BMVert,
				  i: int,
				  A: Dict[Tuple[int], float],
				  b: List[List[float]],
				  multiplier: float,
				  depth: int,
				  vert_col_map: Dict[bmesh.types.BMVert, int],
				  vert_weights: Dict[bmesh.types.BMVert, float],
				  loop_weights: Dict[bmesh.types.BMLoop, float]):
	"""
	Recursive helper function to build a linear system that represents the
	discretized fairing problem
	Implementation details are based on CGAL source code available on GitHub:
		cgal/Polygon_mesh_processing/include/CGAL/Polygon_mesh_processing/internal/fair_impl.h
	Parameters:
		v (bmesh.types.BMVert):							Vertex
		i (int):										Row index of A
		A (Dict[Tuple[int], float]):					Coefficient matrix A
		b (List[List[float]]):							Right hand side of the
														linear system
		multiplier (float):								Recursive multiplier
		depth (int):									Recursion depth
		vert_col_map (Dict[bmesh.types.BMVert, int]):	Maps each vertex to a
														column index j of A
		vert_weights (Dict[bmesh.types.BMVert, float]): Vertex weights
		loop_weights (Dict[bmesh.types.BMLoop, float]): Loop weights
	"""
	if depth == 0:

		# Set the coefficient of an internal vertex.
		if v in vert_col_map:
			j = vert_col_map[v]
			if (i, j) not in A:
				A[i, j] = 0
			A[i, j] -= multiplier

		# Set the value of a boundary vertex.
		else:
			b[i][0] += multiplier * v.co.x
			b[i][1] += multiplier * v.co.y
			b[i][2] += multiplier * v.co.z
	else:
		w_ij_sum = 0
		w_i = vert_weights[v]

		# Recursively compute adjacent vertices.
		for l in v.link_loops:
			other = l.link_loop_next.vert
			w_ij = loop_weights[l]
			w_ij_sum += w_ij
			setup_fairing(other, i, A, b, w_i * w_ij * multiplier, depth - 1, vert_col_map, vert_weights, loop_weights)

		# Recursively compute this vertex.
		setup_fairing(v, i, A, b, -1 * w_i * w_ij_sum * multiplier, depth - 1, vert_col_map, vert_weights, loop_weights)


def find_edge(v1: bmesh.types.BMVert,
			  v2: bmesh.types.BMVert) -> bmesh.types.BMEdge:
	"""
	Finds the edge, if any, connecting given vertices

	Parameters:
		v1, v2 (bmesh.types.BMVert): Vertices

	Returns:
		bmesh.types.BMEdge: Edge connecting vertices; None if not found
	"""
	for e in v1.link_edges:
		if e.other_vert(v1) is v2:
			return e
	return None


def get_closed_neighborhood(v: bmesh.types.BMVert, dist: int) -> Set[bmesh.types.BMVert]:
	"""
	Gets all linked vertices within given distance of a vertex

	Parameters:
		v (bmesh.types.BMVert): Vertex from which to search
		dist (int):				Maximum distance to search

	Returns:
		Set[bmesh.types.BMVert]: Closed neighborhood
	"""
	if dist <= 0:
		visisted = {v}
	else:
		visited = set()
		traversal_queue = collections.deque()
		traversal_queue.appendleft((v, 0))
		while len(traversal_queue) > 0:
			v_curr, dist_curr = traversal_queue.pop()
			visited.add(v_curr)
			if dist_curr < dist:
				dist_next = dist_curr + 1
				for e in v_curr.link_edges:
					v_next = e.other_vert(v_curr)
					if v_next not in visited:
						traversal_queue.appendleft((v_next, dist_next))
	return visited


def expand_faces(faces: Set[bmesh.types.BMFace], dist: int) -> Set[bmesh.types.BMFace]:
	"""
	Expands given face set by a specified topological distance

	Parameters:
		faces (List[bmesh.types.BMFace]): Faces to evaluate
		dist (int):						  Topological distance

	Returns:
		Set[bmesh.types.BMFace]: Expanded face selection
	"""
	if dist <= 0:
		visited = set(faces)
	else:
		visited = set()
		traversal_queue = collections.deque((f, 0) for f in faces)
		while len(traversal_queue) > 0:
			f_curr, dist_curr = traversal_queue.pop()
			visited.add(f_curr)
			if dist_curr < dist:
				dist_next = dist_curr + 1
				for l in f_curr.loops:
					f_next = l.link_loop_radial_next.face
					if f_next not in visited:
						traversal_queue.appendleft((f_next, dist_next))
	return visited


def get_boundary_faces(faces: Set[bmesh.types.BMFace]) -> Set[bmesh.types.BMFace]:
	"""
	Determines which among the given faces are boundary faces

	Parameters:
		faces (List[bmesh.types.BMFace]): Faces to evaluate

	Returns:
		Set[bmesh.types.BMFace]: Boundary faces
	"""
	boundary = set()
	for f_curr in faces:
		for l in f_curr.loops:
			f_other = l.link_loop_radial_next.face
			if f_other is f_curr or f_other not in faces:
				boundary.add(f_curr)
	return boundary

class VertexWeight():
	"""
	Defines the enumeration of vertex weight types
	"""
	UNIFORM = 1
	BARYCENTRIC = 2
	VORONOI = 3

	@classmethod
	def create_cache(cls, cachetype):
		"""
		Factory method for creating a vertex weight cache

		Returns:
			Cache: Vertex weight cache
		"""
		if cachetype == VertexWeight.UNIFORM:
			return Cache(calc_uniform_vertex_weight)
		elif cachetype == VertexWeight.BARYCENTRIC:
			return Cache(calc_barycentric_vertex_weight)
		elif cachetype == VertexWeight.VORONOI:
			return Cache(calc_voronoi_vertex_weight)

class LoopWeight():
	"""
	Defines the enumeration of loop weight types
	"""
	UNIFORM = 1
	COTAN = 2
	MVC = 3

	@classmethod
	def create_cache(cls, cachetype):
		"""
		Factory method for creating a loop weight cache

		Returns:
			Cache: Loop weight cache
		"""
		if cachetype == LoopWeight.UNIFORM:
			return Cache(lambda l: 1)
		elif cachetype == LoopWeight.MVC:
			return Cache(calc_mvc_loop_weight)
		elif cachetype == LoopWeight.COTAN:
			return Cache(calc_cotangent_loop_weight)

############################
class wpled_fair(bpy.types.Operator):
	bl_idname = "mesh.wpled_fair"
	bl_label = "Mesh fairing"
	bl_options = {'REGISTER', 'UNDO'}

	opt_continutyOrder = IntProperty(
			name="Order",
			min=1, max=3,
			default=1
		)

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		active_obj = context.scene.objects.active
		if active_obj is None:
			return {'FINISHED'}
		
		# Initialize BMesh.
		bm = bmesh.from_edit_mesh(active_obj.data)

		# Determine which vertices are affected.
		affected_verts = [v for v in bm.verts if v.select]

		# Pre-fair affected vertices for consistent results.
		fair(
			affected_verts, 1, #types.Continuity.POS.value,
			VertexWeight.create_cache(VertexWeight.UNIFORM), LoopWeight.create_cache(LoopWeight.UNIFORM),
			None)

		fair(
				affected_verts, self.opt_continutyOrder,
				VertexWeight.create_cache(VertexWeight.VORONOI), LoopWeight.create_cache(LoopWeight.COTAN),
				None)

		bm.normal_update()
		bmesh.update_edit_mesh(active_obj.data)
		
		self.report({'INFO'}, "Done")
		return {'FINISHED'}

###########################

# Main Remesher class, this stores all the needed data
class BoundaryAlignedRemesher:
	def __init__(self, obj):
		self.obj = object
		self.bm = bmesh.new()
		self.bm.from_mesh(obj.data)
		self.bvh = BVHTree.FromBMesh(self.bm)
		
		# Boundary_data is a list of directions and locations of boundaries.
		# This data will serve as guidance for the alignment
		self.boundary_data = []
		
		# Fill the data using boundary edges as source of directional data.
		for edge in self.bm.edges:
			if edge.is_boundary:
				vec = (edge.verts[0].co - edge.verts[1].co).normalized()
				center = (edge.verts[0].co + edge.verts[1].co) / 2
				
				self.boundary_data.append((center, vec))
		
		# Create a Kd Tree to easily locate the nearest boundary point
		self.boundary_kd_tree = KDTree(len(self.boundary_data))
		
		for index, (center, vec) in enumerate(self.boundary_data):
			self.boundary_kd_tree.insert(center, index)
		
		self.boundary_kd_tree.balance()

	def nearest_boundary_vector(self, location):
		""" Gets the nearest boundary direction """
		location, index, dist = self.boundary_kd_tree.find(location)
		location, vec = self.boundary_data[index]
		return vec

	def enforce_edge_length(self, edge_length=0.05, bias=0.333):
		""" Replicates dyntopo behaviour """
		upper_length = edge_length + edge_length * bias
		lower_length = edge_length - edge_length * bias
		
		# Subdivide Long edges
		subdivide = []
		for edge in self.bm.edges:
			if edge.calc_length() > upper_length:
				subdivide.append(edge)
		
		bmesh.ops.subdivide_edges(self.bm, edges=subdivide, cuts=1)
		bmesh.ops.triangulate(self.bm, faces=self.bm.faces)
		
		# Remove verts with less than 5 edges, this helps inprove mesh quality
		dissolve_verts = []
		for vert in self.bm.verts:
			if len(vert.link_edges) < 5:
				if not vert.is_boundary:
					dissolve_verts.append(vert)
		
		bmesh.ops.dissolve_verts(self.bm, verts=dissolve_verts)
		bmesh.ops.triangulate(self.bm, faces=self.bm.faces)
		
		# Collapse short edges but ignore boundaries and never collapse two chained edges
		lock_verts = set(vert for vert in self.bm.verts if vert.is_boundary)
		collapse = []
		
		for edge in self.bm.edges:
			if edge.calc_length() < lower_length and not edge.is_boundary:
				verts = set(edge.verts)
				if verts & lock_verts:
					continue
				collapse.append(edge)
				lock_verts |= verts
		
		bmesh.ops.collapse(self.bm, edges=collapse)
		bmesh.ops.beautify_fill(self.bm, faces=self.bm.faces, method=0)

	def align_verts(self, rule=(-1, -2, -3, -4)):
		# Align verts to the nearest boundary by averaging neigbor vert locations selected
		# by a specific rule,
		
		# Rules work by sorting edges by angle relative to the boundary.
		# Eg1. (0, 1) stands for averagiing the biggest angle and the 2nd biggest angle edges.
		# Eg2. (-1, -2, -3, -4), averages the four smallest angle edges
		for vert in self.bm.verts:
			if not vert.is_boundary:
				vec = self.nearest_boundary_vector(vert.co)
				neighbor_locations = [edge.other_vert(vert).co for edge in vert.link_edges]
				best_locations = sorted(neighbor_locations, 
										key = lambda n_loc: abs((n_loc - vert.co).normalized().dot(vec)))
				co = vert.co.copy()
				le = len(vert.link_edges)
				for i in   rule:
					co += best_locations[i % le]
				co /= len(rule) + 1
				co -= vert.co
				co -= co.dot(vert.normal) * vert.normal
				vert.co += co

	def reproject(self):
		""" Recovers original shape """
		for vert in self.bm.verts:
			location, normal, index, dist = self.bvh.find_nearest(vert.co)
			if location:
				vert.co = location

	def remesh(self,edge_length=0.05, iterations=30, quads=True):
		""" Coordenates remeshing """
		if quads:
			rule = (-1,-2, 0, 1)
		else:
			rule = (0, 1, 2, 3)
		
		for _ in range(iterations):
			self.enforce_edge_length(edge_length=edge_length)
			self.align_verts(rule=rule)
			self.reproject()
		
		if quads:
			bmesh.ops.join_triangles(self.bm, faces=self.bm.faces,
										angle_face_threshold=3.14,
										angle_shape_threshold=3.14)
		return self.bm

class Remesher(bpy.types.Operator):
	bl_idname = "mesh.wpled_boundary_aligned_remesh"
	bl_label = "Boundary Aligned Remesh"
	bl_options = {"REGISTER", "UNDO"}

	edge_length = bpy.props.FloatProperty(
		name="Edge Length",
		min=0,
		default = 0.03
	)

	iterations = bpy.props.IntProperty(
		name="Iterations",
		min=1,
		default=30
	)

	quads = bpy.props.BoolProperty(
		name="Quads",
		default=False
	)

	def execute(self, context):
		obj = bpy.context.active_object
		if obj is None:
			return {"FINISHED"}
		print(f"Remeshing {obj.name}")
		select_and_change_mode(obj, 'OBJECT')
		remesher = BoundaryAlignedRemesher(obj)
		bm = remesher.remesh(self.edge_length, self.iterations, self.quads)
		bm.to_mesh(obj.data)
		context.area.tag_redraw()
		return {"FINISHED"}

######### ############ ################# ############

class WPLFairingTools_Panel1(bpy.types.Panel):
	bl_label = "Mesh Fair"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = 'Misc'

	def draw(self, context):
		layout = self.layout
		active_obj = context.scene.objects.active
		col = layout.column()
		if active_obj is not None:
			col.operator("mesh.wpled_fair", text = "Mesh fairing: Position").opt_continutyOrder=1
			col.operator("mesh.wpled_fair", text = "Mesh fairing: Tangency").opt_continutyOrder=2
			col.operator("mesh.wpled_fair", text = "Mesh fairing: Curvature").opt_continutyOrder=3
			col.separator()
			col.operator("mesh.wpled_boundary_aligned_remesh")

def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
	register()
