
from tkinter import messagebox, Checkbutton, Entry, Frame, IntVar, Label, OptionMenu, Spinbox, StringVar, LEFT, RIGHT, X
from tkinter import Button
from source.classes.Empty import Empty

# Override Spinbox to include mousewheel support for changing value
class mySpinbox(Spinbox):
    def __init__(self, *args, **kwargs):
        Spinbox.__init__(self, *args, **kwargs)
        self.bind('<MouseWheel>', self.mouseWheel)
        self.bind('<Button-4>', self.mouseWheel)
        self.bind('<Button-5>', self.mouseWheel)

    def mouseWheel(self, event):
        if event.num == 5 or event.delta == -120:
            self.invoke('buttondown')
        elif event.num == 4 or event.delta == 120:
            self.invoke('buttonup')

# Make a Checkbutton with a label
def make_checkbox(self, parent, label, storageVar, manager, managerAttrs, config):
    self = Frame(parent)
    self.storageVar = storageVar
    if managerAttrs is not None and "default" in managerAttrs:
        if managerAttrs["default"] == "true" or managerAttrs["default"] == True:
            self.storageVar.set(True)
        elif managerAttrs["default"] == "false" or managerAttrs["default"] == False:
            self.storageVar.set(False)
        del managerAttrs["default"]
    options = {"text":label, "variable":self.storageVar}
    if config and "command" in config:
        options.update({"command":lambda m=config["command"]: widget_command(self, m)})
    self.checkbox = Checkbutton(self, options)
    if managerAttrs is not None:
        self.checkbox.pack(managerAttrs)
    else:
        self.checkbox.pack()
    return self

# Make an OptionMenu with a label and pretty option labels
def make_selectbox(self, parent, label, options, storageVar, manager, managerAttrs, config=None):
    self = Frame(parent)

    labels = options

    if isinstance(options,dict):
        labels = options.keys()

    self.labelVar = StringVar()
    self.storageVar = storageVar
    if config and "command" in config:
        self.command = config["command"]
        self.selectbox = OptionMenu(self, self.labelVar, *labels, command=lambda m: widget_command(self, self.command))
    else:
        self.selectbox = OptionMenu(self, self.labelVar, *labels)
    self.selectbox.options = {}

    if isinstance(options,dict):
        self.selectbox.options["labels"] = list(options.keys())
        self.selectbox.options["values"] = list(options.values())
    else:
        self.selectbox.options["labels"] = ["" for i in range(0,len(options))]
        self.selectbox.options["values"] = options

    def change_thing(thing, *args):
        labels = self.selectbox.options["labels"]
        values = self.selectbox.options["values"]
        check = ""
        lbl = ""
        val = ""
        idx = 0

        if thing == "storage":
            check = self.labelVar.get()
        elif thing == "label":
            check = self.storageVar.get()

        if check in labels:
            idx = labels.index(check)
        if check in values:
            idx = values.index(check)

        lbl = labels[idx]
        val = values[idx]

        if thing == "storage":
            self.storageVar.set(val)
        elif thing == "label":
            self.labelVar.set(lbl)
        self.selectbox["menu"].entryconfigure(idx,label=lbl)
        self.selectbox.configure(state="active")


    def change_storage(*args):
        change_thing("storage", *args)
    def change_selected(*args):
        change_thing("label", *args)

    self.storageVar.trace_add("write",change_selected)
    self.labelVar.trace_add("write",change_storage)
    self.label = Label(self, text=label)

    if managerAttrs is not None and "label" in managerAttrs:
        self.label.pack(managerAttrs["label"])
    else:
        self.label.pack(side=LEFT)

    self.selectbox.config(width=config['width'] if config and 'width' in config else 20)
    idx = 0
    default = self.selectbox.options["values"][idx]
    if managerAttrs is not None and "default" in managerAttrs:
        default = managerAttrs["default"]
    labels = self.selectbox.options["labels"]
    values = self.selectbox.options["values"]
    if default in values:
        idx = values.index(default)
    if not labels[idx] == "":
        self.labelVar.set(labels[idx])
        self.selectbox["menu"].entryconfigure(idx,label=labels[idx])
    self.storageVar.set(values[idx])

    if managerAttrs is not None and "selectbox" in managerAttrs:
        self.selectbox.pack(managerAttrs["selectbox"])
    else:
        self.selectbox.pack(side=RIGHT)
    return self

# Make a Spinbox with a label, limit 1-100
def make_spinbox(self, parent, label, storageVar, manager, managerAttrs):
    self = Frame(parent)
    self.storageVar = storageVar
    self.label = Label(self, text=label)
    if managerAttrs is not None and "label" in managerAttrs:
        self.label.pack(managerAttrs["label"])
    else:
        self.label.pack(side=LEFT)
    fromNum = 1
    toNum = 100
    if managerAttrs is not None and "spinbox" in managerAttrs:
        if "from" in managerAttrs:
            fromNum = managerAttrs["spinbox"]["from"]
        if "to" in managerAttrs:
            toNum = managerAttrs["spinbox"]["to"]
    self.spinbox = mySpinbox(self, from_=fromNum, to=toNum, width=5, textvariable=self.storageVar)
    if managerAttrs is not None and "spinbox" in managerAttrs:
        self.spinbox.pack(managerAttrs["spinbox"])
    else:
        self.spinbox.pack(side=RIGHT)
    return self

