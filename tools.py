from ctypes import *

class TypeSwitchUnion(Union):
	_fields_ = [
		('double', c_double),
		('int', c_int),
		('ushort', c_char * 2),
		('uchar', c_char * 8)
	]