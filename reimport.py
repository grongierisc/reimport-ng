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

"""reimport python modules"""


__all__ = ["reimport", "modified"]


import sys
import os
import gc
import inspect
import weakref
import time


_previous_scan_time = time.time() - 1.0
_module_timestamps = {} #dict.fromkeys(sys.modules.iterkeys(), time.time())



def reimport(*modules):
    """reimport modules in a single transaction, by name or module reference"""
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

    # Sort module names and call unimports
    reloadNames = _package_depth_sort(reloadSet)
    for __unimport__ in _find_unimports(reloadNames):
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
        for __unimport__ in _find_unimports(reloadNames):
            try:
                __unimport__()
            except StandardError:
                pass
        sys.modules.update(oldModules)
        raise

    # Update timestamps for loaded time
    now = time.time() - 1.0
    for name in reloadNames:
        _module_timestamps[name] = now

    # Rejigger the universe
    for name in reversed(reloadNames):
        old = oldModules[name]
        new = sys.modules[name]
        filename = new.__file__
        if filename.endswith(".pyo") or filename.endswith(".pyc"):
            filename = filename[:-1]
        _rejigger_module(old, new, filename)

    # Success !   ?


def modified(path=None):
    """Find loaded modules that have changed on disk under the given path.
        If no path is given then all modules are searched."""
    global _previous_scan_time
    modules = []
    
    if path:
        path = os.path.normpath(path) + os.sep
    
    for name, module in sys.modules.iteritems():
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
    """determine if a module comes from python code"""
    try:
        filename = inspect.getsourcefile(module) or "x.notfound"
    except StandardError:
        filename = ""
    extension = os.path.splitext(filename)[1]
    if extension in (".py", ".pyc", ".pyo"):
        return filename
    return ""


def _find_exact_target(module):
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
        # parentName = parentName.rpartition(".")[0]
        # rpartition not supported in Python 2.4
        splitName = parentName.rsplit(".", 1)
        if len(splitName) <= 1:
            return name, actualModule
        parentName = splitName[0]
        
        parentModule = sys.modules.get(parentName)
        unimport = getattr(parentModule, "__unimport__", None)
        if unimport is not None:
            return parentName, parentModule


def _find_reloading_modules(name):
    """Find all modules that will be reloaded from given name"""
    modules = [name]
    childNames = name + "."
    for name in sys.modules.keys():
        if name.startswith(childNames) and _is_code_module(sys.modules[name]):
            modules.append(name)
    return modules


def _package_depth_sort(names):
    """Sort a list of module names by their package depth"""
    def packageDepth(name):
        return name.count(".")
    return sorted(names, key=packageDepth)


def _find_unimports(moduleNames):
    """Get unimport callbacks for a list of module names"""
    unimports = []
    for name in reversed(moduleNames):
        unimport = getattr(sys.modules.get(name), "__unimport__", None)
        if unimport:
            unimports.append(unimport)
    return unimports



# to rejigger is to copy internal values from new to old
# and then to swap external references from old to new


def _rejigger_module(old, new, filename):
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
        
        if name in oldVars:
            oldValue = oldVars[name]

            if inspect.isclass(value) and objfile == filename:
                _rejigger_class(oldValue, value)
            
            elif inspect.isfunction(value) and objfile == filename:
                _rejigger_func(oldValue, value)
        
        setattr(old, name, value)

    for name in oldVars.keys():
        if name not in newVars:
            _remove_refs(getattr(old, name))
            delattr(old, name)
    
    _swap_refs(old, new)



def _rejigger_class(old, new):
#    print "    rejigger class:", hex(id(old)), hex(id(new)), old
    oldVars = vars(old)
    newVars = vars(new)

    for name, value in newVars.iteritems():
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        if name in oldVars:
            oldValue = oldVars[name]

            if inspect.isclass(value):
                _rejigger_class(oldValue, value)
            
            elif inspect.isfunction(value):
                _rejigger_func(oldValue, value)

#            elif inspect.ismethod(value):
#                _rejigger_func(oldValue.im_func, value.im_func)
#                _swap_refs(oldValue, value)

        setattr(old, name, value)
    
    for name in oldVars.keys():
        if name not in newVars:
            _remove_refs(getattr(old, name))
            delattr(old, name)

    _swap_refs(old, new)



def _rejigger_func(old, new):
#    print "       rejigger func:", old
    old.func_code = new.func_code
    old.func_doc = new.func_doc
    old.func_defaults = new.func_defaults
    _swap_refs(old, new)

    

_recursive_tuple_swap = set()


def _swap_refs(old, new):
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
        _swap_refs(oldRef, newRef)

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
                _swap_refs(orig, container)
            finally:
                _recursive_tuple_swap.remove(id(orig))
        
        elif containerType == dict:
            if old in container:
                container[new] = container.pop(old)
            for k,v in container.iteritems():
                if v is old:
                    container[k] = new

        elif containerType == set:
            container.remove(old)
            container.add(new)

       

def _remove_refs(old):
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
            orig = container
            container = list(container)
            while True:
                try:
                    container.remove(old)
                except ValueError:
                    break
            container = tuple(container)
            _swap_refs(orig, container)
        
        elif containerType == dict:
            if old in container:
                container.pop(old)
            for k,v in container.items():
                if v is old:
                    del container[k]

        elif containerType == set:
            container.remove(old)
            
