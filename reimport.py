# MIT Licensed
# Copyright (c) 2009 Peter Shinners <pete@shinners.org> 
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


__all__ = ["reimport", "modified"]


import sys
import os
import gc
import inspect
import weakref
import time


_previous_scan_time = time.time() - 1.0
_module_timestamps = {}

# find the 'instance' old style type
class _OldClass: pass
_InstanceType = type(_OldClass())
del _OldClass



def reimport(*modules):
    """Reimport python modules. Multiple modules can be passed either by
        name or by reference. Only pure python modules can be reimported.
        """
    __internal_swaprefs_ignore__ = "reimport"
    reloadSet = set()

    # Get names of all modules being reloaded
    for module in modules:
        name, target = _find_exact_target(module)
        if not target:
            raise ValueError("Module %r not found" % module)
        if inspect.isbuiltin(target):
            raise ValueError("Cannot reimport builtin, %r" % name)
        if not _is_code_module(target):
            raise ValueError("Cannot reimport extension, %r" % name)

        reloadSet.update(_find_reloading_modules(name))

    # Sort module names 
    reloadNames = _package_depth_sort(reloadSet, False)

    # Move modules out of sys
    oldModules = {}
    for name in reloadNames:
        oldModules[name] = sys.modules.pop(name)
    prevNames = set(sys.modules)

    # Reimport modules, trying to rollback on exceptions
    try:
        for name in reloadNames:
            if name not in sys.modules:
                __import__(name)

    except StandardError:
        # Try to dissolve any newly import modules and revive the old ones
        newNames = set(sys.modules) - prevNames
        newNames = _package_depth_sort(newNames, True)
        for name in newNames:
            _unimport_module(sys.modules.pop(name))
        sys.modules.update(oldModules)
        raise

    # Update timestamps for loaded time
    now = time.time() - 1.0
    for name in reloadNames:
        _module_timestamps[name] = now

    # Rejigger the universe
    ignores = (id(oldModules), )
    for name in reversed(reloadNames):
        old = oldModules[name]
        new = sys.modules[name]
        filename = new.__file__
        if filename.endswith(".pyo") or filename.endswith(".pyc"):
            filename = filename[:-1]
        _rejigger_module(old, new, filename, ignores)



def modified(path=None):
    """Find loaded modules that have changed on disk under the given path.
        If no path is given then all modules are searched. This cannot 
        detect modules that have changed before the reimport module was
        actually imported.
        """
    global _previous_scan_time
    modules = []
    
    if path:
        path = os.path.normpath(path) + os.sep
    
    for name, module in sys.modules.items():
        filename = _is_code_module(module)
        if not filename:
            continue

        prevTime = _module_timestamps.setdefault(name, _previous_scan_time)
        filename = os.path.normpath(os.path.abspath(filename))
        if path and not filename.startswith(path):
            continue

        # Check file timestamp, give priority to filename with .py
        filename, extension = os.path.splitext(filename)
        try:
            diskTime = os.path.getmtime(filename + ".py")
        except OSError:
            if extension != ".py":
                try:
                    diskTime = os.path.getmtime(filename + extension)
                except OSError:
                    diskTime = None
            else:
                diskTime = None
                
        if diskTime is not None and prevTime < diskTime:
            modules.append(name)

    _previous_scan_time = time.time()
    return modules



def _is_code_module(module):
    """Determine if a module comes from python code"""
    try:
        filename = inspect.getsourcefile(module) or "x.notfound"
    except StandardError:
        filename = ""
    extension = os.path.splitext(filename)[1]
    if extension in (".py", ".pyc", ".pyo"):
        return filename
    return ""



def _find_exact_target(module):
    """Given a module name or object, find the
            base module where reimport will happen."""
    # Given a name or a module, find both the name and the module
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

    # Find highest level parent package that has package_reimport magic
    parentName = name
    while True:
        splitName = parentName.rsplit(".", 1)
        if len(splitName) <= 1:
            return name, actualModule
        parentName = splitName[0]
        
        parentModule = sys.modules.get(parentName)
        if getattr(parentModule, "__package_reimport__", None):
            name = parentName
            actualModule = parentModule



def _find_reloading_modules(name):
    """Find all modules that will be reloaded from given name"""
    modules = [name]
    childNames = name + "."
    for name in sys.modules.keys():
        if name.startswith(childNames) and _is_code_module(sys.modules[name]):
            modules.append(name)
    return modules



def _package_depth_sort(names, reverse):
    """Sort a list of module names by their package depth"""
    def packageDepth(name):
        return name.count(".")
    return sorted(names, key=packageDepth, reverse=reverse)



# To rejigger is to copy internal values from new to old
# and then to swap external references from old to new


def _rejigger_module(old, new, filename, ignores):
    """Mighty morphin power modules"""
    __internal_swaprefs_ignore__ = "rejigger_module"
    oldVars = vars(old)
    newVars = vars(new)
    ignores += (id(oldVars),)
    old.__doc__ = new.__doc__

    for name, value in newVars.iteritems():
        try: objfile = inspect.getsourcefile(value)
        except TypeError: objfile = ""
        
        if name in oldVars:
            oldValue = oldVars[name]
            if oldValue is value:
                continue

            if objfile == filename:
                if inspect.isclass(value):
                    _rejigger_class(oldValue, value, ignores)
                    
                elif inspect.isfunction(value):
                    _rejigger_func(oldValue, value, ignores)
        
        setattr(old, name, value)

    for name in oldVars.keys():
        if name not in newVars:
            _remove_refs(getattr(old, name), ignores)
            delattr(old, name)
    
    _swap_refs(old, new, ignores)



