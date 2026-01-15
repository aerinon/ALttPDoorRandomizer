from source.classes.CustomSettings import load_yaml, CustomSettings
import os


def adjust_world_for_limited_runs(world, args):
    for player in range(1, world.players + 1):
        if world.limited_run[player] != 'none':
            yaml = os.path.join('data', 'limited', world.limited_run[player], f'limited_{world.limited_run[player]}.yaml')
            if os.path.exists(yaml):
                if not world.customizer:
                    world.customizer = CustomSettings()
                    world.customizer.load_yaml(yaml)
                else:
                    custom_file = load_yaml(yaml)
                    # TODO: Make this more generic to handle other sections in the future
                    if 'settings' in custom_file:
                        if 'settings' in world.customizer.file_source:
                            world.customizer.file_source['settings'].update(custom_file['settings'])
                        else:
                            world.customizer.file_source['settings'] = custom_file['settings']
                    if 'rooms' in custom_file:
                        if 'rooms' in world.customizer.file_source:
                            world.customizer.file_source['rooms'].update(custom_file['rooms'])
                        else:
                            world.customizer.file_source['rooms'] = custom_file['rooms']
                world.customizer.adjust_args(args)
