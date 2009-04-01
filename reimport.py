"""reimport python modules"""
import sys
import os
import gc
import inspect
import weakref



def reimport(*modules):
    """reimport modules in a single transaction, by name or module reference"""
    reloadSet = set()

    # Get names of all modules being reloaded
    for module in modules:
        name, target = find_exact_target(module)
        if not target:
            raise ValueError("Module %r not found" % module)
        if inspect.isbuiltin(target):
            raise ValueError("Cannot reimport builtin, %r" % name)
        if not is_code_module(target):
            raise ValueError("Cannot reimport extension, %r" % name)

        reloadSet.update(find_reloading_modules(name))

    # Sort module names and call unimports
    reloadNames = package_depth_sort(reloadSet)
    print "REIMPORT:", reloadNames
    for __unimport__ in find_unimports(reloadNames):
        __unimport__()

    # Move modules out of sys
    oldModules = {}
    for name in reloadNames:
        oldModules[name] = sys.modules.pop(name)

    # Reimport modules, trying to rollback on exceptions
    try:
        for name in reloadNames:
            if name not in sys.modules:
                __import__(name)
    except StandardError:
        for __unimport__ in find_unimports(reloadNames):
            try:
                __unimport__()
            except StandardError:
                pass
        sys.modules.update(oldModules)
        raise

    # Rejigger the universe
    for name in reversed(reloadNames):
        old = oldModules[name]
        new = sys.modules[name]
        filename = new.__file__
        if filename.endswith(".pyo") or filename.endswith(".pyc"):
            filename = filename[:-1]
        rejigger_module(old, new, filename)

    # Success !   ?



def is_code_module(module):
    """determine if a module comes from python code"""
    filename = inspect.getsourcefile(module) or "x.notfound"
    extension = os.path.splitext(filename)[1]
    return extension in (".py", ".pyc", ".pyo")



def find_exact_target(module):
    """given a module name or object, find the
            base module where reimport will happen."""
    # Find list of actual modules from names or module references
    actualModule = sys.modules.get(module)
    if actualModule is not None:
        name = module
    else:
        for name, mod in sys.modules.iteritems():
            if mod is module:
                actualModule = module
                break
        else:
            return "", None

    # Find highest level parent package that has unimport callback
    parentName = name
    while True:
        parentName = parentName.rpartition(".")[0]
        if not parentName:
            return name, actualModule
        parentModule = sys.modules.get(parentName)
        unimport = getattr(parentModule, "__unimport__", None)
        if unimport is not None:
            return parentName, parentModule


def find_reloading_modules(name):
    """Find all modules that will be reloaded from given name"""
    modules = [name]
    childNames = name + "."
    for name in sys.modules.keys():
        if name.startswith(childNames) and is_code_module(sys.modules[name]):
            modules.append(name)
    return modules


def package_depth_sort(names):
    """Sort a list of module names by their package depth"""
    def packageDepth(name):
        return name.count(".")
    return sorted(names, key=packageDepth)


def find_unimports(moduleNames):
    """Get unimport callbacks for a list of module names"""
    unimports = []
    for name in reversed(moduleNames):
        unimport = getattr(sys.modules.get(name), "__unimport__", None)
        if unimport:
            unimports.append(unimport)
    return unimports



# to rejigger is to copy internal values from new to old
# and then to swap external references from old to new


def rejigger_module(old, new, filename):
    """Tell everyone that new is the new old, recursive"""
#    print "rejigger module:", filename
    oldVars = vars(old)
    newVars = vars(new)
    
    old.__doc__ = new.__doc__

    for name, value in newVars.iteritems():
        if name.startswith("__"):
            continue
        
        try: objfile = inspect.getsourcefile(value)
        except TypeError: objfile = ""
        
#        print "  modobj:", name, objfile
        if name in oldVars:
            oldValue = oldVars[name]

            if inspect.isclass(value) and inspect.getsourcefile(value) == filename:
                rejigger_class(oldValue, value)
            
            elif inspect.isfunction(value) and inspect.getsourcefile(value) == filename:
                rejigger_func(oldValue, value)
        
        setattr(old, name, value)

    for name in oldVars.keys():
        if name not in newVars:
            remove_refs(getattr(old, name))
            delattr(old, name)
    
    swap_refs(old, new)



def rejigger_class(old, new):
#    print "    rejigger class:", hex(id(old)), hex(id(new)), old
    oldVars = vars(old)
    newVars = vars(new)

    for name, value in newVars.iteritems():
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        if name in oldVars:
#            print "      classobj:", name, value, inspect.isclass(value), inspect.isfunction(value), inspect.ismethod(value)
            oldValue = oldVars[name]

            if inspect.isclass(value):
                rejigger_class(oldValue, value)
            
            elif inspect.isfunction(value):
                rejigger_func(oldValue, value)

#            elif inspect.ismethod(value):
#                rejigger_func(oldValue.im_func, value.im_func)
#                swap_refs(oldValue, value)

        setattr(old, name, value)
    
    for name in oldVars.keys():
        if name not in newVars:
            remove_refs(getattr(old, name))
            delattr(old, name)

    swap_refs(old, new)



def rejigger_func(old, new):
#    print "       rejigger func:", old
#    print "          OLD:", old(None)
#    print "          NEW:", new(None)
    old.func_code = new.func_code
    old.func_doc = new.func_doc
    old.func_defaults = new.func_defaults
    swap_refs(old, new)

    

_recursive_tuple_swap = set()


def swap_refs(old, new):
    """Swap references from one object to another"""
    # Swap weak references
    refs = weakref.getweakrefs(old)
    if not refs:
        return
    try:
        newRef = weakref.ref(new)
    except ValueError:
        return
    for oldRef in refs:
        swap_refs(oldRef, newRef)

    # Swap through garbage collector
    for container in gc.get_referrers(old):
        containerType = type(container)
        
        if containerType == list:
            while True:
                try:
                    index = container.index(old)
                except ValueError:
                    break
                container[index] = new
        
        elif containerType == tuple:
            # protect from recursive tuples
            orig = container
            if id(orig) in _recursive_tuple_swap:
                continue
            _recursive_tuple_swap.add(id(orig))
            try:
                container = list(container)
                while True:
                    try:
                        index = container.index(old)
                    except ValueError:
                        break
                    container[index] = new
                container = tuple(container)
                swap_refs(orig, container)
            finally:
                _recursive_tuple_swap.remove(id(orig))
        
        elif containerType == dict:
            if old in container:
                container[new] = container.pop(old)
            for k,v in container.iteritems():
                if v is old:
                    container[k] = new

#        elif containerType == set:
#            container.remove(old)
#            container.add(new)

        else:
            print "unknown swap:", type(container), container, "for", new

       

def remove_refs(old):
    """Remove references to an object"""        
    # Remove through garbage collector
    for container in gc.get_referrers(old):
        containerType = type(container)

        if containerType == list:
            while True:
                try:
                    container.remove(old)
                except ValueError:
                    break
        
        elif containerType == tuple:
            # protect from recursive tuples
            orig = container
            if id(orig) in _recursive_tuple_swap:
                continue
            _recursive_tuple_swap.add(id(orig))
            try:
                container = list(container)
                while True:
                    try:
                        container.remove(old)
                    except ValueError:
                        break
                container = tuple(container)
                swap_refs(orig, container)
            finally:
                _recursive_tuple_swap.remove(id(orig))
        
        elif containerType == dict:
            if old in container:
                container.pop(old)
            for k,v in container.items():
                if v is old:
                    del container[k]

        elif containerType == set:
            container.remove(old)
            
#        else:
#            print "unknown del:", type(container), container


