from ctypes import *


class TypeSwitchUnion(Union):
	_fields_ = [
		('double', c_double),
		('int', c_int),
		('char', c_char * 8)
	]