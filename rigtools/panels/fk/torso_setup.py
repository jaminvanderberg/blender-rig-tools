import json
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from rigtools.assemblies.reconfigure_assembly import prepare_rebuild
from rigtools.assemblies.assembly_transaction import AssemblyTransactionError, run_assembly_transaction
from rigtools.utils.profiling import profile
from rigtools.assemblies.assembly_data import find_assembly
from rigtools.assemblies.template_options import resolve_template_options
from rigtools.assemblies.torso_assembly import TorsoAssemblyOptions, create_torso_assembly
from rigtools.assemblies.torso_templates import get_torso_template, validate_torso_templates
from rigtools.panels.assembly_setup import begin_setup_edit, validate_setup_context
from rigtools.panels.template_draw import SplitSection, TemplateDraw
from rigtools.rig_data.twist_chain import TwistChainStatus, evaluate_twist_snapshot, existing_twist_count, snapshot_twist_status
from rigtools.utils.bone import select_bones
from rigtools.utils.icons import icon
from rigtools.utils.naming import guess_limb_name
from rigtools.tool.twist_bones import falloff_presets
from rigtools.utils.bone_chain import ChainBranchingError, find_chains_from_selection
from rigtools.utils.widget import fk_widget_types


class RIG_OT_advanced_torso_setup(bpy.types.Operator):
	"""Setup Torso Assembly"""
	bl_idname = "rig.advanced_torso_setup"
	bl_label = "Generate Torso Assembly"
	bl_options = {'REGISTER', 'UNDO'}

	limb: StringProperty(
		name="Limb Name",
		description="Base name of the property to store the limb. Example: 'arm', 'leg', 'tail', etc.",
		default="torso"
	)

	lower_torso_bone_count: IntProperty(
		name="Lower Torso Bone Count",
		description="Number of bones in the lower torso",
		default=2
	)

	fk_widget: EnumProperty(
		name="FK Widget",
		description="Type of widget to use for the FK bones",
		items=fk_widget_types,
		default='CIRCLE'
	)

	neck_bone_count: IntProperty(
		name="Neck Bone Count",
		description="Number of bones in the neck",
		default=1
	)

	use_twist_bones: BoolProperty(
		name="Use Twist Bones",
		description="Use twist bones for the neck and/or chest",
		default=True
	)

	neck_twist_bone_count: IntProperty(
		name="Neck Twist Bone Count",
		description="Number of bones in the neck twist",
		default=2
	)

	chest_twist_bone_count: IntProperty(
		name="Chest Twist Bone Count",
		description="Number of bones in the chest twist",
		default=2
	)

	tweak_relationship: EnumProperty(
		name="Tweak Relationship",
		description="Type of relationship for the tweak bones",
		items=[
			('STRETCH_TO', 'Stretch To', 'Stretch the tweak bone to the target bone'),
			('DAMPED_TRACK', 'Damped Track', 'Damped track the tweak bone to the target bone'),
		],
		default='STRETCH_TO'
	)

	assembly_uid: StringProperty(
		name="Assembly UID",
		description="UID of the assembly to use for the torso assembly",
		default="",
		options={'HIDDEN', 'SKIP_SAVE'}
	)

	assembly_uids: StringProperty(
		name="Assembly UIDs",
		description="Comma-separated UIDs for multi-reconfigure; empty = single assembly_uid",
		default="",
		options={'HIDDEN', 'SKIP_SAVE'}
	)

	dialog_chains_json: StringProperty(
		name="Dialog Chains",
		description="Bone chains captured at invoke for dialog/redo UI",
		default="[]",
		options={'HIDDEN', 'SKIP_SAVE'}
	)

	dialog_twist_json: StringProperty(
		name="Dialog Twist Status",
		description="Twist registration snapshot captured at invoke",
		default="{}",
		options={'HIDDEN', 'SKIP_SAVE'}
	)

	template_id: StringProperty(
		name="Template ID",
		description="Torso template to apply on invoke",
		default="",
		options={'HIDDEN'}
	)

	template_name: StringProperty(
		name="Template Name",
		description="Name of the template to use for the torso assembly",
		default="",
		options={'HIDDEN'}
	)

	add_neck_rotation_isolation: BoolProperty(
		name="Add Neck Rotation Isolation",
		description="Add rotation isolation for the neck",
		default=True
	)

	neck_base_property_name: StringProperty(
		name="Neck Base Property Name",
		description="Base property name for the neck",
		default="neck"
	)

	neck_inherit_scale_from_root: BoolProperty(
		name="Neck Inherit Scale From Root",
		description="Inherit scale from the root for the neck",
		default=True
	)

	add_head_rotation_isolation: BoolProperty(
		name="Add Head Rotation Isolation",
		description="Add rotation isolation for the head",
		default=True
	)

	head_base_property_name: StringProperty(
		name="Head Base Property Name",
		description="Base property name for the head",
		default="head"
	)

	head_inherit_scale_from_root: BoolProperty(
		name="Head Inherit Scale From Root",
		description="Inherit scale from the root for the head",
		default=True
	)

	neck_falloff_type: EnumProperty(
		name="Neck Falloff Type",
		description="Type of falloff for the neck",
		items=falloff_presets + [('NONE', "None", "No falloff", '', 5)],
		default='LINEAR'
	)

	@classmethod
	def description(cls, context, properties):
		if properties.template_id:
			template = get_torso_template(properties.template_id)
			if template:
				return template.description
		return "Setup torso assembly"

	##################################################################################################
	# invoke

	def _torso_twist_parents(self, chains):
		"""(neck, chest) parent names matching TorsoFK neck/chest twist parents."""
		neck = []
		chest = []
		for chain in chains:
			n = len(chain)
			first_neck = n - self.neck_bone_count - 1
			chest_index = first_neck - 1
			neck.extend(chain[i] for i in range(first_neck, n - 1) if 0 <= i < n)
			if 0 <= chest_index < n:
				chest.append(chain[chest_index])
		return neck, chest

	def _torso_twist_expected(self, chains):
		"""(parent, count) pairs matching TorsoFK neck/chest twist parents."""
		expected = []
		if not self.use_twist_bones:
			return expected
		neck, chest = self._torso_twist_parents(chains)
		if self.neck_twist_bone_count > 0:
			expected.extend((name, self.neck_twist_bone_count) for name in neck)
		if self.chest_twist_bone_count > 0:
			expected.extend((name, self.chest_twist_bone_count) for name in chest)
		return expected

	def _store_dialog_chains(self, chains):
		self.dialog_chains_json = json.dumps(chains)

	def _store_twist_snapshot(self, context, chains, *, require_chain):
		use_edit = context.object.mode == 'EDIT'
		# The whole chain, because the neck bone count can change while the dialog is open
		parents = [name for chain in chains for name in chain]
		snapshot = snapshot_twist_status(
			context.object.data,
			parents,
			use_edit_bones=use_edit,
			require_chain=require_chain,
		)
		self.dialog_twist_json = json.dumps(snapshot)
		# A count of 0 turns that twist off, so existing bones don't override it
		neck, chest = self._torso_twist_parents(chains)
		neck_count = existing_twist_count(snapshot, neck)
		if neck_count and self.neck_twist_bone_count > 0:
			self.neck_twist_bone_count = neck_count
		chest_count = existing_twist_count(snapshot, chest)
		if chest_count and self.chest_twist_bone_count > 0:
			self.chest_twist_bone_count = chest_count

	def _invoke_from_template(self, context):
		template = get_torso_template(self.template_id)
		if not template:
			self.report({'ERROR'}, f"Unknown torso template: '{self.template_id}'")
			return {'CANCELLED'}

		option_values = resolve_template_options(TorsoAssemblyOptions, template.options)
		for key, value in option_values.items():
			setattr(self, key, value)

		try:
			chains = find_chains_from_selection(context)
		except ChainBranchingError as error:
			self.report({'ERROR'}, str(error))
			return {'CANCELLED'}

		if not chains:
			self.report({'ERROR'}, "No chains selected.")
			return {'CANCELLED'}

		self._store_dialog_chains(chains)
		self._store_twist_snapshot(context, chains, require_chain=True)
		if not self.limb:
			self.limb = guess_limb_name(chains[0][0])

		self.template_name = template.label

	def _invoke_from_assembly(self, context):
		assembly = find_assembly(context.object, self.assembly_uid)
		if not assembly:
			self.report({'ERROR'}, "Assembly not found.")
			return {'CANCELLED'}

		options = assembly.get_options()
		for key, value in options.items():
			setattr(self, key, value)
		self.limb = assembly.limb

		chains = [assembly.get_chain()]
		self._store_dialog_chains(chains)
		self._store_twist_snapshot(context, chains, require_chain=False)
		self.template_name = assembly.template_name
		self.template_id = assembly.template_id

	def invoke(self, context, event):
		show_dialog = True

		if self.assembly_uid:
			result = self._invoke_from_assembly(context)
		else:
			result = self._invoke_from_template(context)
			template = get_torso_template(self.template_id)
			if template:
				show_dialog = template.show_dialog

		if result == {'CANCELLED'}:
			return result

		if show_dialog:
			return context.window_manager.invoke_props_dialog(self, width=350)
		return self.execute(context)

	##################################################################################################
	# draw

	def draw(self, context):
		layout = self.layout
		template = get_torso_template(self.template_id)
		split_size = 0.6

		def field_visible(field_name):
			if field_name in ["neck_base_property_name", "neck_inherit_scale_from_root"]:
				return self.add_neck_rotation_isolation
			if field_name in ["head_base_property_name", "head_inherit_scale_from_root"]:
				return self.add_head_rotation_isolation
			if field_name in ["neck_twist_bone_count", "chest_twist_bone_count"]:
				return self.use_twist_bones

			return True

		draw = TemplateDraw(self, template, split_size=split_size, visible_func=field_visible)

		draw.box_section(layout, ["limb", "lower_torso_bone_count", "neck_bone_count"], 
			"Torso Settings:", "SETTINGS", lambda col: (

			draw.draw_section(col, ["limb"], lambda: (
				draw.split_field(col, "Limb Name:", "limb"),
			)),
			draw.draw_section(col, ["lower_torso_bone_count", "neck_bone_count"], lambda: (
				draw.split_field(col, "Lower Torso Bone Count:", "lower_torso_bone_count"),
				draw.split_field(col, "Neck Bone Count:", "neck_bone_count"),
			)),
		))
		def draw_twist_status(col):
			if not self.use_twist_bones:
				return
			chains = json.loads(self.dialog_chains_json or "[]")
			if not chains:
				col.label(text="No chains selected.", icon='ERROR')
				return
			snapshot = json.loads(self.dialog_twist_json or "{}")
			status, status_icon, message = evaluate_twist_snapshot(snapshot, self._torso_twist_expected(chains))
			if self.assembly_uid and status == TwistChainStatus.OK:
				return
			col.label(text=message, icon=icon(status_icon))

		def draw_twist_count(col, label, prop, parents):
			# Existing twist bones set the count when the dialog opens
			snapshot = json.loads(self.dialog_twist_json or "{}")
			sub = col.column()
			sub.enabled = getattr(self, prop) == 0 or not any(name in snapshot for name in parents)
			draw.full_field(sub, label, prop)

		neck_parents, chest_parents = self._torso_twist_parents(json.loads(self.dialog_chains_json or "[]"))
		draw.draw_section(layout, ["use_twist_bones", "neck_twist_bone_count", "chest_twist_bone_count"], lambda: (
			draw.full_field(layout, "Use Twist Bones", "use_twist_bones"),
			draw.box_section(layout, ["neck_twist_bone_count", "chest_twist_bone_count"], "Twist Bones:", 'MOD_SCREW', lambda col: (
				draw_twist_status(col),
				draw_twist_count(col, "Neck Twist Bone Count:", "neck_twist_bone_count", neck_parents),
				draw_twist_count(col, "Chest Twist Bone Count:", "chest_twist_bone_count", chest_parents),
			)),
		))
		draw.draw_section(layout, ["fk_widget", "tweak_relationship"], lambda: (
			draw.split_field(layout, "FK Widget:", "fk_widget"),
			draw.split_field(layout, "Tweak Relationship:", "tweak_relationship"),
		))

		draw.box_section(layout, ["add_neck_rotation_isolation", "add_head_rotation_isolation", "neck_base_property_name", "neck_inherit_scale_from_root", "head_base_property_name", "head_inherit_scale_from_root"], 
			"Rotation Isolation:", 'SETTINGS', lambda col: (

			draw.draw_section(col, ["add_neck_rotation_isolation", "neck_base_property_name", "neck_inherit_scale_from_root"], lambda: (
				draw.split_row(col, [
					SplitSection(label="Add Neck Rotation Isolation", prop="add_neck_rotation_isolation"),
					SplitSection(label="", prop="neck_base_property_name"),
				]),
				draw.indented_field(col, "Neck Inherit Scale From Root", "neck_inherit_scale_from_root"),
			)),

			draw.draw_section(col, ["add_head_rotation_isolation", "head_base_property_name", "head_inherit_scale_from_root"], lambda: (
				draw.split_row(col, [
					SplitSection(label="Add Head Rotation Isolation", prop="add_head_rotation_isolation"),
					SplitSection(label="", prop="head_base_property_name"),
				]),
				draw.indented_field(col, "Head Inherit Scale From Root", "head_inherit_scale_from_root"),
			)),
		))

		draw.draw_section(layout, ["neck_falloff_type"], lambda: (
			draw.split_field(layout, "Neck Falloff:", "neck_falloff_type"),
		))

	##################################################################################################
	# execute

	def validate_chains(self, context, chains):
		if not chains:
			return "No chains selected."
		for chain in chains:
			if len(chain) == 1:
				return "All chains must have at least 2 bones."
		return None

	def execute(self, context):
		if not self.limb:
			self.report({'ERROR'}, "Limb name is required.")
			self.assembly_uid = ""
			return {'CANCELLED'}

		err = validate_setup_context(
			context,
			check_property_bone=self.add_neck_rotation_isolation or self.add_head_rotation_isolation,
		)
		if err:
			self.report({'ERROR'}, err)
			self.assembly_uid = ""
			return {'CANCELLED'}

		options = TorsoAssemblyOptions(
			limb=self.limb.strip().lower(),
			lower_torso_bone_count=self.lower_torso_bone_count,
			neck_bone_count=self.neck_bone_count,
			use_twist_bones=self.use_twist_bones,
			neck_twist_bone_count=self.neck_twist_bone_count,
			chest_twist_bone_count=self.chest_twist_bone_count,
			tweak_relationship=self.tweak_relationship,
			add_neck_rotation_isolation=self.add_neck_rotation_isolation,
			neck_base_property_name=self.neck_base_property_name,
			neck_inherit_scale_from_root=self.neck_inherit_scale_from_root,
			add_head_rotation_isolation=self.add_head_rotation_isolation,
			head_base_property_name=self.head_base_property_name,
			head_inherit_scale_from_root=self.head_inherit_scale_from_root,
			fk_widget=self.fk_widget,
			neck_falloff_type=self.neck_falloff_type,
		)

		prev_state = begin_setup_edit(context)

		assembly_uids = [u for u in self.assembly_uids.split(',') if u] or [self.assembly_uid]
		if self.assembly_uid or len(assembly_uids) > 1:
			rebuild_chains = {uid: find_assembly(context.object, uid).get_chain() for uid in assembly_uids}
			chains = list(rebuild_chains.values())
		else:
			rebuild_chains = {}
			try:
				chains = find_chains_from_selection(context)
			except Exception as e:
				self.report({'ERROR'}, str(e))
				self.assembly_uid = ""
				prev_state.restore(context)
				return {'CANCELLED'}

		err = self.validate_chains(context, chains)
		if err:
			self.report({'ERROR'}, err)
			self.assembly_uid = ""
			prev_state.restore(context)
			return {'CANCELLED'}

		def create(uids, chains, prior_configs):
			return create_torso_assembly(
				context,
				chains,
				self.template_id,
				self.template_name,
				options,
				replacement_uids=uids,
				prior_configs=prior_configs,
			)

		def build():
			if len(rebuild_chains) > 0:
				prior_configs = prepare_rebuild(context, assembly_uids)
				return create(assembly_uids, [rebuild_chains[uid] for uid in assembly_uids], prior_configs)
			else:
				return create(None, chains, {})

		try:
			with profile():
				torso_controls = run_assembly_transaction(build)
		except AssemblyTransactionError as e:
			self.report({'ERROR'}, str(e))
			prev_state.restore(context)
			return {'CANCELLED'}

		if torso_controls:
			if context.object.mode != 'POSE':
				bpy.ops.object.mode_set(mode='POSE')
			select_bones(context.object, torso_controls, deselect=True)

		chain_count = len(chains)
		self.report({'INFO'}, f"Successfully generated {chain_count} torso assembl{'ies' if chain_count != 1 else 'y'}.")
		prev_state.restore_mirror(context)
		return {'FINISHED'}


classes = (
	RIG_OT_advanced_torso_setup,
)


def register():
	validate_torso_templates()
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()

	bpy.ops.rig.advanced_torso_setup('INVOKE_DEFAULT')
