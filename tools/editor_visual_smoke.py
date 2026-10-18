"""Real Tk checks for decoded map graphics and reversible marker dragging."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(env, work):
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from adventure_editing import scene_markers
    from editor_model import ProjectDocument, create_project
    from roster_editor import RosterEditor

    os.environ["DISPLAY"] = env["DISPLAY"]
    work = Path(work)

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    def fail_dialog(title, message, **kwargs):
        raise AssertionError(f"{title}: {message}")

    with tempfile.TemporaryDirectory(prefix="editor-graphics-ui-", dir=work) as directory:
        tmp = Path(directory)
        tool = ROOT / "build/btp-project"
        doc = create_project(ROOT / "examples/battletech-demo", tmp / "game",
                             "visual-editor-smoke", "Visual editor smoke", tool)
        window = tk.Tk()
        callback_errors = []
        window.report_callback_exception = lambda kind, value, traceback: callback_errors.append(value)

        def pump():
            window.update()
            if callback_errors:
                raise callback_errors.pop(0)

        def screenshot(label, subject):
            subject.lift()
            pump()
            assert subject.winfo_width() <= subject.winfo_screenwidth()
            assert subject.winfo_height() <= subject.winfo_screenheight()
            ImageGrab.grab(xdisplay=env["DISPLAY"]).save(work / f"editor-graphics-{label}.png")

        with patch.object(messagebox, "showerror", fail_dialog):
            try:
                app = RosterEditor(window, tool, tmp / "settings")
                app.settings["data"] = str(ROOT / "Original DOS")
                app.set_document(doc)
                window.geometry("1000x740+8+8")
                pump()
                screenshot("main", window)
                app.edit_adventure()
                ed = app.map_editor
                ed.window.geometry("1000x720+8+8")
                pump()
                assert {"chi:land", "chi:destroyed"}.issubset(ed.graphics), ed.graphics_note.get()
                assert all(ed.brush.item(str(i), "image") for i in range(len(doc.adventure["tiles"])))
                assert "Graphics ready" in ed.graphics_note.get()
                for sheet in ("chi:land", "chi:destroyed"):
                    for graphic, size in [(0, 16), (100, 24), (249, 32)]:
                        image = ed.tile_image(sheet, graphic, size)
                        assert image is ed.tile_image(sheet, graphic, size)
                        for x, y in [(0, 0), (7, 11), (size - 1, size - 1)]:
                            color = ed.graphics[sheet][graphic][y * 16 // size][x * 16 // size]
                            expected = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
                            assert image.get(x, y) == expected, (sheet, graphic, x, y)
                assert any(ed.canvas.type(i) == "image" for i in ed.canvas.find_all())
                ed.terrain.set(True)
                ed.draw()
                pump()
                assert not any(ed.canvas.type(i) == "image" for i in ed.canvas.find_all())
                ed.terrain.set(False)
                ed.draw()
                pump()
                assert any(ed.canvas.type(i) == "image" for i in ed.canvas.find_all())
                screenshot("map", ed.window)
                print("PASS: original tile pixels, palette thumbnails, zoom sampling, cached images and collision view.", flush=True)

                # Missing source art leaves a usable editor and a clear
                # recovery path, without substituting another tile set.
                data_path=app.settings["data"]
                app.settings["data"]=str(tmp/"missing-original")
                ed.reload_graphics();pump()
                assert not {"chi:land","chi:destroyed"}.intersection(ed.graphics) and "Graphics unavailable" in ed.graphics_note.get()
                assert len(ed.brush.get_children())==len(doc.adventure["tiles"])+1
                app.settings["data"]=data_path;ed.reload_graphics();pump()
                assert {"chi:land","chi:destroyed"}.issubset(ed.graphics)
                print("PASS: missing-art fallback, setup guidance and reload preserve the project.",flush=True)

                def dialog(title):
                    return next(w for w in descendants(window) if isinstance(w, tk.Toplevel) and w.title() == title)

                def button(parent, label):
                    return next(w for w in descendants(parent) if w.winfo_class() == "TButton" and str(w.cget("text")) == label)

                def field(parent, label):
                    title = next(w for w in descendants(parent) if w.winfo_class() == "TLabel" and str(w.cget("text")) == label)
                    row = title.grid_info()["row"]
                    return next(w for w in title.master.winfo_children() if w.grid_info().get("row") == row and w.grid_info().get("column") == 1)

                # Use the same tile definition and graphical chooser controls
                # as a user, including the second sheet and the final tile.
                original = copy.deepcopy(doc.adventure)
                ed.brush.selection_set("0")
                ed.edit_tile()
                pump()
                form = dialog("Tile definition")
                button(form, "Choose graphic...").invoke()
                pump()
                picker = dialog("Choose tile graphic")
                picker.geometry("720x630+80+50")
                sheet_choice = next(w for w in descendants(picker) if w.winfo_class() == "TCombobox")
                sheet_choice.set("chi:destroyed")
                sheet_choice.event_generate("<<ComboboxSelected>>")
                pump()
                atlas = next(w for w in descendants(picker) if isinstance(w, tk.Canvas))
                atlas.yview_moveto(1)
                pump()
                index, cell, columns = 249, 54, 12
                x = round((index % columns) * cell + cell / 2 - atlas.canvasx(0))
                y = round((index // columns) * cell + 20 - atlas.canvasy(0))
                assert 0 <= x < atlas.winfo_width() and 0 <= y < atlas.winfo_height()
                atlas.event_generate("<ButtonPress-1>", x=x, y=y, time=1000)
                atlas.event_generate("<ButtonRelease-1>", x=x, y=y, time=1010)
                pump()
                screenshot("picker", picker)
                button(picker, "Use graphic").invoke()
                pump()
                assert field(form, "Graphic").get() == "249"
                assert field(form, "Sheet").get() == "chi:destroyed"
                button(form, "Apply").invoke()
                pump()
                assert doc.adventure["tiles"][0]["graphic"] == 249
                assert doc.adventure["tiles"][0]["sheet"] == "chi:destroyed"
                doc.validate()
                ed.undo()
                pump()
                assert doc.adventure == original
                print("PASS: visual tile picker selects the final tile on another sheet, applies and undoes through shared validation.", flush=True)

                disk = dict(doc.snapshot)
                event_time = 10000

                def pointer(sequence, x, y, state=0):
                    nonlocal event_time
                    event_time += 1000
                    ed.canvas.event_generate(sequence, x=round(x), y=round(y), state=state, time=event_time)
                    pump()

                def choose_scene(index, zoom="24"):
                    ed.map_choice.current(index)
                    ed.map_choice.event_generate("<<ComboboxSelected>>")
                    ed.zoom.set(zoom)
                    ed.draw()
                    pump()

                def marker(ref, adventure=None):
                    return next(m for m in scene_markers(adventure or doc.adventure, ed.scene_index) if m["ref"] == ref)

                def marker_point(ref, label=False):
                    at = marker(ref)["at"]
                    scale = int(ed.zoom.get()) / 2
                    wx, wy = at[0] * scale, at[1] * scale
                    width = len(ed.scene()["rows"][0]) * int(ed.zoom.get())
                    height = len(ed.scene()["rows"]) * int(ed.zoom.get())
                    ed.canvas.xview_moveto(max(0, (wx - ed.canvas.winfo_width() / 2) / width))
                    ed.canvas.yview_moveto(max(0, (wy - ed.canvas.winfo_height() / 2) / height))
                    pump()
                    if label:
                        tag = next(tag for tag, value in ed.canvas_marker_refs.items() if value == ref)
                        item = next(i for i in ed.canvas.find_withtag(tag) if ed.canvas.type(i) == "text")
                        bounds = ed.canvas.bbox(item)
                        wx, wy = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
                    point = wx - ed.canvas.canvasx(0), wy - ed.canvas.canvasy(0)
                    assert 0 <= point[0] < ed.canvas.winfo_width() and 0 <= point[1] < ed.canvas.winfo_height(), (ref, point)
                    return point

                def drag(ref, delta, label=False, release=True):
                    ed.tool.set("Paint")  # Markers take priority over painting.
                    x, y = marker_point(ref, label)
                    pointer("<ButtonPress-1>", x, y)
                    assert ed.drag is not None and ed.selected_marker == ref, (ref, ed.selected_marker)
                    scale = int(ed.zoom.get()) / 2
                    target = x + delta[0] * scale, y + delta[1] * scale
                    pointer("<B1-Motion>", *target, state=0x100)
                    if release:
                        pointer("<ButtonRelease-1>", *target)

                # Move each kind using pointer events. Each gesture must only
                # affect one coordinate and create exactly one history entry.
                for kind, scene_index in [("entrance", 0), ("npc", 0), ("start", 0), ("party", 1), ("enemy", 1)]:
                    choose_scene(scene_index)
                    ref = next(m["ref"] for m in scene_markers(doc.adventure, scene_index) if m["ref"][0] == kind)
                    before = copy.deepcopy(doc.adventure)
                    history = len(doc.undo_stack)
                    at = marker(ref)["at"]
                    drag(ref, (1, 1))
                    assert marker(ref)["at"] == [at[0] + 1, at[1] + 1], kind
                    assert len(doc.undo_stack) == history + 1, kind
                    after = copy.deepcopy(doc.adventure)
                    expected = copy.deepcopy(before)
                    from adventure_editing import move_marker
                    move_marker(expected, scene_index, ref, [at[0] + 1, at[1] + 1])
                    assert after == expected, kind
                    ed.undo()
                    pump()
                    assert doc.adventure == before
                    ed.redo()
                    pump()
                    assert doc.adventure == after
                    ed.undo()
                    pump()
                    assert doc.adventure == before
                    assert all((doc.root / name).read_bytes() == data for name, data in disk.items())
                print("PASS: entrance, NPC, start, encounter-party and enemy dragging; one undo step per gesture; no disk writes.", flush=True)

                # A scrolled, enlarged map plus a label grab must preserve the
                # pointer offset. Escape cancels the draft without dirty data.
                choose_scene(0, "32")
                start_ref = next(m["ref"] for m in scene_markers(doc.adventure, 0) if m["ref"][0] == "start")
                before = copy.deepcopy(doc.adventure)
                history = len(doc.undo_stack)
                drag(start_ref, (2, 0), label=True)
                assert doc.adventure["start"]["at"] == [before["start"]["at"][0] + 2, before["start"]["at"][1]]
                assert len(doc.undo_stack) == history + 1
                ed.undo()
                pump()
                drag(start_ref, (3, 2), release=False)
                assert doc.adventure == before and ed.stroke != before
                ed.window.focus_force()
                ed.window.event_generate("<Escape>")
                pump()
                assert ed.stroke is None and ed.drag is None
                assert doc.adventure == before and len(doc.undo_stack) == history
                drag(start_ref,(2,1),release=False)
                app.undo();pump()
                assert ed.stroke is None and ed.drag is None
                assert doc.adventure==before and len(doc.undo_stack)==history
                # A click without movement is a selection, not an undo entry.
                x, y = marker_point(start_ref)
                pointer("<ButtonPress-1>", x, y)
                pointer("<ButtonRelease-1>", x, y)
                assert doc.adventure == before and len(doc.undo_stack) == history
                # Synthetic motion outside the viewport still exercises the
                # same captured drag path and clamps to legal map coordinates.
                drag(start_ref, (-100, -100))
                assert doc.adventure["start"]["at"] == [0, 0]
                ed.undo()
                pump()
                assert doc.adventure == before
                print("PASS: scroll/zoom coordinate mapping, label offsets, Escape cancellation, no-op selection and bounds clamp.", flush=True)

                # Finish with a genuinely legal authored change and reopen it.
                choose_scene(0, "24")
                drag(start_ref, (2, 0))
                saved = copy.deepcopy(doc.adventure)
                doc.validate()
                ed.save()
                pump()
                assert not doc.dirty
                reopened = ProjectDocument(doc.root, tool)
                assert reopened.adventure == saved
                screenshot("drag", ed.window)
                print("PASS: valid dragged start passes the C loader, saves and reopens with all other content intact.", flush=True)

                # At the supported minimum sizes, workspace lists shrink and
                # scroll while the editing actions remain on screen.
                window.geometry("940x690+8+8");ed.window.geometry("960x650+8+8");pump()
                ed.sidebar.select(1);pump()
                delete=button(ed.window,"Delete selected marker")
                assert delete.winfo_rooty()+delete.winfo_height()<=ed.window.winfo_rooty()+ed.window.winfo_height()
                screenshot('minimum',ed.window)
                assert ed.canvas.winfo_width()>400,ed.canvas.winfo_width()
                assert ed.markers.winfo_height()>=16
                ed.sidebar.select(0);pump();assert ed.brush.winfo_height()>=40
                menu_labels=[ed.tile_menu.entrycget(i,'label') for i in range(ed.tile_menu.index('end')+1)]
                assert 'Edit pixels' in menu_labels and 'Clone tile' in menu_labels
                for label in ['World / jigsaws','Graphics / sprites']:
                    control=button(ed.window,label)
                    assert control.winfo_rootx()+control.winfo_width()<=ed.window.winfo_rootx()+ed.window.winfo_width(),label
                for label in ["New project","Open","Save","Validate","Undo","Redo","Play","Player setup","Maps / events","Export game"]:
                    control=button(window,label)
                    assert control.winfo_rootx()>=window.winfo_rootx()
                    assert control.winfo_rootx()+control.winfo_width()<=window.winfo_rootx()+window.winfo_width()
                print("PASS: minimum-size roster/map windows keep toolbars, palette and marker controls visible.",flush=True)
            finally:
                window.destroy()
