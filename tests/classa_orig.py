print "--ORIGINAL A MODULE IMPORTED"


class ClassA(object):
    """original class a"""
    def runA(self):
        """original class a runA"""
        print "Class A Run"
        
    def onlyOrigA(self): pass

    
objA = ClassA()

