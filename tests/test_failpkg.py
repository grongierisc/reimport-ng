import shutil

import time

import reimport

def test_package_fail():
    shutil.copy("tests/failpkg/child_orig.py", "tests/failpkg/child.py")
    import failpkg

    print([x for x in dir(failpkg) if not x.startswith("_")])

    time.sleep(1)
    shutil.copy("tests/failpkg/child_fail.py", "tests/failpkg/child.py")
    try:
        reimport.reimport(*reimport.modified())
    except Exception as e:
        print(type(e).__name__, e)

    print([x for x in dir(failpkg) if not x.startswith("_")])
    try:
        print(failpkg.xyzfail)
    except Exception as e:
        print("%s: %s" % (type(e).__name__, e))

    time.sleep(1)
    shutil.copy("tests/failpkg/child_alt.py", "tests/failpkg/child.py")
    reimport.reimport(*reimport.modified())

    print([x for x in dir(failpkg) if not x.startswith("_")])
    try:
        print(failpkg.xyzfail)
    except Exception as e:
        print("%s: %s" % (type(e).__name__, e))
