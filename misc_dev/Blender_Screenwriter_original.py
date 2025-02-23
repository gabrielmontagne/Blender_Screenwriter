bl_info = {
    "name": "Blender Screenwriter with Fountain Live Preview",
    "author": "Tintwotin,  Andrea Monzini, Fountain Module by Colton J. Provias & Manuel Senfft, Export Module by Martin Vilcans. Fountain Format by Nima Yousefi & John August",
    "version": (0, 1),
    "blender": (2, 81, 0),
    "location": "Text Editor > Sidebar",
    "description": "Adds functions for editing of Fountain file with live screenplay preview",
    "warning": "",
    "wiki_url": "",
    "category": "Text Editor",
}

import bpy
import textwrap
import subprocess
import os
import sys
import fountain
from bpy.props import IntProperty, BoolProperty, PointerProperty, StringProperty, EnumProperty
from pathlib import Path

from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator


def get_mergables(areas):
    xs, ys = dict(), dict()
    for a in areas:
        xs[a.x] = a
        ys[a.y] = a
    for area in reversed(areas):
        tx = area.x + area.width + 1
        ty = area.y + area.height + 1
        if tx in xs and xs[tx].y == area.y and xs[tx].height == area.height:
            return area, xs[tx]
        elif ty in ys and ys[ty].x == area.x and ys[ty].width == area.width:
            return area, ys[ty]
    return None, None


def teardown(context):
    while len(context.screen.areas) > 1:
        a, b = get_mergables(context.screen.areas)
        if a and b:
            bpy.ops.screen.area_join(cursor=(a.x, a.y))  #,max_x=b.x,max_y=b.y)
            area = context.screen.areas[0]
            region = area.regions[0]
            blend_data = context.blend_data
            bpy.ops.screen.screen_full_area(
                dict(
                    screen=context.screen,
                    window=context.window,
                    region=region,
                    area=area,
                    blend_data=blend_data))
            bpy.ops.screen.back_to_previous(
                dict(
                    screen=context.screen,
                    window=context.window,
                    region=region,
                    area=area,
                    blend_data=blend_data))


def split_area(window,
               screen,
               region,
               area,
               xtype,
               direction="VERTICAL",
               factor=0.5,
               mouse_x=-100,
               mouse_y=-100):
    beforeptrs = set(list((a.as_pointer() for a in screen.areas)))
    bpy.ops.screen.area_split(
        dict(region=region, area=area, screen=screen, window=window),
        direction=direction,
        factor=factor)
    afterptrs = set(list((a.as_pointer() for a in screen.areas)))
    newareaptr = list(afterptrs - beforeptrs)
    newarea = area_from_ptr(newareaptr[0])
    newarea.type = xtype
    return newarea


def area_from_ptr(ptr):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.as_pointer() == ptr:
                return area


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
        layout.operator("text.dual_view")
        layout.operator("scene.preview_fountain")
        repl = context.scene.text_replace
        layout.prop(repl, "enabled")
        layout.operator("text.scenes_to_strips")


