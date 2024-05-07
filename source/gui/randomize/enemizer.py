from tkinter import ttk, filedialog, StringVar, Button, Entry, Frame, Label, N, E, W, LEFT, RIGHT, BOTTOM, X
import source.gui.widgets as widgets
import json
import os
import webbrowser
from source.classes.Empty import Empty

def enemizer_page(parent,settings):
      # Enemizer
    self = ttk.Frame(parent)

    # Enemizer options
    self.widgets = {}

    # Enemizer option sections
    self.frames = {}

    # Enemizer option frames
    self.frames["checkboxes"] = Frame(self)
    self.frames["checkboxes"].pack(anchor=W)

    self.frames["selectOptionsFrame"] = Frame(self)
    self.frames["leftEnemizerFrame"] = Frame(self.frames["selectOptionsFrame"])
    self.frames["rightEnemizerFrame"] = Frame(self.frames["selectOptionsFrame"])
    self.frames["bottomEnemizerFrame"] = Frame(self)
    self.frames["selectOptionsFrame"].pack(fill=X)
    self.frames["leftEnemizerFrame"].pack(side=LEFT)
    self.frames["rightEnemizerFrame"].pack(side=RIGHT)
    self.frames["bottomEnemizerFrame"].pack(fill=X, padx=(12, 0))

    # Load Enemizer option widgets as defined by JSON file
    # Defns include frame name, widget type, widget options, widget placement attributes
    # These get split left & right
    with open(os.path.join("resources","app","gui","randomize","enemizer","widgets.json")) as widgetDefns:
        myDict = json.load(widgetDefns)
        for framename,theseWidgets in myDict.items():
            dictWidgets = widgets.make_widgets_from_dict(self, theseWidgets, self.frames[framename])
            for key in dictWidgets:
                self.widgets[key] = dictWidgets[key]
                packAttrs = {"anchor":E}
                if self.widgets[key].type == "checkbox":
                    packAttrs["anchor"] = W
                if framename == 'bottomEnemizerFrame':
                    packAttrs["anchor"] = W
                self.widgets[key].pack(packAttrs)

    return self, settings
