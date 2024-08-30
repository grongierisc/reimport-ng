"""
This module intends to be a full featured replacement for Python's reload
function. It is targeted towards making a reload that works for Python
plugins and extensions used by longer running applications.

Reimport currently supports Python 2.4 through 2.6.

By its very nature, this is not a completely solvable problem. The goal of
this module is to make the most common sorts of updates work well. It also
allows individual modules and package to assist in the process. A more
detailed description of what happens is at
http://code.google.com/p/reimport .
"""


__all__ = ["reimport", "modified"]


import sys
import os
import gc
import imp
import inspect
import weakref
import traceback
import time



__version__ = "1.4"
__author__ = "Peter Shinners <pete@shinners.org>"
__license__ = "MIT"
__url__ = "http://code.google.com/p/reimport"



_previous_scan_time = time.time() - 1.0
_module_timestamps = {}


# find the 'instance' old style type
class _OldClass: 
    pass
_InstanceType = type(_OldClass())
del _OldClass



def reimport(*modules):
    """Reimport python modules. Multiple modules can be passed either by
        name or by reference. Only pure python modules can be reimported.
        
        For advanced control, global variables can be placed in modules
        that allows finer control of the reimport process.
        
        If a package module has a true value for "__package_reimport__"
        then that entire package will be reimported when any of its children
        packages or modules are reimported.
        
        If a package module defines __reimported__ it must be a callable
        function that accepts one argument and returns a bool. The argument
        is the reference to the old version of that module before any
        cleanup has happened. The function should normally return True to
        allow the standard reimport cleanup. If the function returns false
        then cleanup will be disabled for only that module. Any exceptions
        raised during the callback will be handled by traceback.print_exc,
        similar to what happens with tracebacks in the __del__ method.
        """
    __internal_swaprefs_ignore__ = "reimport"
    reload_set = set()

    if not modules:
        return

    # Get names of all modules being reloaded
    for module in modules:
        name, target = _find_exact_target(module)
        if not target:
            raise ValueError("Module %r not found" % module)
        if not _is_code_module(target):
            raise ValueError("Cannot reimport extension, %r" % name)

        reload_set.update(_find_reloading_modules(name))

    # Sort module names 
    reload_names = _package_depth_sort(reload_set, False)

    # Check for SyntaxErrors ahead of time. This won't catch all
    # possible SyntaxErrors or any other ImportErrors. But these
    # should be the most common problems, and now is the cleanest
    # time to abort.
    # I know this gets compiled again anyways. It could be
    # avoided with py_compile, but I will not be the creator
    # of messy .pyc files!
    for name in reload_names:
        filename = getattr(sys.modules[name], "__file__", None)
        if not filename:
            continue
        pyname = os.path.splitext(filename)[0] + ".py"
        try:
            data = open(pyname, "rU").read() + "\n"
        except (IOError, OSError):
            continue
        
        compile(data, pyname, "exec", 0, False)  # Let this raise exceptions

    clear_type_cache = getattr(sys, "_clear_type_cache", None)
    if clear_type_cache:
        clear_type_cache()

    # Begin changing things. We "grab the GIL", so other threads
    # don't get a chance to see our half-baked universe
    imp.acquire_lock()
    prev_interval = sys.getcheckinterval()
    sys.setcheckinterval(min(sys.maxint, 0x7fffffff))
    try:

        # Python will munge the parent package on import. Remember original value
        parent_values = []
        parent_package_deleted = lambda: None
        for name in reload_names:
            parent_package_name = name.rsplit(".", 1)
            if len(parent_package_name) == 2:
                parent_package = sys.modules.get(parent_package_name[0], None)
                parent_value = getattr(parent_package, parent_package_name[1], parent_package_deleted)
                if parent_value != sys.modules[name]:
                    parent_values.append((parent_package, parent_package_name[1], parent_value))
                parent_package = parent_value = None

        # Move modules out of sys
        old_modules = {}
        for name in reload_names:
            old_modules[name] = sys.modules.pop(name)
        ignores = (id(old_modules),)
        prev_names = set(sys.modules)

        # Reimport modules, trying to rollback on exceptions
        try:
            try:
                for name in reload_names:
                    if name not in sys.modules:
                        __import__(name)

            except StandardError:
                # Try to dissolve any newly import modules and revive the old ones
                new_names = set(sys.modules) - prev_names
                new_names = _package_depth_sort(new_names, True)
                for name in new_names:
                    backout_module = sys.modules.pop(name, None)
                    if backout_module is not None:
                        _unimport(backout_module, ignores)
                    del backout_module

                sys.modules.update(old_modules)
                raise

        finally:
            # Fix Python automatically shoving of children into parent packages
            for parent_package, name, value in parent_values:
                if value == parent_package_deleted:
                    try:
                        delattr(parent_package, name)
                    except AttributeError:
                        pass
                else:
                    setattr(parent_package, name, value)
            parent_values = parent_package = parent_package_deleted = value = None

        new_names = set(sys.modules) - prev_names
        new_names = _package_depth_sort(new_names, True)

        # Update timestamps for loaded time
        now = time.time() - 1.0
        for name in new_names:
            _module_timestamps[name] = (now, True)

        # Push exported namespaces into parent packages
        push_symbols = {}
        for name in new_names:
            old_module = old_modules.get(name)
            if not old_module:
                continue
            parents = _find_parent_importers(name, old_module, new_names)
            push_symbols[name] = parents
        for name, parents in push_symbols.iteritems():
            for parent in parents:
                old_module = old_modules[name]
                new_module = sys.modules[name]
                _push_imported_symbols(new_module, old_module, parent)

        # Rejigger the universe
        for name in new_names:
            old = old_modules.get(name)
            if not old:
                continue
            new = sys.modules[name]
            rejigger = True
            reimported = getattr(new, "__reimported__", None)
            if reimported:
                try:
                    rejigger = reimported(old)
                except StandardError:
                    # What else can we do? the callbacks must go on
                    # Note, this is same as __del__ behaviour. /shrug
                    traceback.print_exc()

            if rejigger:
                _rejigger_module(old, new, ignores)
            else:
                _unimport_module(new, ignores)

    finally:
        if clear_type_cache:
            clear_type_cache()

        # Restore the GIL
        imp.release_lock()
        sys.setcheckinterval(prev_interval)
        time.sleep(0)



