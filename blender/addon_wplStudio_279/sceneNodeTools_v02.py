import math
import copy
import mathutils
import numpy as np

import bpy
from bpy.props import *
import bpy.types
import bmesh
from mathutils import Vector, Matrix

bl_info = {
	"name": "Scene Node tools",
	"author": "IPv6",
	"version": (1, 2, 3),
	"location": "View 3D > Node Editor > Menu",
	"blender": (2, 7, 9),
	"description": "Adds hierarchical submenus for nodegroups",
	"warning": "",
	"category": "WPL",
	}

kWPLNodePrefix = "#"
kWPLSystemReestrObjs = "Reestr"
kWPLMatTokenWPV = '_v'
kWPLMatTokenDedup = '.'
kWPLHierarchyChar = '_'

class WPL_Gnt:
	ngstore = {}
	rowstr = {}
	nodecopy = {}

######################### ######################### #########################
######################### ######################### #########################
def dumpPythonObject(obj):
	print("- object Dump:")
	for attr in dir(obj):
		if hasattr( obj, attr ):
			print( "...%s = %s" % (attr, getattr(obj, attr)))

def strToTokens(sustrParts):
	if sustrParts is None or len(sustrParts) == 0:
		return []
	sustrParts = sustrParts.replace(";",",")
	sustrParts = sustrParts.replace("+",",")
	sustrParts = sustrParts.replace("|",",")
	stringTokens = [x.strip().lower() for x in sustrParts.split(",")]
	return stringTokens

def checkNameRenamed(node_name):
	if node_name is None:
		return None
	#if node_name == "osl_texTemplateStripes_v02.osl":
	#	return "osl_texTemplateStripes_v02"
	#if node_name == "osl_texStripeTemplate_v02":
	#	return "osl_texTemplateStripes_v02"
	#if node_name == "zzz_Placeholder_v02" or node_name == "fg_charSkin_FaceObject_v35":
	#	return "zzz_Clear"
	#if node_name == "fg_charClothSew_v28" or node_name == "fg_marksSew_v01":
	#	return "zzz_Clear"
	return None

######################### ######################### #########################
######################### ######################### #########################
class NODEVIEW_MT_WPL_Groups(bpy.types.Menu):
	bl_label = "WPL Groups"
	bl_idname = "NODEVIEW_MT_WPL_Groups"
	
	def draw(self, context):
		# menu type
		tree_type = context.space_data.tree_type
		typeFilter = 'SHADER'
		addnodeType = 'ShaderNodeGroup'
		if tree_type == 'CompositorNodeTree':
			typeFilter = 'COMPOSITING'
			addnodeType = 'CompositorNodeGroup'
		# hierlevel
		nameFilter = ""
		try:
			row = context.hier
			nameFilter = WPL_Gnt.rowstr[row]
		except:
			pass
		if len(nameFilter) == 0:
			WPL_Gnt.rowstr = {} # resetting to free objects
		#print("WPL_Gnt.rowstr len=",len(WPL_Gnt.rowstr))
		layout = self.layout
		all_ngroups = bpy.data.node_groups
		all_ngroups_mtt = []
		next_hiercounts = {}
		for ng in all_ngroups:
			ui_name = ng.name
			if ng.type != typeFilter:
				# ignoring improper nodes
				#print("node type",ng.type)
				continue
			if ng.library is not None:
				ui_name = "L: "+ng.name
			if len(nameFilter) > 0 and not ui_name.startswith(nameFilter):
				continue
			bpy.types.WindowManager.ngstore[ui_name] = ng
			
			ui_name_nofil = ui_name
			if len(nameFilter) > 0:
				ui_name_nofil = ui_name_nofil.replace(nameFilter,"")
			ng_hier = ui_name_nofil.split(kWPLHierarchyChar)
			ng_hier_str = ""
			if len(ng_hier)>0:
				ng_hier_str = nameFilter+ng_hier[0]+kWPLHierarchyChar
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
				n_op.type = addnodeType
				n_op.use_transform = True
				n_op_set = n_op.settings.add()
				n_op_set.name = "node_tree"
				# !!!-->> not using node name here! Local and Library items can have EXACT THE SAME NAME <<--!!!
				n_op_set.value = "bpy.types.WindowManager.ngstore['"+ng_ui+"']" #"bpy.data.node_groups['"+item.name+"']"
			else:
				if next_hiercounts[ng_hier] < 999:
					next_hiercounts[ng_hier] = 999
					row = layout.row()
					#n_op_set2 = n_op_start.settings.add()
					#n_op_set2.name = "hier["+ng_ui+"]"
					#n_op_set2.value = ng_hier
					WPL_Gnt.rowstr[row] = ng_hier
					row.context_pointer_set("hier", row)
					row.menu("NODEVIEW_MT_WPL_Groups", text = item["hier"]+"...")

