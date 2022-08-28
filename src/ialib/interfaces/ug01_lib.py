import ctypes
import os

# Cheat and use a windows only solution, this lib only works on windows
UG01lib = ctypes.CDLL(
    f"{os.path.dirname(os.path.abspath(__file__))}\\UG01\\UG01API\\LQUG01_c.dll"
)

UG01lib.Gwrite.restype = ctypes.c_int
UG01lib.Gread.restype = ctypes.c_char_p
UG01lib.Gquery.restype = ctypes.c_char_p
UG01lib.Gfind.restype = ctypes.c_int

UG01lib.Gread.argtypes = [ctypes.c_int]
UG01lib.Gwrite.argtypes = [ctypes.c_int, ctypes.c_char_p]
UG01lib.Gquery.argtypes = [ctypes.c_int, ctypes.c_char_p]