def modified(path=None):
    """Find loaded modules that have changed on disk under the given path.
        If no path is given then all modules are searched.
        """
    global _previous_scan_time
    modules = []
    
    if path:
        path = os.path.normpath(path) + os.sep
        
    default_time = (_previous_scan_time, False)
    pyc_ext = __debug__ and ".pyc" or ".pyo"
    
    for name, module in sys.modules.items():
        filename = _is_code_module(module)
        if not filename:
            continue

        filename = os.path.normpath(filename)
        prev_time, prev_scan = _module_timestamps.setdefault(name, default_time)
        if path and not filename.startswith(path):
            continue

        # Get timestamp of .pyc if this is first time checking this module
        if not prev_scan:
            pyc_name = os.path.splitext(filename)[0] + pyc_ext
            if pyc_name != filename:
                try:
                    prev_time = os.path.getmtime(pyc_name)
                except OSError:
                    pass
            _module_timestamps[name] = (prev_time, True)

        # Get timestamp of source file
        try:
            disk_time = os.path.getmtime(filename)
        except OSError:
            disk_time = None
                
        if disk_time is not None and prev_time < disk_time:
            modules.append(name)

    _previous_scan_time = time.time()
    return modules


def _safevars(obj):
    try:
        return vars(obj)
    except TypeError:
        return {}


def _is_code_module(module):
    """Determine if a module comes from python code"""
    # getsourcefile will not return "bare" pyc modules. we can reload those?
    try:
        return inspect.getsourcefile(module) or ""
    except TypeError:
        return ""



def _find_exact_target(module):
    """Given a module name or object, find the
            base module where reimport will happen."""
    # Given a name or a module, find both the name and the module
    actual_module = sys.modules.get(module)
    if actual_module is not None:
        name = module
    else:
        for name, mod in sys.modules.iteritems():
            if mod is module:
                actual_module = module
                break
        else:
            return "", None

    # Find highest level parent package that has package_reimport magic
    parent_name = name
    while True:
        split_name = parent_name.rsplit(".", 1)
        if len(split_name) <= 1:
            return name, actual_module
        parent_name = split_name[0]
        
        parent_module = sys.modules.get(parent_name)
        if getattr(parent_module, "__package_reimport__", None):
            name = parent_name
            actual_module = parent_module



def _find_reloading_modules(name):
    """Find all modules that will be reloaded from given name"""
    modules = [name]
    child_names = name + "."
    for name in sys.modules.keys():
        if name.startswith(child_names) and _is_code_module(sys.modules[name]):
            modules.append(name)
    return modules



def _package_depth_sort(names, reverse):
    """Sort a list of module names by their package depth"""
    def packageDepth(name):
        return name.count(".")
    return sorted(names, key=packageDepth, reverse=reverse)



def _find_module_exports(module):
    all_names = getattr(module, "__all__", ())
    if not all_names:
        all_names = [n for n in dir(module) if n[0] != "_"]
    return set(all_names)