class wplnode_dedupmats(bpy.types.Operator):
	bl_idname = "object.wplnode_dedupmats"
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
	opt_upgrRenamesMats = BoolProperty(
		name="Upgrade renames",
		default=True
	)
	@classmethod
	def poll( cls, context ):
		return True

	def getLibraryAnalogMat(self, mewmat, matsAll):
		if mewmat is None:
			return None
		if mewmat.library is None:
			for ngt in matsAll:
				if ngt.library is not None and ngt.name == mewmat.name:
					mewmat = ngt
		return mewmat

	def getMatByName(self, mat_name, matsAll):
		if mat_name is None:
			return None
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
		if self.opt_upgrRenamesMats == True:
			for obj in bpy.data.objects:
				if not self.isObjUpdatable(obj,skipNameParts):
					continue
				for slt in obj.material_slots:
					renam = checkNameRenamed(slt.material.name)
					renamMat = self.getMatByName(renam, mats)
					if renamMat is not None:
						print("- %s: '%s' -> '%s'" % (obj.name, slt.name, renamMat))
						slt.material = renamMat
						itogo_ok = itogo_ok+1
		self.report({'INFO'}, "Materials updated: "+str(itogo_ok)+", skipped: "+str(itogo_skip))
		return {'FINISHED'}

class wplnode_dedupnods(bpy.types.Operator):
	bl_idname = "object.wplnode_dedupnods"
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
	opt_upgrRenamesScripts = BoolProperty(
		name="Upgrade renames",
		default=True
	)

	@classmethod
	def poll( cls, context ):
		return True

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

	def upgradeScript(self, node, upgradeVersion, checkLibAtls, upgradeRenames, parentName):
		script_texts = bpy.data.texts
		if checkLibAtls and node.script is not None and node.script.library is None:
			ngt = self.getLibraryAnalog(node.script.name, script_texts)
			if ngt is not None:
				print("- '%s': Warning: library analog found: '%s' -> '%s'" % (parentName, node.script.name, ngt.name))
				node.script = ngt
				print("-- Upgraded to library analog")
		if node.script is not None:
			renamedName = checkNameRenamed(node.script.name)
			if renamedName is not None:
				print("- '%s': Warning: upgradable script item '%s' -> '%s'" % (parentName, node.script.name, renamedName))
				if upgradeRenames:
					node.script = script_texts.get(renamedName)
					print("-- Upgraded to '%s'" % (renamedName))
				return True
			upgrName = self.getHigherVerName(node.script.name, script_texts)
			if upgrName is not None:
				print("- '%s': Warning: upgradable script item '%s' -> '%s'" % (parentName, node.script.name, upgrName))
				if upgradeVersion:
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
				if  node.mode != 'EXTERNAL' and node.script is None:
					print("- Warning: Broken node, no script in %s" % (refname))
					itogos["prb"] = itogos["prb"]+1
					return
				if self.dedupeScript(node,refname):
					itogos["cln"] = itogos["cln"]+1
				if self.upgradeScript(node,self.opt_upgrNodeScripts,self.opt_upgrToLinked,self.opt_upgrRenamesScripts,refname):
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

