def released(fd):
    import fcntl
    pressed = bytearray(96)  # EVIOCGKEY getter; discard the bitmap, export only a Boolean.
    fcntl.ioctl(fd, 0x80604518, pressed, True)
    return not any(pressed)
