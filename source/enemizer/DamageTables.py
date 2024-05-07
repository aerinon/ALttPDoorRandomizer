from Utils import load_cached_yaml


class DamageTable:
    def __init__(self):
        self.damage_table = load_cached_yaml(['source', 'enemizer', 'damage_table.yaml'])
        self.enemy_damage = load_cached_yaml(['source', 'enemizer', 'enemy_damage_table.yaml'])

