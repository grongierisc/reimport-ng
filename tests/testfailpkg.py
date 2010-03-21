import os
import sys
import shutil
import weakref
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import reimport

shutil.copy("tests/failpkg/child_orig.py", "tests/failpkg/child.py")
import failpkg

print [x for x in dir(failpkg) if not x.startswith("_")]

time.sleep(1)
shutil.copy("tests/failpkg/child_fail.py", "tests/failpkg/child.py")
try:
    reimport.reimport(*reimport.modified())
except StandardError, e:
    print type(e).__name__, e

print [x for x in dir(failpkg) if not x.startswith("_")]
try:
    print failpkg.xyzfail
except StandardError, e:
    print "%s: %s" % (type(e).__name__, e)

time.sleep(1)
shutil.copy("tests/failpkg/child_alt.py", "tests/failpkg/child.py")
reimport.reimport(*reimport.modified())

print [x for x in dir(failpkg) if not x.startswith("_")]
try:
    print failpkg.xyzfail
except StandardError, e:
    print "%s: %s" % (type(e).__name__, e)
