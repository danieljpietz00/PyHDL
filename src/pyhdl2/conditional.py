from typing import Callable, List, Union
from .core import _PHDLObj
from .type import isarray
from .architecture import Architecture
from .arithmetic import ArithmeticStack
from .process import Process, _get_current_process
from copy import deepcopy


class Conditional(_PHDLObj):

    def __init__(self, architecture: Architecture, process: Process, condition: ArithmeticStack):
        self.architecture = architecture
        self.process = process
        self.condition = condition
        self.if_str = ''
        self.parent: Union[Process, Conditional, None] = None
        self.childrenStrings: List[str] = []
        self._if_strs: List[str] = []
        pass

    def __call__(self, func: Callable[[], None]):
        # This is
        global ifStack
        self.parent = ifStack[-1] if len(ifStack) > 0 else self.process
        pre_signals = deepcopy(self.process.get_signals())
        ifStack.append(self)
        func()
        ifStack.pop()
        post_signals = self.process.get_signals()

        all_sigs = []

        for pre_signal, post_signal in zip(pre_signals, post_signals):
            if isarray(pre_signal.type):
                for pre_arr, pos_arr in zip(pre_signal, post_signal):
                    all_sigs.append((pre_arr, pos_arr))
            else:
                all_sigs.append((pre_signal, post_signal))

        for pre_signal, post_signal in all_sigs:
            if pre_signal.next is not None and post_signal.next is not None \
                    and pre_signal.next.value() != post_signal.next.value():
                raise ValueError("Cannot make assignment to value used in if statement")
            elif pre_signal.next is None and post_signal.next is not None:
                self._if_strs.append(f"\t{post_signal.name} <= {post_signal.next.value()};")
                post_signal.next = None

        nl = '\n'
        tab = '\t'

        self.if_str = f"\t{func.__name__}: if {self.condition.value()} then \n" \
                      f"{f'{nl}'.join(self._if_strs)} \n" \
                      f"\tend if {func.__name__};"
        self.if_str = self.if_str.replace(nl, f"{nl}{tab * (len(ifStack) + 1)}")

        self.parent.add_if(self)
        pass

    def add_if(self, _if):
        self._if_strs.append(f"\n{_if.value()}")

    def value(self):
        return self.if_str
        pass


ifStack: List[Conditional] = []


def IF(condition):
    return Conditional(_get_current_process().architecture, _get_current_process(), condition)