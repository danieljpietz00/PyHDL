from .core import _PHDLObj
from .entity import Entity
from .signal import Signal, PortSignal
from typing import List, Dict, Tuple
from .check import check_name
from .process import Process, get_signals_from_list
import itertools
from .type import generate_typestrings


class Architecture(_PHDLObj):

    def __init__(self):
        self.signals: List[Signal] = []
        self.processes: List[Process] = []
        self.libraries: Dict[str, Tuple[str]] = {}
        self.types: List[type] = []
        self.packages = set()
        pass

    def add_signal(self, sig):
        if isinstance(sig, PortSignal):
            raise TypeError(f"{sig.__class__.__name__} object cannot be derived from PortSignal")
        elif isinstance(sig, Signal):
            for signal in self.signals:
                if signal.name == sig.name:
                    raise ValueError("Found duplicate signal {}".format(signal.name))
            self.signals.append(sig)
        else:
            raise TypeError(f"{sig.__class__.__name__} object not derived from Signal")

    def value(self):
        _signals = self.signals_string()

        _processes = '\n\n'.join([process.value() for process in self.processes])
        _processes = '\t' + _processes.replace('\n', '\n\t')

        _typestrings = self.typestrings.replace('\n', '\n\t')
        _typestrings = f"\n\t{_typestrings}\n" if len(_typestrings) != 0 else ''

        return f"architecture rtl of {self.entity.name} is\n" \
               f"{_typestrings}" \
               f"\n\t{_signals}\n\n" \
               f"begin\n" \
               f"{_processes}\n" \
               f"end architecture rtl;"

    def signals_string(self):
        return ";\n\t".join([f'{signal.serialize_declaration()}' for signal in self.signals]) + ';' \
            if len(self.signals) > 0 \
            else ""


def architecture(Target):
    target = Target()
    if not issubclass(Target, Architecture):
        raise TypeError(f"Architecture {Target} must inherit Architecture")
    if not isinstance(Target.entity, Entity):
        raise TypeError(f"{Target.entity.__class__.__name__} object not derived from Entity")
    if not hasattr(Target, 'name'):
        target.name = f"{target.entity.name}_rtl"
    check_name(target.name)

    _architecture(target)

    get_architecture_processes(target)
    get_architecture_types(target)
    return target


def _architecture(target):
    target.signals = []
    target_new_signals = []
    for sig in type(target).__dict__.values():
        if isinstance(sig, Signal):
            target_new_signals.append(sig)
    # target_new_signals = get_signals_from_list(target_new_signals)
    for signal in target_new_signals:
        target.add_signal(signal)

    for signal in target.entity.interfaces:
        setattr(target, signal.name, signal)


def get_architecture_processes(_architecture):
    for p in type(_architecture).__dict__.values():
        if isinstance(p, Process):
            p.architecture = _architecture
            p.invoke()


def get_subtypes_from_list(types):
    __types = []
    for _type in types:
        _types = get_subtypes_recursive(_type)
        for _t in reversed(_types):
            if _t not in __types:
                __types.append(_t)
    return __types


def get_subtypes_recursive(_type):
    subtypes = [_type]
    try:
        for sub in _type.subtype:
            subtypes += get_subtypes_recursive(sub)
    except AttributeError:
        pass
    finally:
        return subtypes


def get_architecture_types(target):
    target.types = get_subtypes_from_list(
        [signal.type for signal in list(itertools.chain(*[target.signals, target.entity.interfaces]))])

    custom_types = []

    for _type in target.types:
        if _type.requires is not None:
            for key in _type.requires.keys():
                if key in target.libraries:
                    for key_new in _type.requires[key]:
                        if key_new not in target.libraries[key]:
                            target.libraries[key].add(key_new)

                else:
                    target.libraries[key] = set([k for k in _type.requires[key]]) \
                        if isinstance(_type.requires[key], (list, tuple)) else [_type.requires[key]]
                    if hasattr(_type, 'package'):
                        target.packages.add(_type.package)
        else:
            custom_types.append(_type)
    target.typestrings = generate_typestrings(custom_types)
