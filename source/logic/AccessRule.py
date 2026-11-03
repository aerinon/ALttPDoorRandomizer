"""Inspectable access rules with a compiled callable for evaluation.

Each Location/Entrance holds:
  verbose_rule -- this tree (inspectable, combinable)
  access_rule  -- verbose_rule.compiled(), used by CollectionState BFS

Callables passed to set_rule/add_rule become Opaque leaves. Structured
leaves (Has, Primitive, Reach) are for later conversion; existing rule
authors still pass lambdas.

Evaluate the compiled callable on the fill hot path, not the tree.
Do not expand shops/keys/magic into item DNF here.
"""


def true_fn(state):
    return True


def false_fn(state):
    return False


class AccessRule(object):
    __slots__ = ('_compiled',)

    def __init__(self):
        self._compiled = None

    def eval(self, state):
        return self.compiled()(state)

    def __call__(self, state):
        return self.compiled()(state)

    def flatten(self):
        return self

    def atoms(self):
        """Hashable AND-set of this rule, for dominance checks.

        Empty means always true. A is easier than B when every normalized
        atom of A is in B at an equal or higher count (see requirement_easier).
        An OR keeps atoms shared by every branch, plus one blob for the choice.
        The blob stops a disjoint OR from looking easier than another path.
        Opaque leaves stay unique by id until they are converted.
        """
        return frozenset({('opaque', id(self))})

    def compile(self):
        raise NotImplementedError

    def compiled(self):
        compiled = self._compiled
        if compiled is None:
            compiled = self.compile()
            self._compiled = compiled
        return compiled

    def __and__(self, other):
        return AndRule((self, coerce_rule(other))).flatten()

    def __or__(self, other):
        return OrRule((self, coerce_rule(other))).flatten()

    def __invert__(self):
        return NotRule(self).flatten()

    def __bool__(self):
        raise TypeError('AccessRule cannot be used as a bool; call it with a state or combine with & / |')


class TrueRule(AccessRule):
    __slots__ = ()

    def eval(self, state):
        return True

    def compile(self):
        return true_fn

    def atoms(self):
        return frozenset()

    def __str__(self):
        return 'True'

    def __repr__(self):
        return 'TRUE'


class FalseRule(AccessRule):
    __slots__ = ()

    def eval(self, state):
        return False

    def compile(self):
        return false_fn

    def atoms(self):
        return frozenset({('false',)})

    def __str__(self):
        return 'False'

    def __repr__(self):
        return 'FALSE'


TRUE = TrueRule()
FALSE = FalseRule()


class Opaque(AccessRule):
    """Callable that cannot be inspected further (legacy lambda)."""
    __slots__ = ('fn',)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def compile(self):
        return self.fn

    def atoms(self):
        return frozenset({('opaque', id(self.fn))})

    def __str__(self):
        name = getattr(self.fn, '__name__', None) or repr(self.fn)
        return f'Opaque({name})'

    def __repr__(self):
        return str(self)


class Has(AccessRule):
    __slots__ = ('item', 'player', 'count')

    def __init__(self, item, player, count=1):
        super().__init__()
        self.item = item
        self.player = player
        self.count = count

    def compile(self):
        item, player, count = self.item, self.player, self.count
        if count == 1:
            return lambda state, item=item, player=player: state.has(item, player)
        return lambda state, item=item, player=player, count=count: state.has(item, player, count)

    def atoms(self):
        return frozenset({('has', self.item, self.player, self.count)})

    def __str__(self):
        if self.count == 1:
            return f'has {self.item}'
        return f'has {self.count} {self.item}'

    def __repr__(self):
        return f'Has({self.item!r}, {self.player}, {self.count})'


class Primitive(AccessRule):
    """Named CollectionState method: Primitive('can_use_bombs', player)."""
    __slots__ = ('method_name', 'args', 'kwargs')

    def __init__(self, method_name, *args, **kwargs):
        super().__init__()
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs

    def compile(self):
        name, args, kwargs = self.method_name, self.args, self.kwargs
        return lambda state, name=name, args=args, kwargs=kwargs: getattr(state, name)(*args, **kwargs)

    def atoms(self):
        return frozenset({(
            'prim',
            self.method_name,
            tuple(_atom_value(a) for a in self.args),
            tuple(sorted((k, _atom_value(v)) for k, v in self.kwargs.items())),
        )})

    def __str__(self):
        parts = [repr(a) for a in self.args]
        parts.extend(f'{k}={v!r}' for k, v in self.kwargs.items())
        return f'{self.method_name}({", ".join(parts)})'

    def __repr__(self):
        return f'Primitive({self.method_name!r}, {self.args}, {self.kwargs})'


