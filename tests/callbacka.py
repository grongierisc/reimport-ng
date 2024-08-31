

def TraceCallback(frame, event, arg):
    """CALLBACK A"""
    if event == "call" and frame.f_code.co_name == "trigger":
        print("TRACE FROM CALLBACK A", __name__, True, False, None)

