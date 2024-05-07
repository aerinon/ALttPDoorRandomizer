import importlib.util


def check_requirements(console=False):
    check_packages = {'aenum': 'aenum',
                      'fast-enum': 'fast_enum',
                      'python-bps-continued': 'bps',
                      'colorama': 'colorama',
                      'aioconsole' : 'aioconsole',
                      'websockets' : 'websockets',
                      'pyyaml': 'yaml'}
    missing = []
    for package, import_name in check_packages.items():
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            missing.append(package)
    if len(missing) > 0:
        packages = ','.join(missing)
        if console:
            import logging
            logger = logging.getLogger('')
            logger.error('You need to install the following python packages:')
            logger.error(f'{packages}')
            logger.error('See the step about "Installing Platform-specific dependencies":')
            logger.error('https://github.com/aerinon/ALttPDoorRandomizer/blob/DoorDev/docs/BUILDING.md')
        else:
            import webbrowser
            from tkinter import Tk, Label, Button, Frame

            master = Tk()
            master.title('Error')
            frame = Frame(master)
            frame.pack(expand=True, padx =50, pady=50)
            Label(frame, text='You need to install the following python packages:').pack()
            Label(frame, text=f'{packages}').pack()
            Label(frame, text='See the step about "Installing Platform-specific dependencies":').pack()
            url = 'https://github.com/aerinon/ALttPDoorRandomizer/blob/DoorDev/docs/BUILDING.md'
            link = Label(frame, fg='blue', cursor='hand2', text=url)
            link.pack()
            link.bind('<Button-1>', lambda e: webbrowser.open_new_tab(url))
            Button(master, text='Ok', command=master.destroy).pack()
            master.mainloop()
