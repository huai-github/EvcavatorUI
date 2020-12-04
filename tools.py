from ctypes import *


class TypeSwitchUnion(Union):
	_fields_ = [
		('double', c_double),
		('int', c_int),
		('short', c_short),
		('char', c_char * 8)
	]