class Reach(AccessRule):
    __slots__ = ('spot', 'resolution_hint', 'player')

    def __init__(self, spot, resolution_hint=None, player=None):
        super().__init__()
        self.spot = spot
        self.resolution_hint = resolution_hint
        self.player = player

    def compile(self):
        spot, hint, player = self.spot, self.resolution_hint, self.player
        return lambda state, spot=spot, hint=hint, player=player: state.can_reach(spot, hint, player)

    def atoms(self):
        return frozenset({('reach', _atom_value(self.spot), self.resolution_hint, self.player)})

    def __str__(self):
        return f'canReach {self.spot}'

    def __repr__(self):
        return f'Reach({self.spot!r}, {self.resolution_hint!r}, {self.player})'


class AndRule(AccessRule):
    __slots__ = ('rules',)

    def __init__(self, rules):
        super().__init__()
        self.rules = tuple(rules)

    def flatten(self):
        return _flatten_and(self.rules)

    def compile(self):
        return _compile_and(self.rules)

    def atoms(self):
        combined = frozenset()
        for rule in self.rules:
            combined |= rule.atoms()
        return combined

    def __str__(self):
        return '(' + ' and '.join(str(r) for r in self.rules) + ')'

    def __repr__(self):
        return f'AndRule({self.rules!r})'


class OrRule(AccessRule):
    __slots__ = ('rules',)

    def __init__(self, rules):
        super().__init__()
        self.rules = tuple(rules)

    def flatten(self):
        return _flatten_or(self.rules)

    def compile(self):
        return _compile_or(self.rules)

    def atoms(self):
        # Atoms present on every usable branch are real requirements, so
        # 1 key on every branch still outranks 3 keys. The remaining choice
        # is one blob. Boots-or-hookshot must not look easier than another path.
        branches = []
        for rule in self.rules:
            child = rule.atoms()
            if ('false',) in child:
                continue
            branches.append(child)
        if not branches:
            return frozenset({('false',)})
        if len(branches) == 1:
            return branches[0]
        necessary = branches[0]
        for child in branches[1:]:
            necessary &= child
        return necessary | frozenset({('or', frozenset(branches))})

    def __str__(self):
        return '(' + ' or '.join(str(r) for r in self.rules) + ')'

    def __repr__(self):
        return f'OrRule({self.rules!r})'


class NotRule(AccessRule):
    __slots__ = ('rule',)

    def __init__(self, rule):
        super().__init__()
        self.rule = rule

    def flatten(self):
        inner = coerce_rule(self.rule).flatten()
        if _is_true(inner):
            return FALSE
        if _is_false(inner):
            return TRUE
        if isinstance(inner, NotRule):
            return inner.rule
        if inner is self.rule:
            return self
        return NotRule(inner)

    def compile(self):
        inner = coerce_rule(self.rule).compiled()
        return lambda state, inner=inner: not inner(state)

    def atoms(self):
        return frozenset({('not', coerce_rule(self.rule).atoms())})

    def __str__(self):
        return f'not ({self.rule})'

    def __repr__(self):
        return f'NotRule({self.rule!r})'


def _is_true(rule):
    return type(rule) is TrueRule


def _is_false(rule):
    return type(rule) is FalseRule


def _flatten_and(rules):
    flat = []
    for rule in rules:
        rule = coerce_rule(rule).flatten()
        if _is_true(rule):
            continue
        if _is_false(rule):
            return FALSE
        if isinstance(rule, AndRule):
            flat.extend(rule.rules)
        else:
            flat.append(rule)
    if not flat:
        return TRUE
    if len(flat) == 1:
        return flat[0]
    return AndRule(flat)


def _flatten_or(rules):
    flat = []
    for rule in rules:
        rule = coerce_rule(rule).flatten()
        if _is_false(rule):
            continue
        if _is_true(rule):
            return TRUE
        if isinstance(rule, OrRule):
            flat.extend(rule.rules)
        else:
            flat.append(rule)
    if not flat:
        return FALSE
    if len(flat) == 1:
        return flat[0]
    return OrRule(flat)


def _compile_and(rules):
    fns = tuple(r.compiled() for r in rules)
    n = len(fns)
    if n == 0:
        return true_fn
    if n == 1:
        return fns[0]
    if n == 2:
        a, b = fns
        return lambda state, a=a, b=b: a(state) and b(state)
    if n == 3:
        a, b, c = fns
        return lambda state, a=a, b=b, c=c: a(state) and b(state) and c(state)

    def _and(state, fns=fns):
        for fn in fns:
            if not fn(state):
                return False
        return True

    return _and


