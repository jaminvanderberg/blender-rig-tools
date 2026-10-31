assembly workpad?  probably not anymore?

further down the line: rename limb_property_base_name to limb? Store on assembly rather than options?

property names data class

cleanup main folder?

pick twist bone count based on existing twist bones, don't let use change (unless there are none)

language packs?

weight pain proxy on a single chain is a cylinder?

default arm to FK?

preserve hand-edited widgets/shape settings across reconfigure? (store them?)

improve template draw?

remove name string and separators from preferences

Only selects one assembly on reconfigure

XZ Scale Fix not deleting.

side is stored as the raw bone suffix (".R", "_R", ".R.001"), so ".R" and "_R" are different limbs, "-R" isn't a side at all, and get_side_letter / same_side_names / side_display_name / get_base_name / flip_side_name each re-parse it their own way. Store L/R/C + instance separately; keep the suffix only for building names.