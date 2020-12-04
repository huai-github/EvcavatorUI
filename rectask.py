import serialport
from tools import *


class HeartStruct:
	"""心跳"""

	def __init__(self):
		self.start = 36
		self.type = 0
		self.id = 0
		self.len = 0
		self.seqnum = 0
		self.ack = 0
		self.reserved = 0
		self.end = 0


class SendHeadStruct:
	"""上传头部"""

	def __init__(self):
		self.start = 36
		self.type = None  # 数据类型
		self.id = None  # 挖掘机编号
		self.len = None  # 数据包中长度
		self.seqnum = None  # 包序列号
		self.msg = 0  		# 0 接收任务成功，1 接收任务失败
		self.sumcheck = 0
		self.end = None

class SendBodyStruct:
	"""上传数据,每帧40B"""

	def __init__(self):
		self.start = 36
		self.type = 0  # 数据类型
		self.id = 0  # 挖掘机编号
		self.len = 0  # 数据包中长度
		self.seqnum = 0  # 包序列号
		self.x = [0] * 8  # 8B
		self.y = [0] * 8  # 8B
		self.h = [0] * 8  # 8B
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
		
	def task_msg_analysis(self, recbuff):
		if self.start == recbuff[0]:  # 判断头是否正确
			self.type = recbuff[1]
			self.id = recbuff[2]
			self.len = recbuff[3]
			self.seqnum = recbuff[4]
			self.baseHeight = recbuff[5:7]  # baseHeight 2B
			self.sectionNum = recbuff[7]
			self.section = recbuff[8:-2]  	# section为索引: 8--倒数第2位（不包含倒数第二位）
			self.sumcheck = sum(recbuff[0:-2])  # 计算校验位
			self.sumcheck = self.sumcheck & 0xff  # 取sumcheck的最低字节
			if self.sumcheck != recbuff[-2]:  # 计算出的校验位不等于接受到的校验位
				print("\r\ncheck error!!!\r\n")
			else:
				self.sumcheck = recbuff[-2]
			self.end = recbuff[-1]
		else:
			print("\r\nhead error!!!\r\n")
			
	def section_analysis(self):
		# while (task.sectionNum):
		for i in range(len(task.section)):
			no = self.section[(i + 0):(i + 2)]
			x1 = self.section[(i + 2):(i + 10)]
			y1 = self.section[(i + 10):(i + 18)]
			h1 = self.section[(i + 18):(i + 26)]
			w1 = self.section[(i + 26):(i + 28)]
			x2 = self.section[(i + 28):(i + 36)]
			y2 = self.section[(i + 36):(i + 44)]
			h2 = self.section[(i + 44):(i + 52)]
			w2 = self.section[(i + 52):(i + 54)]
			# self.sectionNum = self.sectionNum - 1
			return no, x1, y1, h1, w1, x2, y2, h2, w2


_4G_COM = "com21"

if __name__ == "__main__":
	task = Task()
	com_4g = serialport.SerialPortCommunication(_4G_COM, 115200, 5)
	task_buffer = com_4g.read_line()  # type = bytes
	com_4g.close_com()
	# print(task_buffer)
	task.task_msg_analysis(task_buffer)
	section_one = task.section_analysis()  # 返回一个直线段
	# print(section_one)  # tuple

	# 联合体转换数据类型
	x1_union = TypeSwitchUnion()
	x1_union.char = section_one[1]
	x1_d = x1_union.int

	y1_union = TypeSwitchUnion()
	y1_union.char = section_one[2]
	y1_d = y1_union.int

	h1_union = TypeSwitchUnion()
	h1_union.char = section_one[3]
	h1_d = h1_union.int

	w1_union = TypeSwitchUnion()
	w1_union.char = section_one[4]
	w1_s = w1_union.short
	# print(w1_s)

	x2_union = TypeSwitchUnion()
	x2_union.char = section_one[5]
	x2_d = x2_union.int

	y2_union = TypeSwitchUnion()
	y2_union.char = section_one[6]
	y2_d = y2_union.int

	h2_union = TypeSwitchUnion()
	h2_union.char = section_one[7]
	h2_d = h2_union.int

	w2_union = TypeSwitchUnion()
	w2_union.char = section_one[8]
	w2_s = w2_union.short


