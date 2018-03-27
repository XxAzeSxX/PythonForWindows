"""utils fonctions non windows-related"""
import sys
import ctypes
import _ctypes
from windows.generated_def import Flag, LPCSTR, LPWSTR, INFINITE

from windows.dbgprint import dbgprint
from windows import winproxy


def buffer(size): # Test
    buf = ctypes.create_string_buffer(size)
    buf.size = size
    buf.address = ctypes.addressof(buf)

    class ImprovedCtypesBufferImpl(ctypes.Array):
        _length_ = size
        _type_ = ctypes.c_char
        def lol(self):
            return "lol"

        def as_string(self):
            return ctypes.cast(self, LPCSTR).value

        def as_wstring(self):
            return ctypes.cast(self, LPWSTR).value

    return ImprovedCtypesBufferImpl()


def wbuffer(size): # Test
    buf = ctypes.create_string_buffer(size)
    buf.size = size
    buf.address = ctypes.addressof(buf)

    class ImprovedCtypesBufferImpl(ctypes.Array):
        _length_ = size
        _type_ = ctypes.c_wchar
        def lol(self):
            return "lol"

        def as_string(self):
            return ctypes.cast(self, LPCSTR).value

        def as_wstring(self):
            return ctypes.cast(self, LPWSTR).value

    return ImprovedCtypesBufferImpl()


def fixedpropety(f):
    cache_name = "_" + f.__name__

    def prop(self):
        try:
            return getattr(self, cache_name)
        except AttributeError:
            setattr(self, cache_name, f(self))
            return getattr(self, cache_name)
    return property(prop, doc=f.__doc__)


# type replacement based on name
def transform_ctypes_fields(struct, replacement):
    return [(name, replacement.get(name, type)) for name, type in struct._fields_]


def print_ctypes_struct(struct, name="", ident=0, hexa=False):
    if isinstance(struct, _ctypes._Pointer):
        if ctypes.cast(struct, ctypes.c_void_p).value is None:
            print("{0} -> NULL".format(name))
            return
        return print_ctypes_struct(struct[0], name + "<deref>", hexa=hexa)

    if not hasattr(struct, "_fields_"):
        value = struct
        if hasattr(struct, "value"):
            value = struct.value

        if isinstance(value, basestring):
            value = repr(value)
        if hexa and not isinstance(value, Flag):
            try:
                print("{0} -> {1}".format(name, hex(value)))
                return
            except TypeError:
                pass
        print("{0} -> {1}".format(name, value))
        return

    for fname, ftype in struct._fields_:
        try:
            value = getattr(struct, fname)
        except Exception as e:
            print("Error while printing <{0}> : {1}".format(fname, e))
            continue
        print_ctypes_struct(value, "{0}.{1}".format(name, fname), hexa=hexa)


def sprint(struct, name="struct", hexa=True):
    """Print recursively the content of a :mod:`ctypes` structure"""
    return print_ctypes_struct(struct, name=name, hexa=hexa)


class AutoHandle(object):
    """An abstract class that allow easy handle creation/destruction/wait"""
     # Big bypass to prevent missing reference at programm exit..
    _close_function = ctypes.WinDLL("kernel32").CloseHandle
    def _get_handle(self):
        raise NotImplementedError("{0} is abstract".format(type(self).__name__))

    @property
    def handle(self):
        """An handle on the object

        :type: HANDLE

           .. note::
                The handle is automaticaly closed when the object is destroyed
        """
        if hasattr(self, "_handle"):
            return self._handle
        self._handle = self._get_handle()
        dbgprint("Open handle {0} for {1}".format(hex(self._handle), self), "HANDLE")
        return self._handle

    def wait(self, timeout=INFINITE):
        """Wait for the object"""
        return winproxy.WaitForSingleObject(self.handle, timeout)

    def __del__(self):
        # sys.path is not None -> check if python shutdown
        if hasattr(sys, "path") and sys.path is not None and hasattr(self, "_handle") and self._handle:
            # Prevent some bug where dbgprint might be None when __del__ is called in a closing process
            dbgprint("Closing Handle {0} for {1}".format(hex(self._handle), self), "HANDLE") if dbgprint is not None else None
            self._close_function(self._handle)