class wplnode_findnodeuse(bpy.types.Operator):
	bl_idname = "object.wplnode_findnodeuse"
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

		if nd.bl_idname == 'ShaderNodeScript' and nd.mode != 'EXTERNAL' and nd.script is None:
			log_str = "- !!! found broken node "+nd.name+" in "+src_info
			debug_logs.append(log_str)
			print(log_str)
			return
		if nd.bl_idname == 'ShaderNodeGroup' and (nd.node_tree is None or len(nd.node_tree.nodes) == 0):
			log_str = "- !!! found broken node "+nd.name+" in "+src_info
			debug_logs.append(log_str)
			print(log_str)
			return
		isAnyTestPresent = None
		for tn in testNames:
			if tn in nd.name:
				isAnyTestPresent = "name:"+nd.name
			if tn in nd.label:
				isAnyTestPresent = "label:"+nd.label
			if nd.bl_idname == 'ShaderNodeScript':
				if nd.script is not None and tn in nd.script.name.lower():
					isAnyTestPresent = "script:"+nd.script.name
				if nd.filepath is not None and tn in nd.filepath.lower():
					isAnyTestPresent = "file:"+nd.filepath
			if nd.bl_idname == 'ShaderNodeGroup' and tn in nd.node_tree.name.lower():
				isAnyTestPresent = "nodetree:"+nd.node_tree.name
		if isAnyTestPresent is None:
			return
		log_str = "- "+nd.name+" in "+src_info+" ["+isAnyTestPresent+"]"
		debug_logs.append(log_str)
		print(log_str)
		for inpt in nd.inputs:
			#print("input:", inpt)
			if inpt.is_linked:
				for tn in testNames:
					if tn in inpt.name.lower():
						log_str = "- found linked input "+inpt.name
						debug_logs.append(log_str)
						print(log_str)
			elif inpt.type == 'STRING' and len(inpt.default_value) > 0:
				for tn in testNames:
					if tn in inpt.name.lower():
						log_str = "- found linked input "+inpt.name+" = "+inpt.default_value
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
			stringTokens = strToTokens(self.nameSubstrs)
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

class wplnode_nodeval_copy(bpy.types.Operator):
	bl_idname = "object.wplnode_nodeval_copy"
	bl_label = "Copy #values"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		space = context.space_data
		return space.type == 'NODE_EDITOR'

	def execute( self, context ):
		keys_found = WPL_Gnt.nodecopy
		selnodes = context.selected_nodes
		if len(selnodes) == 0:
			self.report({'INFO'}, "Select some nodes first")
			return {'FINISHED'}
		for node in selnodes:
			if kWPLNodePrefix in node.label:
				#dumpPythonObject(node)
				if node.bl_idname == 'ShaderNodeRGB':
					keys_found[node.label] = list(node.outputs[0].default_value)
				elif node.bl_idname == 'ShaderNodeCombineXYZ':
					keys_found[node.label] = [node.inputs[0].default_value, node.inputs[1].default_value, node.inputs[2].default_value]
				elif node.bl_idname == 'ShaderNodeValue':
					keys_found[node.label] = node.outputs[0].default_value
				elif node.bl_idname == 'ShaderNodeVectorCurve':
					cmapping = {}
					cmapping["curves"] = []
					for curve in node.mapping.curves:
						ccurve = {}
						ccurve["points"] = []
						for point in curve.points:
							cpoint = {}
							cpoint["handle_type"] = point.handle_type
							cpoint["location"] = copy.copy(point.location)
							cpoint["select"] = point.select
							ccurve["points"].append(cpoint)
						cmapping["curves"].append(ccurve)
					keys_found[node.label] = cmapping
				else:
					self.report({'ERROR'}, "Can not copy node value: "+node.label)
					return {'CANCELLED'}
		print("Copied node values", keys_found)
		self.report({'INFO'}, "Values copied="+str(len(keys_found)))
		return {'FINISHED'}

