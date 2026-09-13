import bpy
from dataclasses import dataclass, field
from rigtools.utils.bone import generate_bone_name, duplicate_bone, set_bone_collection
from rigtools.utils.widget import get_widget_collection, create_circle_widget, create_sphere_widget
from rigtools.armature_settings import get_armature_settings
from rigtools.preferences import get_preferences

@dataclass
class FKTweakChain:
	name: str
	original_bones: list[str] = field(default_factory=list)
	fk_bones: list[str] = field(default_factory=list)
	tweak_bones: list[str] = field(default_factory=list)
	terminal_tweak: str = ""
	bone_lengths: dict[str, float] = field(default_factory=dict)

@dataclass
class TweakChainOptions:
	fk_bone_template: str = "FK-{name}"
	skip_first_tweak: bool = False
	do_create_fk: bool = True
	do_create_fk_widgets: bool = False
	tweak_collection_name: str = ""
	fk_collection_name: str = ""

def create_tweak_chain_edit_mode(armature_data, chain_bone_names, options: TweakChainOptions) -> FKTweakChain :
	prefs = get_preferences()
	bpy.ops.object.mode_set(mode='EDIT')

	chain_name = generate_bone_name(chain_bone_names[0], "{name}")
	chain = FKTweakChain(
		name = chain_name,
		original_bones = chain_bone_names
	)
	
	edit_bones = armature_data.edit_bones
	
	total_length = sum(edit_bones[name].length for name in chain_bone_names)
	avg_length = total_length / len(chain_bone_names)
	tweak_length = avg_length * 0.25
	
	last_parent = edit_bones[chain_bone_names[0]].parent
	
	for bone_name in chain_bone_names:
		org_bone = edit_bones[bone_name]
		chain.bone_lengths[bone_name] = org_bone.length

		if options.do_create_fk:
			fk_name = generate_bone_name(bone_name, options.fk_bone_template)
			fk_bone = duplicate_bone(armature_data, org_bone, fk_name, 1.0)
			fk_bone.parent = last_parent

			chain.fk_bones.append(fk_bone.name)
		
			last_parent = fk_bone

			if options.fk_collection_name:
				set_bone_collection(armature_data, fk_bone, options.fk_collection_name)

		if options.skip_first_tweak and bone_name == chain_bone_names[0]:
			chain.tweak_bones.append("")
			continue
		
		tweak_name = generate_bone_name(bone_name, prefs.tweak_template)
		tweak_bone = duplicate_bone(armature_data, org_bone, tweak_name, 1)
		tweak_bone.length = tweak_length
		
		if options.do_create_fk:
			tweak_bone.parent = fk_bone
		else:
			tweak_bone.parent = last_parent
			last_parent = tweak_bone
		
		chain.tweak_bones.append(tweak_bone.name)

		if options.tweak_collection_name:
			set_bone_collection(armature_data, tweak_bone, options.tweak_collection_name)

	# Create terminal (tip) tweak bone            
	last_org_bone = edit_bones[chain_bone_names[-1]]
	term_name = generate_bone_name(chain_bone_names[-1], prefs.term_template)
	term_bone = edit_bones.new(term_name)
	if options.do_create_fk:
		term_bone.parent = last_parent

	for coll in last_org_bone.collections:
		coll.assign(term_bone)
	
	term_bone.head = last_org_bone.tail
	direction = (last_org_bone.tail - last_org_bone.head).normalized()
	term_bone.tail = last_org_bone.tail + (direction * tweak_length)
	term_bone.roll = last_org_bone.roll

	if options.tweak_collection_name:
		set_bone_collection(armature_data, term_bone, options.tweak_collection_name)
	
	chain.terminal_tweak = term_bone.name
	
	# Parent ORG bones to Tweak
	for i in range(len(chain_bone_names)):
		org_name = chain_bone_names[i]
		org_bone = edit_bones[org_name]
		org_bone.use_connect = False
		if not chain.tweak_bones[i]: # Skip first tweak
			if not options.do_create_fk:
				continue # Leave the bone parented to the last parent
			fk_bone = edit_bones[chain.fk_bones[i]]
			org_bone.parent = fk_bone
		else:
			tweak_bone = edit_bones[chain.tweak_bones[i]]
			org_bone.parent = tweak_bone
		
	# Children of the last bone need to be children of the terminal tweak bone instead
	last_children = [c for c in last_org_bone.children if c.name not in chain_bone_names]
	for child in last_children:
		child.use_connect = False
		child.parent = term_bone
		
	return chain

def create_tweak_chain_pose_mode(context, obj, chain: FKTweakChain, options: TweakChainOptions):
	prefs = get_preferences()
	pose_bones = obj.pose.bones
	settings = get_armature_settings(obj.data, context)

	if obj.mode != 'POSE':
		bpy.ops.object.mode_set(mode='POSE')

	# Targets for original bones: [T1, T2, T3, ..., T_END]
	targets = chain.tweak_bones[1:] + [chain.terminal_tweak]

	for orig_name, target_tweak in zip(chain.original_bones, targets):
		pbone = pose_bones[orig_name]

		c_name = "Stretch To Tweak"
		constraint = pbone.constraints.get(c_name)
		if not constraint:
			constraint = pbone.constraints.new(type='STRETCH_TO')
			constraint.name = c_name

		constraint.target = obj
		constraint.subtarget = target_tweak
		constraint.volume = 'VOLUME_XZX'
		constraint.rest_length = chain.bone_lengths[orig_name]

	# Bone Colors
	tweakers = [t for t in chain.tweak_bones if t] + [chain.terminal_tweak]
	
	for fk_name in chain.fk_bones:
		fk_bone = pose_bones[fk_name]
		fk_bone.color.palette = prefs.fk_bone_color
		
	for tweak_name in tweakers:
		tweak_bone = pose_bones[tweak_name]
		tweak_bone.color.palette = prefs.tweak_bone_color
		

	# Widgets
	coll = get_widget_collection(context, settings.widget_collection)
	if settings.do_create_widgets and options.do_create_fk_widgets:
		for fk_name in chain.fk_bones:
			fk_bone = pose_bones[fk_name]
			widget_name = generate_bone_name(fk_name, settings.widget_template)
			wgt = create_circle_widget(widget_name, coll)
			fk_bone.custom_shape = wgt
		
	if settings.do_create_widgets:
		for tweak_name in tweakers:
			tweak_bone = pose_bones[tweak_name]
			widget_name = generate_bone_name(tweak_name, settings.widget_template)
			wgt = create_sphere_widget(widget_name, coll)
			tweak_bone.custom_shape = wgt
