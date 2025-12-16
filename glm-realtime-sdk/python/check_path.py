# check_paths.py
import sys,os
print("Python 路径:")
for path in sys.path:
    print(f"  {path}")

print(f"\n当前工作目录: {os.getcwd()}")