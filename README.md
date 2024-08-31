# Reimport-ng
 
>Reimport-ng is a fork of the original [reimport](https://bitbucket.org/petershinners/reimport) module by Peter Shinners. The original module was last updated in 2014 and is not compatible with Python 3.8+. This fork aims to update the module to work with Python 3.8+ and to fix any bugs that may have been present in the original module.

This module intends to be a full featured replacement for Python's reload function. It is targeted towards making a reload that works for Python plugins and extensions used by longer running applications. 

Reimport currently supports Python 3.8+.

By its very nature, this is not a completely solvable problem. The goal of this module is to make the most common sorts of updates work well. It also allows individual modules and package to assist in the process. A more detailed description of what happens is on the [Wiki](https://bitbucket.org/petershinners/reimport/wiki) page.

## Quick Docs

There are two functions in the API.

    def reimport(*modules):
        """Reimport python modules. Multiple modules can be passed either by
            name or by reference. Only pure python modules can be reimported."""
        return None
    
    def modified(path=None):
        """Find loaded modules that have changed on disk under the given path.
            If no path is given then all modules are searched."""
        return list_of_strings 


## Related

There have been previous attempts at python reimporting. Most are incomplete or frightening, but several of them are worth a closer look.

  * [Livecoding](http://code.google.com/p/livecoding) is one of the more complete, it offers a special case directory tree of Python modules that are treated as live files.
  * [mod_python](http://www.modpython.org) has implemented a similar reloading mechanism. The module reloading itself may be difficult to use outside mod_python's environment.
  * [xreload](http://svn.python.org/projects/sandbox/trunk/xreload) The python source itself comes with a minimal extended reload.
  * [globalsub](http://packages.python.org/globalsub) Replace and restore objects with one another globally.

## Overview of the reimport process

The reimport process is handled in several steps.

- A list of modules and packages are given to be reimported.
- For each module, we check all parent packages for a package_reimport value. If the value is True we will reimport the entire package, instead of just the submodule.
- Build a unique set of final modules and packages to reimport. Sort them by package depth order.
- Check each module for SyntaxError and early exception out.
- Move all packages to be reloaded out of sys.modules and hang onto them.
- Reimport modules one at a time. Check to make sure it hasn't already been imported from a parent package being reimported.
  - If module added values to all that are missing, AttributeError is raised and reimports are rolled back.
- Find reimported callback and pass the old module reference as an argument
    - If callback returns False, do not perform the rejigger for that module
    - Exceptions from the callback are redirected to traceback.print_exc
- Find parent packages that haven't been reimported that appear to import * (change for 1.1)
  - Push exported symbols from children into these parents (change for 1.1)
- Begin rejigger process for each module imported
  - Match old objects to new objects by name
  - Transmute classes and functions in the module from old to new
  - Switch references from the old object to the new
  - For lists, sets, and dictionaries this isn't tricky.
  - For tuples it is trickier, but an attempt is made to build a new tuple, and swap references to the tuple itself.
  - Classes that derive from the old object have their bases modified.
  - Instance have their class swapped
  - Remove references to old objects that have no matching named object
  - Similar process to the above reference switching
  - Note, this doesn't seem to find bound methods to a method that gets dropped
    - My first guess is that the gc doesn't track bound methods? (surprising)

## Credits

Reimport was written by Peter Shinners. The original module was last updated in 2014.