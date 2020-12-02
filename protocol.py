import serialport
from ctypes import Union, c_ubyte, c_double

class TypeSwitchUnion(Union):
	_fields_ = [
		('double', c_double),
		('ushort', c_ubyte * 2),
		('uchar', c_ubyte * 8)
	]

class HeartStruct:
	"""心跳"""

	def __init__(self):
		self.start = None
		self.type = None
		self.id = None
		self.len = None
		self.seqnum = None
		self.ack = None
		self.reserved = None
		self.end = None


class SendHeadStruct:
	"""上传头部"""

	def __init__(self):
		self.start = "$"
		self.type = None  # 数据类型
		self.id = None  # 挖掘机编号
		self.len = None  # 数据包中长度
		self.seqnum = None  # 包序列号
		self.reserved = 0  # 预留
		self.sumcheck = 0
		self.end = None


class SendBodyStruct:
	"""上传数据,每帧40B"""

	def __init__(self):
		self.start = '$'
		self.type = None  # 数据类型
		self.id = None  # 挖掘机编号
		self.len = None  # 数据包中长度
		self.seqnum = None  # 包序列号
		self.x = [None] * 8  # 8B
		self.y = [None] * 8  # 8B
		self.h = [None] * 8  # 8B
		self.reserved = [0] * 9  # 9B
		self.sumcheck = 0
		self.end = '0a'


class Task:
	"""接收任务消息"""

	def __init__(self):
		self.start = 36  # ‘$’ = 36(十进制) = 24(16进制)
		self.type = 0  # 数据类型
		self.id = 0  # 挖掘机编号
		self.len = 0  # 数据包中长度
		self.seqnum = 0  # 包序列号
		self.baseHeight = []  # 2B
		self.sectionNum = 0
		self.section = []  # 不定长
		self.sumcheck = 0
		self.end = '0a'


###################################### Rec ######################################
task = Task()
com_4g = serialport.SerialPortCommunication(serialport._4G_COM, 115200, 5)
task_buffer = com_4g.read_line()	# type = bytes
print(task_buffer)

if task.start == task_buffer[0]:  # 判断头是否正确
	task.type = task_buffer[1]
	task.id = task_buffer[2]
	task.len = task_buffer[3]
	task.seqnum = task_buffer[4]
	task.baseHeight = task_buffer[5:7]  	# baseHeight 2B
	task.sectionNum = task_buffer[7]
	task.section = task_buffer[8:-2]  		# section为索引: 8--倒数第2位（不包含倒数第二位）
	task.sumcheck = sum(task_buffer[0:-2])  # 计算校验位
	task.sumcheck = task.sumcheck & 0xff	# 取sumcheck的最低字节
	if task.sumcheck != task_buffer[-2]:  	# 计算出的校验位不等于接受到的校验位
		print("\r\ncheck error!!!\r\n")
	else:
		task.sumcheck = task_buffer[-2]
	task.end = task_buffer[-1]
else:
	print("\r\nhead error!!!\r\n")

# no = []
# x1 = []
# y1 = []
# h1 = []
# w1 = []
# x2 = []
# y2 = []
# h2 = []
# w2 = []
i = 0
# for i in range(len(task.section)):
while(task.sectionNum):
	no = task.section[(i+0):(i+2)]
	x1 = task.section[(i+2):(i+10)]
	y1 = task.section[(i+10):(i+18)]
	h1 = task.section[(i+18):(i+26)]
	w1 = task.section[(i+26):(i+28)]
	x2 = task.section[(i+28):(i+36)]
	y2 = task.section[(i+36):(i+44)]
	h2 = task.section[(i+44):(i+52)]
	w2 = task.section[(i+52):(i+54)]
	task.sectionNum  = task.sectionNum -1

# 联合体转换数据类型
x1_union = TypeSwitchUnion()
x1_union.uchar = x1
x1_d = x1_union.double

y1_union = TypeSwitchUnion()
y1_union.uchar = y1
y1_d = y1_union.double

h1_union = TypeSwitchUnion()
h1_union.uchar = h1
h1_d = h1_union.double

w1_union = TypeSwitchUnion()
w1_union.uchar = w1
w1_s = w1_union.ushort

x2_union = TypeSwitchUnion()
x2_union.uchar = x2
x2_d = x2_union.double

y2_union = TypeSwitchUnion()
y2_union.uchar = y2
y2_d = y2_union.double

h2_union = TypeSwitchUnion()
h2_union.uchar = h2
h2_d = h2_union.double

w2_union = TypeSwitchUnion()
w2_union.uchar = w2
w2_s = w2_union.ushort


sX = 550/2
sY = 50
eX = 480/2
eY = 400
Interval = 120
