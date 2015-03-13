import sys
import shutil
import time
import reimport

def trigger():
    pass

time.sleep(0.4)
shutil.copy("tests/callbacka.py", "tests/callback.py")

import callback
sys.setprofile(callback.TraceCallback)

print callback.TraceCallback.__doc__
trigger()

time.sleep(0.4)
shutil.copy("tests/callbackb.py", "tests/callback.py")
reimport.reimport(callback)

print callback.TraceCallback.__doc__
trigger()


