print "--ORIGINAL A MODULE IMPORTED"


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

    
objA = ClassA()


def __reimported__(old):
    print "DO NOT USE THIS REIMPORT! I AM STALE"
    raise RuntimeError("Do not want")
    print "classa being reimported, from:", old
    return True
