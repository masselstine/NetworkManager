#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
# vim: ft=python ts=4 sts=4 sw=4 et ai

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2018 Red Hat, Inc.

import sys

###############################################################################
# nm_pyutil.py contains helper functions used by some examples. The helper functions
# should be simple and independent, so that the user can extract them easily
# when modifying the example to his needs.
###############################################################################

def _sys_clock_gettime_ns_lazy():
    import ctypes

    class timespec(ctypes.Structure):
        _fields_ = [
                ('tv_sec', ctypes.c_long),
                ('tv_nsec', ctypes.c_long)
        ]

    librt = ctypes.CDLL('librt.so.1', use_errno=True)
    clock_gettime = librt.clock_gettime
    clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

    t = timespec()
    def f(clock_id):
        if clock_gettime(clock_id, ctypes.pointer(t)) != 0:
            import os
            errno_ = ctypes.get_errno()
            raise OSError(errno_, os.strerror(errno_))
        return (t.tv_sec * 1000000000) + t.tv_nsec
    return f

_sys_clock_gettime_ns = None

# call POSIX clock_gettime() and return it as integer (in nanoseconds)
def sys_clock_gettime_ns(clock_id):
    global _sys_clock_gettime_ns
    if _sys_clock_gettime_ns is None:
        _sys_clock_gettime_ns = _sys_clock_gettime_ns_lazy()
    return _sys_clock_gettime_ns(clock_id)

def nm_boot_time_ns():
    # NetworkManager exposes some timestamps as CLOCK_BOOTTIME.
    # Try that first (number 7).
    try:
        return sys_clock_gettime_ns(7)
    except OSError as e:
        # On systems, where this is not available, fallback to
        # CLOCK_MONOTONIC (numeric 1).
        # That is what NetworkManager does as well.
        import errno
        if e.errno == errno.EINVAL:
            return sys_clock_gettime_ns(1)
        raise
def nm_boot_time_us():
    return nm_boot_time_ns() / 1000
def nm_boot_time_ms():
    return nm_boot_time_ns() / 1000000
def nm_boot_time_s():
    return nm_boot_time_ns() / 1000000000

###############################################################################

class Util:

    PY3 = (sys.version_info[0] == 3)

    STRING_TYPE = (str if PY3 else basestring)

    @classmethod
    def create_uuid(cls):
        n = getattr(cls, '_uuid', None)
        if n is None:
            import uuid
            n = uuid
            cls._uuid = n
        return str(n.uuid4())

    @classmethod
    def NM(cls):
        n = getattr(cls, '_NM', None)
        if n is None:
            import gi
            gi.require_version('NM', '1.0')
            from gi.repository import NM, GLib, Gio, GObject
            cls._NM = NM
            cls._GLib = GLib
            cls._Gio = Gio
            cls._GObject = GObject
            n = NM
        return n

    @classmethod
    def GLib(cls):
        cls.NM()
        return cls._GLib

    @classmethod
    def Gio(cls):
        cls.NM()
        return cls._Gio

    @classmethod
    def GObject(cls):
        cls.NM()
        return cls._GObject

    @classmethod
    def GMainLoop(cls, mainloop = None):
        if mainloop is not None:
            return mainloop
        gmainloop = getattr(cls, '_GMainLoop', None)
        if gmainloop is None:
            gmainloop = cls.GLib().MainLoop()
            cls._GMainLoop = gmainloop
        return gmainloop

    @classmethod
    def GMainLoop_run(cls, mainloop = None, timeout = None):
        if timeout is None:
            cls.GMainLoop(mainloop).run()
            return True

        GLib = cls.GLib()
        loop = cls.GMainLoop(mainloop)
        result = []
        def _timeout_cb(unused):
            result.append(1)
            loop.quit()
            return False
        timeout_id = GLib.timeout_add(int(timeout * 1000), _timeout_cb, None)
        loop.run()
        if result:
            return False
        GLib.source_remove(timeout_id)
        return True

    @classmethod
    def GMainLoop_iterate(cls, mainloop = None, may_block = False):
        return cls.GMainLoop(mainloop).get_context().iteration(may_block)

###############################################################################
