

def TraceCallback(frame, event, arg):
    """CALLBACK B"""
    if event == "call" and frame.f_code.co_name == "trigger":
        print "TRACE FROM CALLBACK B", __name__, True, False, None



