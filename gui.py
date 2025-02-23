import bpy

class SCREENWRITER_PT_panel(bpy.types.Panel):
    """Preview fountain script as formatted screenplay"""
    bl_label = "Screenwriter"
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Text"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row(align=True)
        row.operator("screenwriter.dual_view")
        row.operator("scene.preview_fountain", text="", icon="FILE_REFRESH")
        repl = context.scene.text_replace
        layout.prop(repl, "enabled")


class SCREENWRITER_PT_sequencer_panel(bpy.types.Panel):
    """Screenwriter Sequencer Options"""
    bl_label = "Sequencer"
    bl_parent_id = "SCREENWRITER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Text"

    def draw(self, context):
        self.layout.operator("text.scenes_to_strips")
        self.layout.operator("text.switch_to_scene")


def screenwriter_menu_export(self, context):
    self.layout.separator()
    self.layout.operator("export.screenplay", text="Export Screenplay")