def _find_parent_importers(name, old_module, new_names):
    """Find parents of reimported module that have all exported symbols"""
    parents = []

    # Get exported symbols
    exports = _find_module_exports(old_module)
    if not exports:
        return parents

    # Find non-reimported parents that have all old symbols
    parent = name
    while True:
        names = parent.rsplit(".", 1)
        if len(names) <= 1:
            break
        parent = names[0]
        if parent in new_names:
            continue
        parent_module = sys.modules[parent]
        if not exports - set(dir(parent_module)):
            parents.append(parent_module)
    
    return parents



def _push_imported_symbols(new_module, old_module, parent):
    """Transfer changes symbols from a child module to a parent package"""
    # This assumes everything in old_module is already found in parent
    old_exports = _find_module_exports(old_module)
    new_exports = _find_module_exports(new_module)

    # Delete missing symbols
    for name in old_exports - new_exports:
        delattr(parent, name)
    
    # Find symbols in new module, use placeholder if missing
    symbols = {}
    for name in new_exports:
        try:
            symbols[name] = getattr(new_module, name)
        except AttributeError:
            holder = type(name, (_MissingAllReference,),
                        {"__module__":new_module.__name__})
            symbols[name] = holder()
        
    
    # Add new symbols
    for name in new_exports - old_exports:
        setattr(parent, name, symbols[name])
    
    # Update existing symbols
    for name in new_exports & old_exports:
        old_value = getattr(old_module, name)
        if getattr(parent, name) is old_value:
            setattr(parent, name, symbols[name])
    


# To rejigger is to copy internal values from new to old
# and then to swap external references from old to new


def _rejigger_module(old, new, ignores):
    """Mighty morphin power modules"""
    __internal_swaprefs_ignore__ = "rejigger_module"
    old_vars = _safevars(old)
    new_vars = _safevars(new)
    ignores += (id(old_vars),)
    old.__doc__ = new.__doc__

    # Get filename used by python code
    filename = new.__file__

    for name, value in new_vars.iteritems():
        if name in old_vars:
            old_value = old_vars[name]
            if old_value is value:
                continue

            if _from_file(filename, value):
                if inspect.isclass(value):
                    if inspect.isclass(old_value):
                        _rejigger_class(old_value, value, ignores)
                    
                elif inspect.isfunction(value):
                    if inspect.isfunction(old_value):
                        _rejigger_func(old_value, value, ignores)
        
        setattr(old, name, value)

    for name, value in old_vars.items():
        if name not in new_vars:
            delattr(old, name)
            if _from_file(filename, value):
                if inspect.isclass(value) or inspect.isfunction(value):
                    _remove_refs(value, ignores)
    
    _swap_refs(old, new, ignores)



def _from_file(filename, value):
    """Test if object came from a filename, works for pyc/py confusion"""
    try:
        objfile = inspect.getsourcefile(value)
    except TypeError:
        return False
    return bool(objfile) and objfile.startswith(filename)



def _rejigger_class(old, new, ignores):
    """Mighty morphin power classes"""
    __internal_swaprefs_ignore__ = "rejigger_class"    
    old_vars = _safevars(old)
    new_vars = _safevars(new)
    ignores += (id(old_vars),)    

    slotted = hasattr(old, "__slots__") and isinstance(old.__slots__, tuple)
    ignore_attrs = ["__dict__", "__doc__", "__weakref__"]
    if slotted:
        ignore_attrs.extend(old.__slots__)
        ignore_attrs.append("__slots__")
    ignore_attrs = tuple(ignore_attrs)

    for name, value in new_vars.iteritems():
        if name in ignore_attrs:
            continue

        if name in old_vars:
            old_value = old_vars[name]
            if old_value is value:
                continue

            if inspect.isclass(value) and value.__module__ == new.__module__:
                _rejigger_class(old_value, value, ignores)
            
            elif inspect.isfunction(value):
                _rejigger_func(old_value, value, ignores)

        setattr(old, name, value)
    
    for name, value in old_vars.items():
        if name not in new_vars:
            delattr(old, name)
            _remove_refs(value, ignores)

    _swap_refs(old, new, ignores)



def _rejigger_func(old, new, ignores):
    """Mighty morphin power functions"""
    __internal_swaprefs_ignore__ = "rejigger_func"    
    old.func_code = new.func_code
    old.func_doc = new.func_doc
    old.func_defaults = new.func_defaults
    old.func_dict = new.func_dict
    _swap_refs(old, new, ignores)



def _unimport(old, ignores):
    """Unimport something, mainly used to rollback a reimport"""
    if isinstance(old, type(sys)):
        _unimport_module(old, ignores)
    elif inspect.isclass(old):
        _unimport_class(old, ignores)
    else:
        _remove_refs(old, ignores)
    


