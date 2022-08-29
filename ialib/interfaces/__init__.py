import ialib.interfaces.plx_gpib_ethernet

try:
    import ialib.interfaces.ug01_lib
except OSError:
    # Incompatible DLL (64bit Windows only)
    pass
