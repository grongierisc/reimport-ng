This module intends to be a full featured replacement for Python's reload function. It is targeted towards making a reload that works for Python plugins and extensions used by longer running applications. 

Reimport currently supports Python 2.4 through 2.7.

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


= Related =

There have been previous attempts at python reimporting. Most are incomplete or frightening, but several of them are worth a closer look.

  * [Livecoding](http://code.google.com/p/livecoding) is one of the more complete, it offers a special case directory tree of Python modules that are treated as live files.
  * [mod_python](http://www.modpython.org) has implemented a similar reloading mechanism. The module reloading itself may be difficult to use outside mod_python's environment.
  * [xreload](http://svn.python.org/projects/sandbox/trunk/xreload) The python source itself comes with a minimal extended reload.
  * [globalsub](http://packages.python.org/globalsub) Replace and restore objects with one another globally.