def _rejigger_class(old, new, ignores):
    """Mighty morphin power classes"""
    __internal_swaprefs_ignore__ = "rejigger_class"    
    oldVars = vars(old)
    newVars = vars(new)
    ignores += (id(oldVars),)    

    for name, value in newVars.iteritems():
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        if name in oldVars:
            oldValue = oldVars[name]
            if oldValue is value:
                continue

            if inspect.isclass(value) and value.__module__ == new.__module__:
                _rejigger_class(oldValue, value, ignores)
            
            elif inspect.isfunction(value):
                _rejigger_func(oldValue, value, ignores)

        setattr(old, name, value)
    
    for name in oldVars.keys():
        if name not in newVars:
            _remove_refs(getattr(old, name), ignores)
            delattr(old, name)

    _swap_refs(old, new, ignores)



def _rejigger_func(old, new, ignores):
    """Mighty morphin power functions"""
    __internal_swaprefs_ignore__ = "rejigger_func"    
    old.func_code = new.func_code
    old.func_doc = new.func_doc
    old.func_defaults = new.func_defaults
    old.func_dict = new.func_dict
    _swap_refs(old, new, ignores)



def _unimport_module(old, filename, ignores):
    """Try to remove traces of reimported module after failure"""
    __internal_swaprefs_ignore__ = "unimport_module"
    oldVars = vars(old)
    ignores += (id(oldVars),)

    for name, value in oldVars.iteritems():
        try: objfile = inspect.getsourcefile(value)
        except TypeError: objfile = ""
        
        if objfile == filename:
            if inspect.isclass(value):
                _unimport_class(value, ignores)

        _remove_refs(value, ignores)
        delattr(old, name)
    
    _remove_refs(old, ignores)



def _unimport_class(old, ignores):
    """Try to remove traces of reimported class after failure"""
    __internal_swaprefs_ignore__ = "unimport_class"    
    oldVars = vars(old)
    ignores += (id(oldVars),)    

    for name, value in oldVars.iteritems():
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        _remove_refs(value, ignores)
        delattr(old, name)

    _remove_refs(old, ignores)



_recursive_tuple_swap = set()



def _swap_refs(old, new, ignores):
    """Swap references from one object to another"""
    __internal_swaprefs_ignore__ = "swap_refs"    
    # Swap weak references
    refs = weakref.getweakrefs(old)
    if refs:
        try:
            newRef = weakref.ref(new)
        except ValueError:
            pass
        else:
            for oldRef in refs:
                _swap_refs(oldRef, newRef, ignores + (id(refs),))
    del refs

    # Swap through garbage collector
    referrers = gc.get_referrers(old)
    for container in referrers:
        if id(container) in ignores:
            continue
        containerType = type(container)
        
        if containerType is list:
            while True:
                try:
                    index = container.index(old)
                except ValueError:
                    break
                container[index] = new
        
        elif containerType is tuple:
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
                _swap_refs(orig, container, ignores + (id(referrers),))
            finally:
                _recursive_tuple_swap.remove(id(orig))
        
        elif containerType is dict:
            if "__internal_swaprefs_ignore__" not in container:
                if old in container:
                    container[new] = container.pop(old)
                for k,v in container.iteritems():
                    if v is old:
                        container[k] = new

        elif containerType is set:
            container.remove(old)
            container.add(new)
            
        elif containerType == type:
            if old in container.__bases__:
                bases = list(container.__bases__)
                bases[bases.index(old)] = new
                container.__bases__ = tuple(bases)
        
        elif type(container) is old:
            container.__class__ = new
        
        elif containerType is _InstanceType:
            if container.__class__ is old:
                container.__class__ = new

       

def _remove_refs(old, ignores):
    """Remove references to a discontinued object"""
    __internal_swaprefs_ignore__ = "remove_refs"
    
    # Ignore builtin immutables that keep no other references
    _isinst = isinstance
    if (old is None or _isinst(old, int) or _isinst(old, basestring)
                or _isinst(old, float) or _isinst(old, complex)):
        return
    
    # Remove through garbage collector
    for container in gc.get_referrers(old):
        if id(container) in ignores:
            continue
        containerType = type(container)

        if containerType == list:
            while True:
                try:
                    container.remove(old)
                except ValueError:
                    break
        
        elif containerType == tuple:
            orig = container
            container = list(container)
            while True:
                try:
                    container.remove(old)
                except ValueError:
                    break
            container = tuple(container)
            _swap_refs(orig, container, ignores)
        
        elif containerType == dict:
            if old in container:
                container.pop(old)
            for k,v in container.items():
                if v is old:
                    del container[k]

        elif containerType == set:
            container.remove(old)
            
        elif containerType == type:
            if old in container.__bases__:
                bases = list(container.__bases__)
                bases.remove(old)
                container.__bases__ = tuple(bases)
        
        elif type(container) is old:
            container.__class__ = old.__bases__[0]
            _remove_refs(container, ignores)
        
        elif containerType is _InstanceType:
            if container.__class__ is old:
                if container.__class__.__bases__:
                    container.__class__ = container.__class__.__bases__[0]
                _remove_refs(container, ignores)
