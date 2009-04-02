import os
import sys
import shutil
import weakref
import time
sys.path.insert(0, "tests")

shutil.copy("tests/classa_orig.py", "tests/classa.py")
os.system("rm tests/*.pyc")

import classa, classb
obj = classa.objA
meth = classa.objA.runA
ref = weakref.ref(classa.objA)
weakd = weakref.WeakValueDictionary()
weakd[0] = classa.ClassA
weakd[1] = classa.objA
clss = (classa.ClassA, classb.ClassB)
objs = (classa.objA, classb.objB)
meths = (classa.objA.runA, classb.objB.runA)
class HOLDER1(object): pass
class HOLDER2: pass
def HOLDER3(): pass
HOLDER1.c = classa.ClassA
HOLDER1.o = classa.objA
HOLDER2.c = classa.ClassA
HOLDER2.o = classa.objA
HOLDER3.c = classa.ClassA
HOLDER3.o = classa.objA
goners = ["BUTROS", classa.objA.onlyOrigA, classa.ClassA.onlyOrigA]


print (classa.objA.__doc__, classa.objA.runA.__doc__)
classa.objA.runA()
classb.objB.runA()
#obj.runA()
#meth()
#ref().runA()
#weakd[0]().runA()
#weakd[1].runA()
#[c().runA() for c in clss]
#[o.runA() for o in objs]
#[m() for m in meths]
print len(goners)#, goners


time.sleep(1)
shutil.copy("tests/classa_alt.py", "tests/classa.py")
os.system("rm tests/*.pyc")


import reimport
changed = reimport.modified(os.path.dirname(__file__))
print "Changed modules:", changed
reimport.reimport(*changed)


print (classa.objA.__doc__, classa.objA.runA.__doc__)
classa.objA.runA()
classb.objB.runA()
#obj.runA()
#[o.runA() for o in objs]
#[m() for m in meths]
#HOLDER1.c().runA()
#HOLDER1.o.runA()
#HOLDER2.c().runA()
#HOLDER2.o.runA()
#HOLDER3.c().runA()
#HOLDER3.o.runA()
print len(goners)#, goners


