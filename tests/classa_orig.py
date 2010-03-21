print "--ORIGINAL A MODULE IMPORTED"

import time


class ClassA(object):
    """original class a"""
    def runA(self):
        """original class a runA"""
        print "Class A Run"
    
    ClassStatic1 = 12
    ClassStatic2 = "twelve"
    def onlyOrigA(self): pass


ModStatic1 = 13
ModStatic2 = "thirteen"
WillItDelete1 = None
WillItDelete2 = True
WillItDelete3 = False

    
objA = ClassA()



class SlotA(object):
    __slots__ = ("one", "two", "three")
    def __init__(self):
        self.one = 1
        self.two = 2
        self.three = 3

    def getone(self):
        return self.one


slotA = SlotA()


class ClassToFunc(object):
    pass


def FuncToClass():
    pass


def __reimported__(old):
    print "DO NOT USE THIS REIMPORT! I AM STALE"
    raise RuntimeError("Do not want")
    print "classa being reimported, from:", old
    return True
