import sys
import UI
import cv2
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import QtCore
from time import sleep
from my_thread import MyThread
import rectask
import gps


class UIFreshThread:
	def __init__(self):
		rectask_threadLock.acquire()
		# self.startX = w // 2  # from could
		# self.startY = 50
		# self.endX = w // 2
		# self.endY = 400
		# self.Interval = 120
		self.startX = int(rectask.x1_d)	 # from could
		self.startY = int(rectask.y1_d)
		self.endX = int(rectask.x2_d)
		self.endY = int(rectask.y2_d)
		self.Interval = 120
		rectask_threadLock.release()

		self.nowX = 0  # from gps
		self.nowY = 0
		self.deep = 0

	def __call__(self):
		# while True:
		gps_threadLock.acquire()
		self.nowX = int(gps.x - 4076000)  # from gps
		self.nowY = int(gps.y - 515000)
		self.deep = int(gps.deep)
		# sleep(1)
		gps_threadLock.release()

	def get_msg_xy(self):
		return self.startX, self.startY, self.endX, self.endY, self.Interval, self.nowX, self.nowY

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

		self.imgLine = np.zeros((h, w, 3), np.uint8)  # 画布
		self.imgBar = np.zeros((h, w, 3), np.uint8)
		self.figure = plt.figure()  # 可选参数,facecolor为背景颜色
		self.canvas = FigureCanvas(self.figure)
		self.__timer = QtCore.QTimer()  # 定时器用于定时刷新
		self.set_slot()

		self.__thread = UIFreshThread()  # 开启线程(同时将这个线程类作为一个属性)
		MyThread(self.__thread, (), name='UIFreshThread', daemon=True).start()
		self.__timer.start(1000)  # s 刷新一次

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
		BorderReminderLedXY = (530, 460)  # 边界指示灯位置 界内绿色
		BorderReminderTextXY = (230, 470)
		cv2.circle(img, BorderReminderLedXY, 12, (0, 255, 0), -1)
		self.BorderReminder.setText("   ")
		# 如果超出边界，BorderReminder红色,并提示汉字信息
		if nowX > (startX + Interval) or nowX < (startX - Interval):
			cv2.circle(img, BorderReminderLedXY, 12, (0, 0, 255), -1)  # 边界报警指示灯
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
		img[::] = 255  # 设置画布颜色

		if len(self.NumList) >= 15:
			self.DeepList.pop(0)
			self.NumList.pop(0)

		self.DeepList.append(deep)
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


h = 480  # 画布大小
w = 550
gps_threadLock = threading.Lock()
rectask_threadLock = threading.Lock()
if __name__ == "__main__":
	gps_thread = threading.Thread(target=gps.gps_thread_fun)
	rectask_thread = threading.Thread(target=rectask.rectask_thread_fun)

	gps_thread.setDaemon(True)  # 守护线程,当主进程结束后,子线程也会随之结束
	rectask_thread.setDaemon(True)

	gps_thread.start()			# 启动线程
	rectask_thread.start()

	gps_thread.join()			# 设置主线程等待子线程结束
	rectask_thread.join()

	app = QApplication(sys.argv)
	mainWindow = MyWindows()
	mainWindow.show()
	sys.exit(app.exec_())