def _unimport_module(old, ignores):
    """Remove traces of a module"""
    __internal_swaprefs_ignore__ = "unimport_module"
    old_values = _safevars(old).values()
    ignores += (id(old_values),)    

    # Get filename used by python code
    filename = old.__file__
    fileext = os.path.splitext(filename)
    if fileext in (".pyo", ".pyc", ".pyw"):
        filename = filename[:-1]

    for value in old_values:
        try: objfile = inspect.getsourcefile(value)
        except TypeError: objfile = ""
        
        if objfile == filename:
            if inspect.isclass(value):
                _unimport_class(value, ignores)
                
            elif inspect.isfunction(value):
                _remove_refs(value, ignores)

    _remove_refs(old, ignores)



def _unimport_class(old, ignores):
    """Remove traces of a class"""
    __internal_swaprefs_ignore__ = "unimport_class"    
    old_items = _safevars(old).items()
    ignores += (id(old_items),)    

    for name, value in old_items:
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        if inspect.isclass(value) and value.__module__ == old.__module__:
            _unimport_class(value, ignores)
            
        elif inspect.isfunction(value):
            _remove_refs(value, ignores)

    _remove_refs(old, ignores)




class _MissingAllReference(object):
    """This is a stub placeholder for objects added to __all__ but
        are not actually found.
        """
    def __str__(self, *args):
        raise AttributeError("%r missing from module %r" %
                    (type(self).__name__, type(self).__module__))
    __nonzero__ = __hash__ = __id__ = __cmp__ = __len__ = __iter__ = __str__
    __repr__ = __int__ = __getattr__ = __setattr__ = __delattr__ = __str__
    


_recursive_tuple_swap = set()


def _bonus_containers():
    """Find additional container types, if they are loaded. Returns
        (deque, defaultdict).
        Any of these will be None if not loaded. 
        """
    deque = defaultdict = None
    collections = sys.modules.get("collections", None)
    if collections:
        deque = getattr(collections, "collections", None)
        defaultdict = getattr(collections, "defaultdict", None)
    return deque, defaultdict



def _find_sequence_indices(container, value):
    """Find indices of value in container. The indices will
        be in reverse order, to allow safe editing.
        """
    indices = []
    for i in range(len(container)-1, -1, -1):
        if container[i] is value:
            indices.append(i)
    return indices


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

    deque, defaultdict = _bonus_containers()

    # Swap through garbage collector
    referrers = gc.get_referrers(old)
    for container in referrers:
        if id(container) in ignores:
            continue
        container_type = type(container)
        
        if container_type is list or container_type is deque:
            for index in _find_sequence_indices(container, old):
                container[index] = new
        
        elif container_type is tuple:
            # protect from recursive tuples
            orig = container
            if id(orig) in _recursive_tuple_swap:
                continue
            _recursive_tuple_swap.add(id(orig))
            try:
                container = list(container)
                for index in _find_sequence_indices(container, old):
                    container[index] = new
                container = tuple(container)
                _swap_refs(orig, container, ignores + (id(referrers),))
            finally:
                _recursive_tuple_swap.remove(id(orig))
        
        elif container_type is dict or container_type is defaultdict:
            if "__internal_swaprefs_ignore__" not in container:
                try:
                    if old in container:
                        container[new] = container.pop(old)
                except TypeError:  # Unhashable old value
                    pass
                for k,v in container.iteritems():
                    if v is old:
                        container[k] = new

        elif container_type is set:
            container.remove(old)
            container.add(new)

        elif container_type is type:
            if old in container.__bases__:
                bases = list(container.__bases__)
                bases[bases.index(old)] = new
                container.__bases__ = tuple(bases)
        
        elif type(container) is old:
            try:
                container.__class__ = new
            except TypeError:
                # Type error happens on slotted classes
                pass
        
        elif container_type is _InstanceType:
            if container.__class__ is old:
                container.__class__ = new

       

def _remove_refs(old, ignores):
    """Remove references to a discontinued object"""
    __internal_swaprefs_ignore__ = "remove_refs"
    
    # Ignore builtin immutables that keep no other references
    if old is None or isinstance(old, (int, basestring, float, complex)):
        return

    deque, defaultdict = _bonus_containers()
    
    # Remove through garbage collector
    for container in gc.get_referrers(old):
        if id(container) in ignores:
            continue
        container_type = type(container)

        if container_type is list or container_type is deque:
            for index in _find_sequence_indices(container, old):
                del container[index]
        
        elif container_type is tuple:
            orig = container
            container = list(container)
            for index in _find_sequence_indices(container, old):
                del container[index]
            container = tuple(container)
            _swap_refs(orig, container, ignores)
        
        elif container_type is dict or container_type is defaultdict:
            if "__internal_swaprefs_ignore__" not in container:
                try:
                    container.pop(old, None)
                except TypeError:  # Unhashable old value
                    pass
                for k,v in container.items():
                    if v is old:
                        del container[k]

        elif container_type is set:
            container.remove(old)