# Make an Entry box with a label
# Support for Grid or Pack so that the Custom Item Pool & Starting Inventory pages don't look ugly
def make_textbox(self, parent, label, storageVar, manager, managerAttrs):
    widget = Empty()
    widget.storageVar = storageVar
    widget.label = Label(parent, text=label)
    widget.textbox = Entry(parent, justify=RIGHT, textvariable=widget.storageVar, width=3)
    if "default" in managerAttrs:
        widget.storageVar.set(managerAttrs["default"])

    # grid
    if manager == "grid":
        widget.label.grid(managerAttrs["label"] if managerAttrs is not None and "label" in managerAttrs else None, row=parent.thisRow, column=parent.thisCol)
        if managerAttrs is not None and "label" not in managerAttrs:
            widget.label.grid_configure(sticky="w")
        parent.thisCol += 1
        widget.textbox.grid(managerAttrs["textbox"] if managerAttrs is not None and "textbox" in managerAttrs else None, row=parent.thisRow, column=parent.thisCol)
        parent.thisRow += 1
        parent.thisCol = 0

    # pack
    elif manager == "pack":
        widget.label.pack(managerAttrs["label"] if managerAttrs is not None and "label" in managerAttrs else None)
        widget.textbox.pack(managerAttrs["textbox"] if managerAttrs is not None and "textbox" in managerAttrs else None)
    return widget


def make_button(self, parent, label, manager, managerAttrs, config):
    self = Frame(parent)
    if config and "command" in config:
        self.command = config["command"]
    else:
        self.command = lambda: None

    self.button = Button(parent, text=label, command=lambda: widget_command(self, self.command))
    if managerAttrs is not None:
        self.button.pack(managerAttrs)
    else:
        self.button.pack(anchor='w')
    return self


# Make a generic widget
def make_widget(self, type, parent, label, storageVar=None, manager=None, managerAttrs=dict(),
                options=None, config=None):
    widget = None
    if manager is None:
        manager = "pack"
    thisStorageVar = storageVar
    if isinstance(storageVar,str):
        if storageVar == "int" or storageVar == "integer":
            thisStorageVar = IntVar()
        elif storageVar == "str" or storageVar == "string":
            thisStorageVar = StringVar()

    if type == "checkbox":
        if thisStorageVar is None:
            thisStorageVar = IntVar()
        widget = make_checkbox(self, parent, label, thisStorageVar, manager, managerAttrs, config)
    elif type == "selectbox":
        if thisStorageVar is None:
            thisStorageVar = StringVar()
        widget = make_selectbox(self, parent, label, options, thisStorageVar, manager, managerAttrs, config)
    elif type == "spinbox":
        if thisStorageVar is None:
            thisStorageVar = StringVar()
        widget = make_spinbox(self, parent, label, thisStorageVar, manager, managerAttrs)
    elif type == "textbox":
        if thisStorageVar is None:
            thisStorageVar = StringVar()
        widget = make_textbox(self, parent, label, thisStorageVar, manager, managerAttrs)
    elif type == 'button':
        widget = make_button(self, parent, label, manager, managerAttrs, config)
    widget.type = type
    return widget

# Make a generic widget from a dict
def make_widget_from_dict(self, defn, parent):
    type = defn["type"] if "type" in defn else None
    label = defn["label"]["text"] if "label" in defn and "text" in defn["label"] else ""
    manager = defn["manager"] if "manager" in defn else None
    managerAttrs = defn["managerAttrs"] if "managerAttrs" in defn else None
    options = defn["options"] if "options" in defn else None
    config = defn["config"] if "config" in defn else None

    if managerAttrs is None and "default" in defn:
        managerAttrs = {}
    if "default" in defn:
        managerAttrs["default"] = defn["default"]

    widget = make_widget(self, type, parent, label, None, manager, managerAttrs, options, config)
    widget.type = type
    return widget

# Make a set of generic widgets from a dict
def make_widgets_from_dict(self, defns, parent):
    widgets = {}
    for key,defn in defns.items():
        widgets[key] = make_widget_from_dict(self, defn, parent)
    return widgets

# Add padding to widget
def add_padding_from_config(packAttrs, defn):
    if "config" in defn:
        config = defn["config"]
        if 'padx' in config:
            packAttrs["padx"] = config['padx']
        if 'pady' in config:
            packAttrs["pady"] = config['pady']
    return packAttrs

# Callback when a widget issues a command
def widget_command(widget, command=""):
    root = widget.winfo_toplevel()
    text_output = ""
    if command == "retro":
        temp_widget = root.pages["randomizer"].pages["dungeon"].widgets["smallkeyshuffle"]
        text_output += f'\n    {temp_widget.label.cget("text")}'
        temp_widget.storageVar.set('universal')

        temp_widget = root.pages["randomizer"].pages["item"].widgets["bow_mode"]
        text_output += f'\n    {temp_widget.label.cget("text")}'
        if temp_widget.storageVar.get() == 'progressive':
            temp_widget.storageVar.set('retro')
        elif temp_widget.storageVar.get() == 'silvers':
            temp_widget.storageVar.set('retro_silvers')

        temp_widget = root.pages["randomizer"].pages["item"].widgets["take_any"]
        text_output += f'\n    {temp_widget.label.cget("text")}'
        if temp_widget.storageVar.get() == 'none':
            temp_widget.storageVar.set('random')

        messagebox.showinfo('', f'The following settings were changed:{text_output}')
    elif command == "keydropshuffle":
        temp_widget = root.pages["randomizer"].pages["item"].widgets["pottery"]
        text_output += f'\n    {temp_widget.label.cget("text")}'
        if temp_widget.storageVar.get() == 'none':

            temp_widget.storageVar.set('keys')

        temp_widget = root.pages["randomizer"].pages["item"].widgets["dropshuffle"]
        text_output += f'\n    {temp_widget.label.cget("text")}'
        if temp_widget.storageVar.get() == 'none':
            temp_widget.storageVar.set('keys')

        if text_output:
            messagebox.showinfo('', f'The following settings were changed:{text_output}')

