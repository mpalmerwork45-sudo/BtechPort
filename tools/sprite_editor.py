"""Direction-aware editing for the sprite layouts the player understands."""
from __future__ import annotations

import copy
import tkinter as tk
from tkinter import ttk

from graphics_editor import PixelEditor, photo
from pixel_tools import target,flatten
from action_tracks import edit_track,entries
from sprite_editing import (DIRECTIONS, VIEWS, default_view, describe,
                            onion_rows, paste_frame, sequence, sharing_note)


class SpriteEditor(PixelEditor):
    """Edit fixed image slots while previewing one movement direction at a time.

    The frame selector kept by PixelEditor is hidden here. It always names the
    actual stored image; direction/phase navigation translates into that index.
    Playback has its own phase so it cannot change where a pencil stroke lands.
    """

    def __init__(self, owner, image):
        self.direction = 4
        self.phase = 0
        self.preview_phase = 0
        self.preview_timer = None
        self.clipboard = None
        self.thumbnails = []
        self.thumbnail_cache = {}
        super().__init__(owner, image)
        self.window.title('Sprite editor - ' + image['name'])
        self.window.geometry('960x740')
        self.window.minsize(900, 730)
        self.zoom.set(str(max(z for z in (1, 2, 4, 8, 16)
                              if z * max(image['width'], image['height']) <= 256)))
        self.window.bind('<Alt-Left>', lambda _: self.step(-1))
        self.window.bind('<Alt-Right>', lambda _: self.step(1))
        self.window.bind('<Alt-Up>', lambda _: self.face((self.direction - 1) % 8))
        self.window.bind('<Alt-Down>', lambda _: self.face((self.direction + 1) % 8))
        self.window.bind('<Destroy>', self.destroyed, add='+')
        self.draw()

    def build_frames(self):
        if hasattr(self.window,'workspace'):
            from editor_art_layout import build_sprite
            return build_sprite(self)
        panel = ttk.Frame(self.window, padding=8)
        panel.pack(fill='x')
        panel.columnconfigure(1, weight=1)
        self.view = tk.StringVar(value=default_view(self.owner.document, self.image))
        options = ttk.Frame(panel)
        options.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 8))
        ttk.Label(options, text='Preview as').pack(side='left')
        chooser = ttk.Combobox(options, textvariable=self.view, values=VIEWS,
                               state='readonly', width=24)
        chooser.pack(side='left', padx=(6, 16))
        chooser.bind('<<ComboboxSelected>>', lambda _: self.change_view())
        self.description = tk.StringVar()
        ttk.Label(options, textvariable=self.description).pack(side='left')

        compass = ttk.LabelFrame(panel, text='Movement direction', padding=4)
        compass.grid(row=1, column=0, sticky='n', padx=(0, 12))
        self.directions = {}
        for direction, row, col in ((7, 0, 0), (0, 0, 1), (1, 0, 2), (6, 1, 0),
                                    (2, 1, 2), (5, 2, 0), (4, 2, 1), (3, 2, 2)):
            button = ttk.Button(compass, text=DIRECTIONS[direction], width=10,
                                command=lambda d=direction: self.face(d))
            button.grid(row=row, column=col, padx=1, pady=2)
            self.directions[direction] = button
        ttk.Label(compass, text='Facing', anchor='center').grid(row=1, column=1)

        frames = ttk.Frame(panel)
        frames.grid(row=1, column=1, sticky='nsew', padx=(0, 12))
        self.strip = tk.Canvas(frames, width=330, height=106, background='#e5e8ec',
                               highlightthickness=0)
        self.strip.pack(fill='x')
        scroll = ttk.Scrollbar(frames, orient='horizontal', command=self.strip.xview)
        scroll.pack(fill='x')
        self.strip.configure(xscrollcommand=scroll.set)
        self.strip.bind('<Button-1>', self.pick_thumbnail)
        navigation = ttk.Frame(frames)
        navigation.pack(fill='x', pady=(6, 0))
        self.previous = ttk.Button(navigation, text='Previous frame', width=0,
                                   command=lambda: self.step(-1))
        self.previous.pack(side='left', padx=(0, 4))
        self.next = ttk.Button(navigation, text='Next frame', width=0,
                               command=lambda: self.step(1))
        self.next.pack(side='left')

        playback = ttk.Frame(panel)
        playback.grid(row=1, column=2, sticky='n')
        self.animation = tk.Canvas(playback, width=144, height=96,
                                   background='#d6d6d6', highlightthickness=0)
        self.animation.pack()
        self.play_button = ttk.Button(playback, text='Play preview', command=self.play)
        self.play_button.pack(fill='x', pady=(4, 0))
        speed = ttk.Frame(playback)
        speed.pack(pady=(4, 0))
        self.fps = tk.StringVar(value='8')
        ttk.Combobox(speed, textvariable=self.fps, values=('4', '6', '8', '12'),
                     state='readonly', width=3).pack(side='left')
        ttk.Label(speed, text=' fps (preview)').pack(side='left')

        tools = ttk.Frame(panel)
        tools.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(8, 0))
        ttk.Button(tools,text='Edit action...',command=lambda:self.guard(lambda:edit_track(self))).pack(side='left',padx=(0,4))
        ttk.Button(tools,text='Clone image',command=lambda:self.guard(self.clone_pose)).pack(side='left',padx=(0,4))
        ttk.Button(tools, text='Copy frame', command=self.copy_frame).pack(side='left')
        self.paste_button = ttk.Button(tools, text='Paste frame', command=lambda: self.guard(self.paste),
                                      state='disabled')
        self.paste_button.pack(side='left', padx=(4, 12))
        self.onion = tk.BooleanVar(value=False)
        ttk.Checkbutton(tools, text='Show previous frame faintly', variable=self.onion,
                        command=self.draw).pack(side='left')
        
        self.note = tk.StringVar()
        ttk.Label(panel, textvariable=self.note, wraplength=865,
                  style='Muted.TLabel').grid(row=3, column=0, columnspan=3,
                                            sticky='w', pady=(6, 0))
        # Fixed slots are deliberate: deleting or inserting an image changes
        # how the runtime interprets every following direction. Copy/paste
        # provides pose duplication without silently reassigning directions.
        self.frame = ttk.Combobox(panel, state='readonly')

    def frames(self):
        return sequence(self.image, self.view.get(), self.direction)

    def refresh_frames(self):
        self.frame.configure(values=list(range(1, len(self.image['frames']) + 1)))
        self.phase %= len(self.frames())
        self.frame.current(self.frames()[self.phase])

    def change_view(self):
        self.finish()
        current = self.frame.current()
        frames = self.frames()
        self.phase = frames.index(current) if current in frames else 0
        self.preview_phase = self.phase
        self.refresh_frames()
        self.draw()
        self.reveal_frame()

    def face(self, direction):
        if self.view.get() == 'All images': return
        self.finish()
        self.direction = direction
        self.preview_phase = 0
        self.refresh_frames()
        self.draw()
        self.reveal_frame()

    def select_phase(self, phase):
        self.finish()
        self.phase = phase % len(self.frames())
        self.refresh_frames()
        self.draw()
        self.reveal_frame()

    def step(self, delta):
        self.select_phase(self.phase + delta)

    def pick_thumbnail(self, event):
        phase = int(self.strip.canvasx(event.x) // 80)
        if 0 <= phase < len(self.frames()): self.select_phase(phase)

    def reveal_frame(self):
        left, right = self.strip.xview()
        count = len(self.frames())
        start, end = self.phase / count, (self.phase + 1) / count
        if start < left: self.strip.xview_moveto(start)
        elif end > right: self.strip.xview_moveto(max(0, end - (right - left)))

    def draw(self):
        super().draw()
        frames = self.frames()
        self.description.set(describe(self.image, self.view.get(), self.direction,
                                      self.frame.current(), self.phase))
        self.note.set(sharing_note(self.image, self.view.get(), self.direction))
        for direction, button in self.directions.items():
            button.state(['disabled'] if self.view.get() == 'All images' else ['!disabled'])
            button.state(['pressed'] if direction == self.direction else ['!pressed'])
        if hasattr(self,'direction_choice'):
            self.direction_choice.current(self.direction)
            self.direction_choice.configure(state='disabled' if self.view.get()=='All images' else 'readonly')
        self.strip.delete('all')
        self.thumbnails = []
        zoom = max(1, 64 // max(self.image['width'], self.image['height']))
        for phase, frame in enumerate(frames):
            x = phase * 80
            self.strip.create_rectangle(x+2, 2, x+78, 104, width=2,
                                        outline='#2768b5' if phase == self.phase else '#bac2cc',
                                        fill='#dceafa' if phase == self.phase else '#f3f5f7')
            # Painting a single pixel should not decode all 32 poses again.
            key = (self.image['width'], self.image['height'], tuple(self.image['frames'][frame]), zoom)
            cached = self.thumbnail_cache.get(frame)
            if cached is None or cached[0] != key:
                cached = (key, photo(self.window, self.image, frame, zoom))
                self.thumbnail_cache[frame] = cached
            thumbnail = cached[1]
            self.thumbnails.append(thumbnail)
            self.strip.create_image(x+40, 36, image=thumbnail)
            self.strip.create_text(x+40, 86, text=f'Frame {phase+1}\nImage {frame+1}',
                                   font='TkSmallCaptionFont', fill='#243344', justify='center')
        self.strip.configure(scrollregion=(0, 0, len(frames)*80, 106))
        self.play_button.configure(text='Pause preview' if self.playing else 'Play preview')
        self.draw_animation()

    def edit_photo(self, zoom):
        if not self.onion.get(): return super().edit_photo(zoom)
        frames = self.frames()
        rows = onion_rows(self.image, self.frame.current(), frames[(self.phase-1) % len(frames)])
        result = tk.PhotoImage(master=self.window, width=self.image['width'], height=self.image['height'])
        result.put(' '.join('{' + ' '.join(row) + '}' for row in rows))
        return result.zoom(zoom)

    def draw_animation(self):
        frames = self.frames()
        phase = self.preview_phase % len(frames) if self.playing else self.phase
        zoom = max(1, min(3, 88 // max(self.image['width'], self.image['height'])))
        self.animation_photo = photo(self.window, self.image, frames[phase], zoom)
        self.animation.delete('all')
        self.animation.create_image(72, 48, image=self.animation_photo)

    def copy_frame(self):
        self.finish()
        self.clipboard = copy.deepcopy(target(self.image)['frames'][self.frame.current()])
        self.paste_button.state(['!disabled'])

    def paste(self):
        self.finish()
        self.playing = False
        candidate = copy.deepcopy(self.image)
        paste_frame(target(candidate), self.frame.current(), self.clipboard);flatten(candidate,self.frame.current())
        if candidate != self.image:
            self.history.append(self.image)
            self.history = self.history[-40:]
            self.future = []
            self.image = candidate
            self.draw()

    def cancel_timer(self):
        if self.preview_timer is not None:
            self.window.after_cancel(self.preview_timer)
            self.preview_timer = None

    def play(self):
        self.cancel_timer()
        self.playing = not self.playing
        self.preview_phase = self.phase
        self.play_button.configure(text='Pause preview' if self.playing else 'Play preview')
        self.draw_animation()
        if self.playing:
            self.preview_timer = self.window.after(self.frame_delay(), self.animate)

    def animate(self):
        self.preview_timer = None
        if not self.playing: return
        self.preview_phase = (self.preview_phase + 1) % len(self.frames())
        self.draw_animation()
        self.preview_timer = self.window.after(self.frame_delay(), self.animate)

    def frame_delay(self):
        track=entries(self.image,self.view.get().lower(),self.direction)
        return 32*track[self.preview_phase%len(track)]["ticks"] if track else round(1000/int(self.fps.get()))

    def clone_pose(self):
        self.view.set("All images");self.add_frame();self.phase=len(self.image["frames"])-1;self.refresh_frames();self.draw()

    def destroyed(self, event):
        if event.widget == self.window:
            self.playing = False
            self.cancel_timer()