class wplnode_nodeval_paste(bpy.types.Operator):
	bl_idname = "object.wplnode_nodeval_paste"
	bl_label = "Paste #values"
	bl_options = {'REGISTER', 'UNDO'}

	opt_dryRun = BoolProperty(
			name = "Do nothing, dry run",
			default = False
	)
	opt_nodeTag = StringProperty(
			name = "Paste tagged only",
			default = ""
	)
	opt_curvesXSym = BoolProperty(
			name = "Curves: apply X symmetry",
			default = False
	)
	
	@classmethod
	def poll(cls, context):
		space = context.space_data
		return space.type == 'NODE_EDITOR'

	def execute( self, context ):
		keys_found = WPL_Gnt.nodecopy
		if len(keys_found) == 0:
			self.report({'INFO'}, "Copy some values first")
			return {'FINISHED'}
		pasted_values = {}
		selnodes = context.selected_nodes
		if len(selnodes) == 0:
			self.report({'INFO'}, "Select some nodes first")
			return {'FINISHED'}
		if self.opt_dryRun:
			self.report({'INFO'}, "Dry run: Operation skipped (F6)")
			return {'FINISHED'}
		for node in selnodes:
			if kWPLNodePrefix in node.label:
				#dumpPythonObject(node)
				if node.label not in keys_found:
					print("- Skipping node, not in clipboard", node.label)
					continue
				if len(self.opt_nodeTag) > 0 and not(self.opt_nodeTag in node.label):
					print("- Skipping node, not tagged", node.label, self.opt_nodeTag)
					continue
				val = keys_found[node.label]
				pasted_values[node.label] = val
				if node.bl_idname == 'ShaderNodeRGB':
					node.outputs[0].default_value = val
				if node.bl_idname == 'ShaderNodeCombineXYZ':
					node.inputs[0].default_value = val[0]
					node.inputs[1].default_value = val[1]
					node.inputs[2].default_value = val[2]
				if node.bl_idname == 'ShaderNodeValue':
					node.outputs[0].default_value = val
				if node.bl_idname == 'ShaderNodeVectorCurve':
					if len(node.mapping.curves) == 0 or len(val["curves"]) == 0:
						print("- Skipping node, missing curves", node.label, len(node.mapping.curves), len(val["curves"]))
						self.report({'ERROR'}, "Can not paste curve: "+node.label)
						return {'CANCELLED'}
					if len(node.mapping.curves) != len(val["curves"]):
						print("! Warning: curves count not the same", node.label, len(node.mapping.curves), len(val["curves"]))
					# https://docs.blender.org/api/2.79/bpy.types.CurveMapPoint.html#bpy.types.CurveMapPoint
					for i, node_curv in enumerate(node.mapping.curves):
						if i >= len(val["curves"]):
							break
						val_curv = val["curves"][i]
						#print("..Handling curve point",node_curv,val_curv)
						while len(node_curv.points) > len(val_curv["points"]):
							p = node_curv.points[0]
							#print("..Removing point",p)
							node_curv.points.remove(p)
						while len(node_curv.points) < len(val_curv["points"]):
							#print("..Adding point")
							node_curv.points.new(0,0)
						pnt_len = len(val_curv["points"])
						for i in range(0, pnt_len):
							val_point = val_curv["points"][i]
							node_point = node_curv.points[i]
							pst_location = copy.copy(val_point["location"])
							if self.opt_curvesXSym and pst_location[0] < 0:
								# getting value from x>0 side
								symPnt = val_curv["points"][pnt_len-i-1]
								symPnt_loc = copy.copy(symPnt["location"])
								symPnt_loc = (-1*symPnt_loc[0],symPnt_loc[1])
								pst_location = symPnt_loc
							#print("..Copy from",val_point,"to",node_point)
							node_point.handle_type = val_point["handle_type"]
							node_point.location = pst_location
							node_point.select = val_point["select"]
							#dumpPythonObject(val_point)
							#dumpPythonObject(node_point)
					node.mapping.update()
		self.report({'INFO'}, "Values pasted="+str(len(pasted_values))+"; in clipboard: "+str(len(keys_found)))
		return {'FINISHED'}