class SCREENWRITER_OT_preview_fountain(bpy.types.Operator):
    '''Updates the preview'''
    bl_idname = "scene.preview_fountain"
    bl_label = "Refresh"

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        filepath = bpy.context.area.spaces.active.text.filepath
        if filepath.strip() == "": return False
        return ((space.type == 'TEXT_EDITOR')
                and Path(filepath).suffix == ".fountain")

    def execute(self, context):
        space = bpy.context.space_data
        dir = os.path.dirname(bpy.data.filepath)
        if not dir in sys.path:
            sys.path.append(dir)

        current_text = os.path.basename(bpy.context.space_data.text.filepath)
        if current_text.strip() == "": return

        fountain_script = bpy.context.area.spaces.active.text.as_string()
        if fountain_script.strip() == "": return {"CANCELLED"}

        F = fountain.Fountain(fountain_script)

        filename = "Preview.txt"

        if filename not in bpy.data.texts:
            bpy.data.texts.new(filename)  # New document in Text Editor
        else:
            bpy.data.texts[filename].clear()  # Clear existing text

        # Get number of header lines
        contents = fountain_script.strip().replace('\r', '')

        contents_has_metadata = ':' in contents.splitlines()[0]
        contents_has_body = '\n\n' in contents

        if contents_has_metadata and contents_has_body:
            lines = fountain_script.split('\n\n')
            lines = lines[0].splitlines()
            current_line = bpy.data.texts[current_text].current_line_index - len(
                lines) - 1
        # elif contents_has_metadata and not contents_has_body:
        # self._parse_head(contents.splitlines())
        else:
            current_line = bpy.data.texts[current_text].current_line_index

        current_character = bpy.data.texts[current_text].current_character
        jump_to_line = 0
        margin = " " * 4
        document_width = 60 + len(margin)
        action_wrapper = textwrap.TextWrapper(width=document_width)
        dialogue_wrapper = textwrap.TextWrapper(
            width=37 + int(len(margin) / 2))
        dialogue_indentation = 13 + int(len(margin) / 2)
        cursor_indentation = margin
        add_lines = 0
        add_characters = current_character
        cursor_indentation_actual = ""
        text = bpy.context.area.spaces.active.text
        current_line_length = len(text.current_line.body)
        add_lines_actual = 0
        add_characters_actual = 0

        # This is the way to use title stuff
        # for meta in iter(F.metadata.items()):
        # if meta[0] == 'title':
        # bpy.data.texts[filename].write((str(meta[1])).center(document_width)+chr(10))

        add_lines = 0 

        for fc, f in enumerate(F.elements):
            add_lines = -1 
            #add_lines = 0  #int(document_width/current_character)
            add_characters = current_character
            if f.element_type == 'Scene Heading':
                if str(f.scene_number) != "": f.scene_number = f.scene_number+ " "
                bpy.data.texts[filename].write(
                    margin + f.scene_number+ f.scene_abbreviation.upper() + " " + f.element_text.upper() +
                    chr(10))
                   
                cursor_indentation = margin
            elif f.element_type == 'Action' and f.is_centered == False:
                action = f.element_text
                action_list = action_wrapper.wrap(text=action)
                add_action_lines = 0
                
                for action in action_list:
                    bpy.data.texts[filename].write(margin + action + chr(10))
                cursor_indentation = margin
            elif f.element_type == 'Action' and f.is_centered == True:
                bpy.data.texts[filename].write(
                    margin + f.element_text.center(document_width) + chr(10))
                cursor_indentation = margin + ("_" * (int(
                    (document_width / 2 - len(f.element_text) / 2)) - 2))
            elif f.element_type == 'Character':
                bpy.data.texts[filename].write(
                    margin + f.element_text.center(document_width).upper() +
                    chr(10))  # .upper()
                cursor_indentation = margin + ("_" * ((f.element_text.center(
                    document_width)).find(f.element_text)))
            elif f.element_type == 'Parenthetical':
                bpy.data.texts[filename].write(
                    margin + f.element_text.center(document_width).lower() +
                    chr(10))  # .lower()
                cursor_indentation = margin + ("_" * int(
                    (document_width / 2 - len(f.element_text) / 2)))
            elif f.element_type == 'Dialogue':
                dialogue = f.element_text
                current_character
                line_list = dialogue_wrapper.wrap(text=dialogue)
                for dialogue in line_list:
                    bpy.data.texts[filename].write(margin + (
                        " " * dialogue_indentation + dialogue) + chr(10))
                    # if add_characters >= len(dialogue):
                    # add_characters = add_characters-len(dialogue)
                    # add_lines += 1
                cursor_indentation = margin + (" " * dialogue_indentation
                                               )  # + (" "*add_characters)
            elif f.element_type == 'Synopsis':  # Ignored by Fountain formatting
                bpy.data.texts[filename].write(chr(10))
            elif f.element_type == 'Page Break':
                bpy.data.texts[filename].write(
                    chr(10) + margin + ("_" * document_width) + chr(10))
            elif f.element_type == 'Boneyard':  # Ignored by Fountain formatting
                bpy.data.texts[filename].write(chr(10))
            elif f.element_type == 'Comment':  # Ignored by Fountain formatting
                bpy.data.texts[filename].write(chr(10))
            elif f.element_type == 'Section Heading':  # Ignored by Fountain formatting
                bpy.data.texts[filename].write(chr(10))
            elif f.element_type == 'Transition':
                bpy.data.texts[filename].write(
                    margin + f.element_text.rjust(document_width).upper() + chr(10))
                cursor_indentation = margin + ("_" * (
                    document_width - len(f.element_text)))
            elif f.element_type == 'Empty Line':
                bpy.data.texts[filename].write(chr(10))
            #print("org "+str(f.original_line))
            #print("cur "+str(current_line))
            if current_line >= f.original_line and f.original_line != 0:  #current_line
                jump_to_line = bpy.data.texts[filename].current_line_index
                cursor_indentation_actual = cursor_indentation
                add_lines_actual = add_lines
                #print("add line: "+str(add_lines_actual))
                #add_characters_actual = add_characters
        #print("Jump: "+str(jump_to_line))

        line = jump_to_line - 1 #- add_lines_actual
        if line < 0: line = 0
        bpy.data.texts[filename].current_line_index = line
        cur = current_character + len(cursor_indentation_actual)  #+ add_characters_actual
        #print("Character:" + str(cur)+" Line: "+str((line)))
        bpy.data.texts[filename].select_set(line, cur, line, cur)

        return {"FINISHED"}


