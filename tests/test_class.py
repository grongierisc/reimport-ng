import os
import sys
import shutil
import weakref
import time

def test_class():

    shutil.copy("tests/classa_orig.py", "tests/classa.py")
    
    import classb 
    import classa

    inst = classa.ClassA()

    obj = classa.objA
    assert isinstance(classa.objA, classa.ClassA)
    assert isinstance(inst, classa.ClassA)
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
    slotter = classa.SlotA()
    slotter.one = 111

    goners = ["BUTROS", classa.objA.onlyOrigA, classa.ClassA.__dict__["onlyOrigA"]]


    #assert classa.objA.__doc__ == classa.objA.runA.__doc__
    classa.objA.runA()
    classb.objB.runA()
    obj.runA()
    meth()
    ref().runA()
    weakd[0]().runA()
    weakd[1].runA()
    [c().runA() for c in clss]
    [o.runA() for o in objs]
    [m() for m in meths]
    assert len(goners) == 3
    assert slotter.one == slotter.getone()
    print(classa.ClassToFunc, classa.FuncToClass)
    assert classa.ClassA.ClassStatic1 == inst.ClassStatic1 == 12
    assert hasattr(inst, "ClassStatic2")

    time.sleep(1)
    shutil.copy("tests/classa_alt.py", "tests/classa.py")
    #os.system("rm tests/*.pyc")

    ENSURE_NOT_DELETED1 = "thirteen"
    ENSURE_NOT_DELETED2 = True
    ENSURE_NOT_DELETED3 = False
    ENSURE_NOT_DELETED4 = None

    import reimport

    print( "TIME:", getattr(reimport, "time", None))
    print( "ENSURE:", ENSURE_NOT_DELETED1, ENSURE_NOT_DELETED2, ENSURE_NOT_DELETED3, ENSURE_NOT_DELETED4)

    changed = reimport.modified()# os.path.dirname(__file__))
    print( "Changed modules:", changed)
    #if not changed:
    #    changed.append(classa)
    try:
        reimport.reimport(*changed)
    except Exception as e:
        print( "ROLLBACK BECAUSE OF:", e)
        import traceback
        traceback.print_exc()
        #raise

    print( "TIME:", getattr(reimport, "time", None))
    print( "ENSURE:", ENSURE_NOT_DELETED1, ENSURE_NOT_DELETED2, ENSURE_NOT_DELETED3, ENSURE_NOT_DELETED4)



    print (classa.objA.__doc__, classa.objA.runA.__doc__)
    assert isinstance(classa.objA, classa.ClassA)
    assert isinstance(inst, classa.ClassA)
    classa.objA.runA()
    classb.objB.runA()
    obj.runA()
    [o.runA() for o in objs]
    [m() for m in meths]
    HOLDER1.c().runA()
    HOLDER1.o.runA()
    HOLDER2.c().runA()
    HOLDER2.o.runA()
    HOLDER3.c().runA()
    HOLDER3.o.runA()
    print( len(goners))
    print( slotter.one, slotter.getone())
    print( classa.ClassToFunc, classa.FuncToClass)
    print( classa.ClassA.ClassStatic1, inst.ClassStatic1, hasattr(inst, "ClassStatic2"))



