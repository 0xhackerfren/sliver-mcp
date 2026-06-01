import py_compile
import sys

try:
    py_compile.compile("server.py", doraise=True)
    print("SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
    sys.exit(1)

try:
    import server
    print("IMPORT OK")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)
