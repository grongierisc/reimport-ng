print "--ALTERNATE A MODULE IMPORTED"


class ClassA(object):
    """alternate class a"""
    def runA(self):
        """altername class a runA"""
        print "ALT A Run"
    
    def onlyAltA(self): pass
    
objA = ClassA()


def __reimported__(old):
    print "classa being reimported, from:", old
    return True


#klass SYNTAXERR(x): pass