from source.classes.CustomSettings import load_yaml, CustomSettings
import os


def get_limited_run_args(limited_run_args):
    # limited_run_args is a string formatted as "key1=value1|key2=value2|key3=value3
    if isinstance(limited_run_args, dict):
        return limited_run_args
    else:
        args_dict = {}
        if limited_run_args:
            args_list = limited_run_args.split('|')
            for arg in args_list:
                key_value = arg.split('=')
                if len(key_value) == 2:
                    key, value = key_value
                    # Attempt to convert to int or bool if applicable
                    if value.isdigit():
                        value = int(value)
                    elif value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    args_dict[key] = value
        return args_dict


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
                    for section_key, section_value in custom_file.items():
                        if section_key in world.customizer.file_source:
                            world.customizer.file_source[section_key].update(section_value)
                        else:
                            world.customizer.file_source[section_key] = section_value
                world.customizer.adjust_args(args)
