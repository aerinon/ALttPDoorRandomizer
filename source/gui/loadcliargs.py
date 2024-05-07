from source.classes.SpriteSelector import SpriteSelector as spriteSelector
from source.gui.randomize.gameoptions import set_sprite
from Rom import Sprite, get_sprite_from_name
from Utils import update_deprecated_args
import source.classes.constants as CONST
from source.classes.BabelFish import BabelFish
from source.classes.Empty import Empty

# Load args/settings for most tabs
def loadcliargs(gui, args, settings=None):
    if args is not None:
        args = update_deprecated_args(args)
        args = vars(args)
        fish = BabelFish()
        for k, v in args.items():
            if isinstance(v,dict) and 1 in v:
                setattr(args, k, v[1])  # only get values for player 1 for now
        # load values from commandline args

        # set up options to get
        # Page::Subpage::GUI-id::param-id
        options = CONST.SETTINGSTOPROCESS

        # Cycle through each page
        for mainpage in options:
            subpage = None
            _, v = next(iter(options[mainpage].items()))
            if isinstance(v, str):
                subpage = ""
            # Cycle through each subpage (in case of Item Randomizer)
            for subpage in (options[mainpage] if subpage is None else [subpage]):
                # Cycle through each widget
                for widget in (options[mainpage][subpage] if subpage != "" else options[mainpage]):
                    page = gui.pages[mainpage].pages[subpage] if subpage != "" else gui.pages[mainpage]
                    pagewidgets = page.content.customWidgets if mainpage == "custom" else page.content.startingWidgets if mainpage == "startinventory" else page.widgets
                    if widget in pagewidgets:
                        thisType = ""
                        # Get the value and set it
                        arg = options[mainpage][subpage][widget] if subpage != "" else options[mainpage][widget]
                        if args[arg] == None:
                            args[arg] = ""
                        label_ref = mainpage + ('.' + subpage if subpage != "" else '') + '.' + widget
                        label = fish.translate("gui","gui", label_ref)
                        if hasattr(pagewidgets[widget],"type"):
                            thisType = pagewidgets[widget].type
                            if thisType == "checkbox":
                                pagewidgets[widget].checkbox.configure(text=label)
                            elif thisType == "selectbox":
                                theseOptions = pagewidgets[widget].selectbox.options
                                pagewidgets[widget].label.configure(text=label)
                                i = 0
                                for value in theseOptions["values"]:
                                    pagewidgets[widget].selectbox.options["labels"][i] = fish.translate("gui","gui", label_ref + '.' + str(value))
                                    i += 1
                                for i in range(0, len(theseOptions["values"])):
                                    pagewidgets[widget].selectbox["menu"].entryconfigure(i, label=theseOptions["labels"][i])
                                pagewidgets[widget].selectbox.options = theseOptions
                            elif thisType == "spinbox":
                                pagewidgets[widget].label.configure(text=label)
                            elif thisType == 'button':
                                pagewidgets[widget].button.configure(text=label)
                        if hasattr(pagewidgets[widget], 'storageVar'):
                            pagewidgets[widget].storageVar.set(args[arg])
                        # If we're on the Game Options page and it's not about Hints
                        if subpage == "gameoptions" and widget not in ["hints", "collection_rate"]:
                            # Check if we've got settings
                            # Check if we've got the widget in Adjust settings
                            hasSettings = settings is not None
                            hasWidget = ("adjust." + widget) in settings if hasSettings else None
                            label = fish.translate("gui","gui","adjust." + widget)
                            if ("adjust." + widget) in label:
                                label = fish.translate("gui","gui","randomizer.gameoptions." + widget)
                            if hasattr(gui.pages["adjust"].content.widgets[widget],"type"):
                                type = gui.pages["adjust"].content.widgets[widget].type
                                if type == "checkbox":
                                    gui.pages["adjust"].content.widgets[widget].checkbox.configure(text=label)
                                elif type == "selectbox":
                                    gui.pages["adjust"].content.widgets[widget].label.configure(text=label)
                            if hasWidget is None:
                                # If we've got a Game Options val and we don't have an Adjust val, use the Game Options val
                                gui.pages["adjust"].content.widgets[widget].storageVar.set(args[arg])

        # Get baserom path
        mainpage = "randomizer"
        subpage = "generation"
        widget = "rom"
        setting = "rom"
        # set storagevar
        gui.pages[mainpage].pages[subpage].widgets[widget].storageVar.set(args[setting])
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].pieces["frame"].label.configure(text=label)
        # set button label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget + ".button")
        gui.pages[mainpage].pages[subpage].widgets[widget].pieces["button"].configure(text=label)

        # Get Multiworld Worlds count
        mainpage = "bottom"
        subpage = "content"
        widget = "worlds"
        setting = "multi"
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].label.configure(text=label)
        if args[setting]:
            # set storagevar
            gui.pages[mainpage].pages[subpage].widgets[widget].storageVar.set(str(args[setting]))

        # Set Multiworld Names
        mainpage = "bottom"
        subpage = "content"
        widget = "names"
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].pieces["frame"].label.configure(text=label)

        # Get Seed ID
        mainpage = "bottom"
        subpage = "content"
        widget = "seed"
        setting = "seed"
        if args[setting]:
            gui.pages[mainpage].pages[subpage].widgets[widget].storageVar.set(args[setting])
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].pieces["frame"].label.configure(text=label)

        # Get number of generations to run
        mainpage = "bottom"
        subpage = "content"
        widget = "generationcount"
        setting = "count"
        if args[setting]:
            gui.pages[mainpage].pages[subpage].widgets[widget].storageVar.set(str(args[setting]))
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].label.configure(text=label)

        # Set Generate button
        mainpage = "bottom"
        subpage = "content"
        widget = "go"
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].pieces["button"].configure(text=label)

        # Set Output Directory button
        mainpage = "bottom"
        subpage = "content"
        widget = "outputdir"
        # set textbox/frame label
        label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
        gui.pages[mainpage].pages[subpage].widgets[widget].pieces["button"].configure(text=label)
        # Get output path
        gui.pages[mainpage].pages[subpage].widgets[widget].storageVar.set(args["outputpath"])

        # Set Documentation button
        mainpage = "bottom"
        subpage = "content"
        widget = "docs"
        if widget in gui.pages[mainpage].pages[subpage].widgets:
            if "button" in gui.pages[mainpage].pages[subpage].widgets[widget].pieces:
                # set textbox/frame label
                label = fish.translate("gui","gui",mainpage + '.' + subpage + '.' + widget)
                gui.pages[mainpage].pages[subpage].widgets[widget].pieces["button"].configure(text=label)

        # Figure out Sprite Selection
        def sprite_setter(spriteObject):
            gui.pages["randomizer"].pages["gameoptions"].widgets["sprite"]["spriteObject"] = spriteObject
        if args["sprite"] is not None:
            sprite_obj = args.sprite if isinstance(args["sprite"], Sprite) else get_sprite_from_name(args["sprite"])
            set_sprite(sprite_obj, False, spriteSetter=sprite_setter,
                       spriteNameVar=gui.pages["randomizer"].pages["gameoptions"].widgets["sprite"]["spriteNameVar"],
                       randomSpriteVar=gui.randomSprite)

        def sprite_setter_adj(spriteObject):
            gui.pages["adjust"].content.sprite = spriteObject
        if args["sprite"] is not None:
            sprite_obj = args.sprite if isinstance(args["sprite"], Sprite) else get_sprite_from_name(args["sprite"])
            set_sprite(sprite_obj, False, spriteSetter=sprite_setter_adj,
                       spriteNameVar=gui.pages["adjust"].content.spriteNameVar2,
                       randomSpriteVar=gui.randomSprite)

# Load args/settings for Adjust tab
def loadadjustargs(gui, settings):
    options = {
        "adjust": {
            "content": {
                "nobgm": "adjust.nobgm",
                "quickswap": "adjust.quickswap",
                "heartcolor": "adjust.heartcolor",
                "heartbeep": "adjust.heartbeep",
                "menuspeed": "adjust.menuspeed",
                "owpalettes": "adjust.owpalettes",
                "uwpalettes": "adjust.uwpalettes",
                "reduce_flashing": "adjust.reduce_flashing",
                "shuffle_sfx": "adjust.shuffle_sfx"
            }
        }
    }
    for mainpage in options:
        for subpage in options[mainpage]:
            for widget in options[mainpage][subpage]:
                key = options[mainpage][subpage][widget]
                if key in settings:
                    gui.pages[mainpage].content.widgets[widget].storageVar.set(settings[key])