class TEXT_OT_dual_view(bpy.types.Operator):
    '''Toggles screenplay preview'''
    bl_idname = "text.dual_view"
    bl_label = "Preview"

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        filepath = bpy.context.area.spaces.active.text.filepath
        if filepath.strip() == "": return False
        return ((space.type == 'TEXT_EDITOR')
                and Path(filepath).suffix == ".fountain")

    original_area = None

    def execute(self, context):
        main_scene = bpy.context.scene
        count = 0
        original_type = bpy.context.area.type

        # # setting font (on Windows) not working
        # try:
        # for a in bpy.context.screen.areas:
        # if a.type == 'PREFERENCES':
        # bpy.context.area.type ="PREFERENCES"
        # bpy.context.preferences.view.font_path_ui_mono("C:\\Windows\\Fonts\\Courier.ttf")
        # break
        # except RuntimeError as ex:
        # error_report = "\n".join(ex.args)
        # print("Caught error:", error_report)
        # #pass
        bpy.context.area.type = original_type
        self.original_area = context.area
        original = context.copy()
        thisarea = context.area
        otherarea = None
        tgxvalue = thisarea.x + thisarea.width + 1
        thistype = context.area.type

        arealist = list(context.screen.areas)

        filename = "Preview.txt"
        if filename not in bpy.data.texts:
            bpy.ops.scene.preview_fountain()

            fountain_script = bpy.context.area.spaces.active.text.as_string()
            if fountain_script.strip() == "":
                msg = "Text-block can't be empty!"
                self.report({'INFO'}, msg)
                return {"CANCELLED"}

        for area in context.screen.areas:
            if area == thisarea:
                continue
            elif area.x == tgxvalue and area.y == thisarea.y:
                otherarea = area
                break

        if otherarea:  #leave trim-mode

            # The 2.81 API doesn't have an option for automatic joining.
            bpy.ops.screen.area_join(
                'INVOKE_DEFAULT',
                cursor=(otherarea.x, otherarea.y + int(otherarea.height / 2)))

            # normal settings
            bpy.ops.screen.screen_full_area()
            bpy.ops.screen.screen_full_area()
            override = context.copy()
            area = self.original_area
            override['area'] = area
            override['space_data'] = area.spaces.active

            return {"FINISHED"}

        else:  # enter dual-mode

            areax = None

            #split
            window = context.window
            region = context.region
            screen = context.screen
            main = context.area

            main.type = "TEXT_EDITOR"
            ctrlPanel = bpy.ops.screen.area_split(
                direction="VERTICAL")  #, factor=0.7)

            #settings for preview 2.
            bpy.ops.screen.screen_full_area()
            bpy.ops.screen.screen_full_area()
            override = original
            area = self.original_area
            override['area'] = area
            override['space_data'] = area.spaces.active
            override['space_data'].text = bpy.data.texts['Preview.txt']
            override['space_data'].show_region_ui = False
            override['space_data'].show_region_header = False
            override['space_data'].show_region_footer = False
            override['space_data'].show_line_numbers = False
            override['space_data'].show_syntax_highlight = False
            override['space_data'].show_word_wrap = False

            for area in context.screen.areas:
                if area not in arealist:
                    areax = area
                    break

            if areax:
                areax.type = thistype
                return {"FINISHED"}

        return {"CANCELLED"}


