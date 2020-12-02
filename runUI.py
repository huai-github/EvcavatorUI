import sys
import UI
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import QtCore
from time import sleep
from my_thread import MyThread

h = 480
w = 550


class ThreadFunc():
	def __init__(self):
		self.startX = w//2
		self.startY = 50
		self.endX = w//2
		self.endY = 400
		self.Interval = 120

		self.nowX = 0
		self.nowY = 0
		self.deep = 0

	def __call__(self):
		while True:
			self.nowX = np.random.randint(0, h, 1)[0]
			self.nowY = np.random.randint(0, w, 1)[0]
			self.deep = np.random.randint(-10, 10, 1)[0]
			sleep(1)

	def get_msg_xy(self):
		return (self.startX, self.startY, self.endX, self.endY, self.Interval, self.nowX, self.nowY)

	def get_msg_deep(self):
		return self.deep

	def get_msg_startXY(self):
		return (self.startX, self.startY)

	def get_msg_endXY(self):
		return (self.endX, self.endY)

	def get_msg_nowXY(self):
		return (self.nowX, self.nowY)


class MyWindows(QWidget, UI.Ui_Form):
	def __init__(self):
		super().__init__()
		# 注意：里面的控件对象也成为窗口对象的属性了
		self.setupUi(self)

		self.imgLine = np.zeros((h, w, 3), np.uint8)
		self.imgBar = np.zeros((h, w, 3), np.uint8)

		self.figure = plt.figure()  # 可选参数,facecolor为背景颜色
		self.canvas = FigureCanvas(self.figure)

		self.__timer = QtCore.QTimer()  # 定时器用于定时刷新
		self.set_slot()

		self.__thread = ThreadFunc()  # 开启线程(同时将这个线程类作为一个属性)
		MyThread(self.__thread, (), name='ThreadFunc', daemon=True).start()
		self.__timer.start(25)  # 25 ms 刷新一次

		self.DeepList = []
		self.NumList = []

	def set_slot(self):
		self.__timer.timeout.connect(self.update)

	def leftWindow(self, img, startX, startY, endX, endY, Interval, nowX, nowY):
		img[...] = 255
		cv2.line(img, (startX, startY), (endX, endY), (0, 255, 0), 1)
		cv2.line(img, (startX + Interval, startY), (endX + Interval, endY), (0, 0, 255), 3)
		cv2.line(img, (endX - Interval, startY), (endX - Interval, endY), (0, 0, 255), 3)
		cv2.circle(img, (nowX, nowY), 6, (255, 0, 0), -1)
		BorderReminderLedXY = (530, 460)   # 边界指示灯位置 界内绿色
		BorderReminderTextXY = (230, 470)
		cv2.circle(img, BorderReminderLedXY, 12, (0, 255, 0), -1)
		self.BorderReminder.setText("   ")
		# 如果超出边界，BorderReminder红色,并提示汉字信息
		if nowX > (startX + Interval) or nowX < (startX - Interval):
			cv2.circle(img, BorderReminderLedXY, 12, (0, 0, 255), -1)	 # 边界报警指示灯
			self.BorderReminder.setText("！！即将超出边界！！")

		cv2.putText(img, "BorderReminder", BorderReminderTextXY, cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 2)
		QtImgLine = QImage(cv2.cvtColor(img, cv2.COLOR_BGR2RGB).data,
						   img.shape[1],
						   img.shape[0],
						   img.shape[1] * 3,  # 每行的字节数, 彩图*3
						   QImage.Format_RGB888)

		pixmapL = QPixmap(QtImgLine)
		self.leftLabel.setPixmap(pixmapL)

	def rightWindow(self, img, deep):
		img[::] = 255

		if len(self.NumList) >= 15:
			self.DeepList.pop(0)
			self.NumList.pop(0)

		self.DeepList.append(np.random.randint(1, 100, 1)[0])
		self.NumList.append(1)

		# 将self.DeepList中的数据转化为int类型
		self.DeepList = list(map(int, self.DeepList))

		# 将x,y轴转化为矩阵式
		self.x = np.arange(len(self.NumList)) + 1
		self.y = np.array(self.DeepList)

		# print(self.DeepList)
		colors = ["g" if i > 0 else "r" for i in self.DeepList]
		plt.clf()
		plt.bar(range(len(self.NumList)), self.DeepList, tick_label=self.NumList, color=colors, width=0.5)

		# 在柱体上显示数据
		for a, b in zip(self.x, self.y):
			plt.text(a - 1, b, '%d' % b, ha='center', va='bottom')

		# 画图
		self.canvas.draw()

		img = np.array(self.canvas.renderer.buffer_rgba())

		QtImgBar = QImage(img.data,
						  img.shape[1],
						  img.shape[0],
						  img.shape[1] * 4,
						  QImage.Format_RGBA8888)
		pixmapR = QPixmap(QtImgBar)

		self.rightLabel.setPixmap(pixmapR)

	def showStartXY(self, startX, startY):
		self.startXY.setText("(%d, %d)" % (startX, startY))

	def showEndXY(self, endX, endY):
		self.endXY.setText("(%d, %d)" % (endX, endY))

	def showNowXY(self, nowX, nowY):
		self.nowXY.setText("(%d, %d)" % (nowX, nowY))

	def update(self):
		self.leftWindow(self.imgLine, *self.__thread.get_msg_xy())
		self.rightWindow(self.imgBar, self.__thread.get_msg_deep())
		self.showStartXY(*self.__thread.get_msg_startXY())
		self.showEndXY(*self.__thread.get_msg_endXY())
		self.showNowXY(*self.__thread.get_msg_nowXY())


if __name__ == "__main__":
	app = QApplication(sys.argv)
	mainWindow = MyWindows()
	mainWindow.show()
	sys.exit(app.exec_())
