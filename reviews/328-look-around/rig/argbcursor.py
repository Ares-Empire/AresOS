#!/usr/bin/python3
# Package 328 rig: makes the cursor GLFW 3.5 hides with on X11 (a 16x16 Xcursor ARGB image, every pixel transparent)
# on the rig's X server, prints its XID and keeps it alive until stdin closes. xmimic.py's ARGB_CURSOR uses it.
import ctypes
import os
import sys

env = dict(line.strip().split('=', 1) for line in open(os.path.join(sys.argv[1], 'env')) if '=' in line)
assert env['DISPLAY'] != ':0'
x11 = ctypes.CDLL('libX11.so.6')
xcursor = ctypes.CDLL('libXcursor.so.1')
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
xcursor.XcursorImageCreate.restype = ctypes.c_void_p
xcursor.XcursorImageCreate.argtypes = [ctypes.c_int, ctypes.c_int]
xcursor.XcursorImageLoadCursor.restype = ctypes.c_ulong
xcursor.XcursorImageLoadCursor.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
x11.XFlush.argtypes = [ctypes.c_void_p]


class XcursorImage(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint), ('size', ctypes.c_uint), ('width', ctypes.c_uint),
                ('height', ctypes.c_uint), ('xhot', ctypes.c_uint), ('yhot', ctypes.c_uint),
                ('delay', ctypes.c_uint), ('pixels', ctypes.POINTER(ctypes.c_uint32))]


display = x11.XOpenDisplay(env['DISPLAY'].encode())
image = xcursor.XcursorImageCreate(16, 16)
pixels = XcursorImage.from_address(image).pixels
for i in range(16 * 16):
    pixels[i] = 0
cursor = xcursor.XcursorImageLoadCursor(display, image)
x11.XFlush(display)
print(cursor, flush=True)
sys.stdin.read()
