import shutil
import time

def test_package():
    
    #import reimport


    shutil.copy("tests/pkg/child_orig.py", "tests/pkg/child.py")

    import pkg

    print(pkg.child)
    pkg.child()



    time.sleep(1)
    shutil.copy("tests/pkg/child_alt.py", "tests/pkg/child.py")
    #os.system("rm tests/*.pyc")


    import reimport

    changed = reimport.modified()
    print("Changed modules:", changed)
    try:
        reimport.reimport(*changed)
    except Exception as e:
        print("ROLLBACK BECAUSE OF:", e)
        import traceback
        traceback.print_exc()
        #raise


    print(pkg.child)
    pkg.child()