handler = None


def get_space(context):
    for area in context.screen.areas:
        if area.type == "TEXT_EDITOR":
            return area.spaces.active


def text_handler(spc, context):

    scene = bpy.context.scene
    text = bpy.context.area.spaces.active.text
    line = text.current_line.body
    current_text = os.path.basename(bpy.context.space_data.text.filepath)
    if current_text.strip() == "": return
    current_character = bpy.data.texts[current_text].current_character

    if not text:
        return

    if scene.last_line is None and scene.last_line_index != text.current_line_index:
        scene.last_line = line
        scene.last_line_index = text.current_line_index

    if scene.last_character is None:  # scene.last_character != current_character:
        scene.last_character = current_character

    if line != scene.last_line or len(line) != len(scene.last_line):
        bpy.ops.scene.preview_fountain()
    elif current_character != scene.last_character:
        bpy.ops.scene.preview_fountain()

    scene.last_line = line
    scene.last_character = current_character


def redraw(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'TEXT_EDITOR':
                area.tag_redraw()


def activate_handler(self, context):
    global handler

    spc = get_space(context)
    if not spc:
        return

    enabled = context.scene.text_replace.enabled

    if enabled:
        handler = spc.draw_handler_add(text_handler, (
            spc,
            context,
        ), "WINDOW", "POST_PIXEL")
        print("handler activated", handler)
    else:
        if handler is not None:
            spc.draw_handler_remove(handler, "WINDOW")
        handler = None
        print("handler deactivated")


class TextReplaceProperties(bpy.types.PropertyGroup):
    enabled: BoolProperty(
        name="Live Preview",
        description="Enables live screenplay preview",
        update=activate_handler,
        default=False)

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        filepath = bpy.context.area.spaces.active.text.filepath
        if filepath.strip() == "": return False
        return ((space.type == 'TEXT_EDITOR')
                and Path(filepath).suffix == ".fountain")

    def execute(self, context):
        return {"FINISHED"}


class SCREENWRITER_OT_export(Operator, ExportHelper):
    """Export Screenplay"""
    bl_idname = "export.screenplay"
    bl_label = "Export"

    filename_ext = ""

    filter_glob: StringProperty(
        default="*.html;*.pdf;*.fdx",
        options={'HIDDEN'},
        maxlen=255,
    )
    # ("PDF", "pdf", "Exports pdf"), #not working currently
    opt_exp: EnumProperty(
        items=(("HTML", "Html", "Exports html"), ("PDF", "pdf", "Exports pdf"), ("FDX", "fdx", "Final Draft")),
        name="Export Data Type",
        description="Choose what format to export ",
        default="HTML")
    open_browser: BoolProperty(
        name="Open in Browser",
        description="Open exported html or pdf in browser",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        filepath = bpy.context.area.spaces.active.text.filepath
        if filepath.strip() == "": return False
        return ((space.type == 'TEXT_EDITOR')
                and Path(filepath).suffix == ".fountain")

    def execute(self, context):
        return screenplay_export(context, self.filepath, self.opt_exp,
                                 self.open_browser)


def screenwriter_menu_export(self, context):
    self.layout.separator()
    self.layout.operator(
        SCREENWRITER_OT_export.bl_idname, text="Export Screenplay")


def screenplay_export(context, screenplay_filepath, opt_exp, open_browser):

    import os
    dir = os.path.dirname(bpy.data.filepath)
    if not dir in sys.path:
        sys.path.append(dir)

    fountain_script = bpy.context.area.spaces.active.text.as_string()
    if fountain_script.strip() == "": return {"CANCELLED"}

    # screenplain
    try:
        import screenplain
    except ImportError:
        print('Installing screenplain module (this is only required once)...')
        import urllib.request as urllib
        import zipfile
        import shutil

        url = 'https://github.com/vilcans/screenplain/archive/0.8.0.zip'
        home_url = bpy.utils.script_path_user() + "\\addons\\"
        urllib.urlretrieve(url, home_url + 'screenplain-0.8.0.zip')
        with zipfile.ZipFile(home_url + 'screenplain-0.8.0.zip', 'r') as z:
            z.extractall(home_url)
        target_dir = home_url
        shutil.move(home_url + 'screenplain-0.8.0/screenplain', target_dir)
        os.remove(home_url + 'screenplain-0.8.0.zip')
        shutil.rmtree(home_url + 'screenplain-0.8.0')
        import screenplain

    import screenplain.parsers.fountain as fountain
    from io import StringIO
    import webbrowser
    s = StringIO(fountain_script)
    screenplay = fountain.parse(s)
    output = StringIO()
    if opt_exp == "HTML":
        from screenplain.export.html import convert
        convert(screenplay, output, bare=False)
    if opt_exp == "FDX":
        from screenplain.export.fdx import to_fdx
        to_fdx(screenplay, output)
    if opt_exp == "PDF":
        from screenplain.export.pdf import to_pdf
        to_pdf(screenplay, output)
    sp_out = output.getvalue()
    filename, extension = os.path.splitext(screenplay_filepath)
    fileout_name = filename + "." + opt_exp.lower()
    file = open(fileout_name, "w")
    file.write(sp_out)
    file.close()
    if open_browser:
        if opt_exp == "HTML" or opt_exp == "PDF":
            webbrowser.open(fileout_name)

    return {'FINISHED'}


class TEXT_OT_scenes_to_strips(bpy.types.Operator):
    """Convert screenplay data to scene and text strips"""
    bl_idname = "text.scenes_to_strips"
    bl_label = "Create Sequence"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        filepath = bpy.context.area.spaces.active.text.filepath
        return ((space.type == 'TEXT_EDITOR') and
                Path(filepath).suffix == ".fountain")

    def execute(self, context):

        fountain_script = bpy.context.area.spaces.active.text.as_string()
        if fountain_script.strip() == "": return {"CANCELLED"}

        F = fountain.Fountain(fountain_script)

        if not bpy.context.scene.sequence_editor:
            bpy.context.scene.sequence_editor_create()   

        addSceneChannel = 1
        previous_time = 0
        previous_line = 0
        lines_pr_minute = 59
        first_duration = 0
        render = bpy.context.scene.render
        fps = round((render.fps / render.fps_base), 3)
        count = 0
        f_collected = []
        duration = 0
        
        for fc, f in enumerate(F.elements):
            if f.element_type == 'Scene Heading':
                f_collected.append(f)

        for fc, f in enumerate(f_collected):
            if str(f.scene_number) != "": f.scene_number = f.scene_number+ " "
            name = str(f.scene_number + f.element_text.title())
            new_scene = bpy.data.scenes.new(name=name)

            cam = bpy.data.cameras.new("Camera")
            cam.lens = 35
            cam_obj1 = bpy.data.objects.new("Camera", cam)
            cam_obj1.location = (9.69, -10.85, 12.388)
            cam_obj1.rotation_euler = (0.6799, 0, 0.8254)
            new_scene.collection.objects.link(cam_obj1)

            if fc == 0:
                for ec, e in enumerate(f_collected):
                    if ec == fc + 1:
                        first_duration = int((((e.original_line)/lines_pr_minute)*60)*fps)
                        duration = first_duration
                print("Fc "+str(e.original_line)+" ec "+str(f.original_line))
            else:
                for ec, e in enumerate(f_collected):
                    if ec == fc+1:            
                        duration = int((((e.original_line - f.original_line)/lines_pr_minute)*60)*fps)
                        
            in_time =  duration + previous_time
            bpy.data.scenes[name].frame_start = 0
            bpy.data.scenes[name].frame_end = duration
            newScene=bpy.context.scene.sequence_editor.sequences.new_scene(f.element_text.title(), new_scene, addSceneChannel, previous_time)
            bpy.context.scene.sequence_editor.sequences_all[newScene.name].scene_camera = bpy.data.objects[cam.name]
            #bpy.context.scene.sequence_editor.sequences_all[newScene.name].animation_offset_start = 0
            bpy.context.scene.sequence_editor.sequences_all[newScene.name].frame_final_end = in_time
            bpy.context.scene.sequence_editor.sequences_all[newScene.name].frame_start = previous_time
            previous_time = in_time
            previous_line = f.original_line
            
        bpy.ops.sequencer.set_range_to_strips()

        characters_pr_minute = 900
        for fc, f in enumerate(F.elements):
            if f.element_type == 'Dialogue':
                name = str(f.element_text)
                duration = int(((len(f.original_content)/characters_pr_minute)*60)*fps)
                in_time = int(((f.original_line/lines_pr_minute)*60)*fps)
                
                text_strip = bpy.context.scene.sequence_editor.sequences.new_effect(
                    name=name,
                    type='TEXT',
                    channel=addSceneChannel+1,
                    frame_start=in_time,
                    frame_end=in_time + duration
                    )
                text_strip.font_size = int(bpy.context.scene.render.resolution_y/18)
                text_strip.text = str(name)
                text_strip.use_shadow = True
                text_strip.select = True
                text_strip.wrap_width = 0.85
                text_strip.location[1] = 0.10
                text_strip.blend_type = 'ALPHA_OVER'

        return {'FINISHED'}


def register():
    bpy.utils.register_class(SCREENWRITER_PT_panel)
    bpy.utils.register_class(SCREENWRITER_OT_preview_fountain)
    bpy.utils.register_class(TEXT_OT_dual_view)
    bpy.utils.register_class(SCREENWRITER_OT_export)
    bpy.types.TEXT_MT_text.append(screenwriter_menu_export)
    bpy.utils.register_class(TEXT_OT_scenes_to_strips)

    bpy.types.Scene.last_character = IntProperty(default=0)
    bpy.types.Scene.last_line = StringProperty(default="")
    bpy.types.Scene.last_line_index = IntProperty(default=0)

    bpy.utils.register_class(TextReplaceProperties)
    bpy.types.Scene.text_replace = PointerProperty(type=TextReplaceProperties)


def unregister():
    bpy.utils.unregister_class(SCREENWRITER_PT_panel)
    bpy.utils.unregister_class(SCREENWRITER_OT_preview_fountain)
    bpy.utils.unregister_class(TEXT_OT_dual_view)
    bpy.utils.unregister_class(SCREENWRITER_OT_export)
    bpy.types.TEXT_MT_text.remove(screenwriter_menu_export)
    bpy.utils.unregister_class(TEXT_OT_scenes_to_strips)

    del bpy.types.Scene.last_character
    del bpy.types.Scene.last_line
    del bpy.types.Scene.last_line_index

    bpy.utils.unregister_class(TextReplaceProperties)
    del bpy.types.Scene.text_replace


if __name__ == "__main__":
    register()
