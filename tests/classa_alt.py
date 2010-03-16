print "--ALTERNATE A MODULE IMPORTED"


class ClassA(object):
    """alternate class a"""
    def runA(self):
        """altername class a runA"""
        print "ALT A Run"
    
    def onlyAltA(self): pass
    
objA = ClassA()

ModStatic1 = 22
ModStatic3 = 1.0


def SlotA(object):
    __slots__ = ("one", "two")
    def __init__(self):
        self.one = 11
        self.two = 22


slotA = SlotA()


def __reimported__(old):
    print "classa being reimported, from:", old
    return True


#klass SYNTAXERR(x): pass