def _compile_or(rules):
    fns = tuple(r.compiled() for r in rules)
    n = len(fns)
    if n == 0:
        return false_fn
    if n == 1:
        return fns[0]
    if n == 2:
        a, b = fns
        return lambda state, a=a, b=b: a(state) or b(state)
    if n == 3:
        a, b, c = fns
        return lambda state, a=a, b=b, c=c: a(state) or b(state) or c(state)

    def _or(state, fns=fns):
        for fn in fns:
            if fn(state):
                return True
        return False

    return _or


def _atom_value(value):
    try:
        hash(value)
        return value
    except TypeError:
        return ('id', id(value))


# Primitive.args index whose integer is "more is harder" (keys, hearts, crystals, magic).
_COUNT_PRIMITIVES = {
    'has_sm_key': 2,
    'has_sm_key_strict': 2,
    'has_hearts': 1,
    'has_crystals': 0,
    'can_extend_magic': 1,
}


def _atom_key_count(atom):
    kind = atom[0] if atom else None
    if kind == 'has':
        return ('has', atom[1], atom[2]), atom[3]
    if kind == 'prim':
        name, args, kwargs = atom[1], atom[2], atom[3]
        idx = _COUNT_PRIMITIVES.get(name)
        if idx is not None:
            if idx < len(args) and isinstance(args[idx], int):
                return ('prim', name, args[:idx] + args[idx + 1:], kwargs), args[idx]
            if idx >= len(args):
                return ('prim', name, args, kwargs), 1
    return atom, 1


def _normalize_requirement(atoms):
    """Map comparable keys to the hardest count in the AND-set. None means FALSE."""
    if ('false',) in atoms:
        return None
    hardest = {}
    for atom in atoms:
        key, count = _atom_key_count(atom)
        prev = hardest.get(key)
        if prev is None or count > prev:
            hardest[key] = count
    return hardest


def requirement_easier(a_atoms, b_atoms):
    """True if a is less restrictive than b (satisfying b implies a).

    Counted Has / has_sm_key / hearts / crystals / magic: a lower count is easier.
    Other atoms must match exactly. Empty is easier than everything.
    """
    a = _normalize_requirement(a_atoms)
    b = _normalize_requirement(b_atoms)
    if a is None:
        return b is None
    if b is None:
        return True
    for key, count in a.items():
        if key not in b or b[key] < count:
            return False
    return True


def keep_better_requirement(arrivals, dest, atoms, path):
    """Keep a Pareto front of requirement atom-sets per destination.

    Returns True if this arrival is new or strictly easier than some existing
    one, and should be explored further.
    """
    existing = arrivals.get(dest)
    if existing is None:
        arrivals[dest] = [(atoms, path)]
        return True
    for old_atoms, _old_path in existing:
        if requirement_easier(old_atoms, atoms):
            return False
    arrivals[dest] = [
        (old_atoms, old_path)
        for old_atoms, old_path in existing
        if not requirement_easier(atoms, old_atoms)
    ]
    arrivals[dest].append((atoms, path))
    return True


def coerce_rule(rule):
    if rule is None:
        return TRUE
    if isinstance(rule, AccessRule):
        return rule
    if rule is True:
        return TRUE
    if rule is False:
        return FALSE
    # source.logic.Rule.Rule (legacy dual-object experiment)
    if getattr(rule, 'rule_lambda', None) is not None:
        return coerce_rule(rule.rule_lambda)
    if callable(rule):
        if rule is true_fn:
            return TRUE
        if rule is false_fn:
            return FALSE
        return Opaque(rule)
    raise TypeError(f'Cannot coerce {type(rule)!r} to AccessRule')


def and_rule(*rules):
    return _flatten_and(rules)


def or_rule(*rules):
    return _flatten_or(rules)


def not_rule(rule):
    return NotRule(coerce_rule(rule)).flatten()


def _attach(spot, rule):
    """Write tree and compiled callable together. Do not assign either field directly."""
    rule = coerce_rule(rule).flatten()
    spot.verbose_rule = rule
    spot.access_rule = rule.compiled()
    return rule


def set_rule(spot, rule):
    _attach(spot, rule)


def add_rule(spot, rule, combine='and'):
    new = coerce_rule(rule)
    old = coerce_rule(getattr(spot, 'verbose_rule', None))
    if combine == 'or':
        combined = _flatten_or((old, new))
    else:
        combined = _flatten_and((old, new))
    _attach(spot, combined)