# class wplnode_nodeinj_locals(bpy.types.Operator):
	# bl_idname = "object.wplnode_nodeinj_locals"
	# bl_label = "Inject locals"
	# bl_options = {'REGISTER', 'UNDO'}

	
	# @classmethod
	# def poll(cls, context):
		# space = context.space_data
		# return space.type == 'NODE_EDITOR'
		
	# def execute( self, context ):
		# active_obj = context.scene.objects.active
		# selnodes = context.selected_nodes
		# if len(selnodes) == 0 or active_obj is None:
			# self.report({'INFO'}, "Select some object and material nodes first")
			# return {'FINISHED'}
		# locals_found = 0
		# inject_found = 0
		# active_mat = active_obj.material_slots[active_obj.active_material_index]
		# target_locals_prefix = active_mat.name
		# node_groups = bpy.data.node_groups
		# for node in selnodes:
			# if node.bl_idname == 'ShaderNodeGroup' and kWPLNodePrefix in node.label:
				# inject_found = inject_found+1
				# node_clear_name = node.label.replace(kWPLNodePrefix,"")
				# replacement_name = target_locals_prefix+"_"+node_clear_name
				# print("Looking for injection", node.name, replacement_name, node)#dumpPythonObject(node)
				# if node.node_tree.name == replacement_name:
					# print("- Skipping - already injected", node.name, replacement_name)
					# continue
				# if replacement_name in node_groups:
					# replacement_nodegroup = node_groups[replacement_name]
					# node.node_tree = replacement_nodegroup
					# locals_found=locals_found+1
					# print("- Injected", replacement_name)
		# self.report({'INFO'}, "Replaced nodegroups: "+str(locals_found)+"/"+str(inject_found))
		# return {'FINISHED'}

######################### ######################### #########################
######################### ######################### #########################
class NODEVIEW_MT_WPL_Menu(bpy.types.Menu):
	bl_label = "WPL Groups"

	@classmethod
	def poll(cls, context):
		space = context.space_data
		return space.type == 'NODE_EDITOR'

	def draw(self, context):
		tree_type = context.space_data.tree_type
		if not ((tree_type in "ShaderNodeTree") or (tree_type in "CompositorNodeTree")):
			#print("tree_type",tree_type)
			return

		layout = self.layout
		layout.separator()
		layout.operator_context = 'INVOKE_REGION_WIN'
		layout.menu(NODEVIEW_MT_WPL_Groups.bl_idname)
		

class WPLSceneNodes_Panel1(bpy.types.Panel):
	bl_label = "Scene Nodes"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	#bl_context = "objectmode"
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		col = self.layout.column()
		col.operator("object.wplnode_dedupnods", text="Dedupe NodeGroups")
		col.operator("object.wplnode_dedupmats", text="Dedupe Materials")
		col.operator("object.wplnode_findnodeuse", text="Test nodes")

class WPLSceneNodes_Panel2(bpy.types.Panel):
	bl_label = "Scene Nodes"
	bl_space_type = 'NODE_EDITOR'
	bl_region_type = 'TOOLS'
	bl_category = 'WPL'

	def draw_header(self, context):
		layout = self.layout
		layout.label(text="")

	def draw(self, context):
		col = self.layout.column()
		col.operator("object.wplnode_nodeval_copy", text="Copy #values")
		col.operator("object.wplnode_nodeval_paste", text="RawPaste #values").opt_curvesXSym = False
		col.operator("object.wplnode_nodeval_paste", text="SymPaste #values").opt_curvesXSym = True
		#col.separator()
		#col.operator("object.wplnode_nodeinj_locals", text="Inject locals")

def register():
	bpy.utils.register_module(__name__)
	try:
		ngstore = bpy.types.WindowManager.ngstore
	except:
		bpy.types.NODE_MT_add.append(bpy.types.NODEVIEW_MT_WPL_Menu.draw)
		bpy.types.WindowManager.ngstore = WPL_Gnt.ngstore

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