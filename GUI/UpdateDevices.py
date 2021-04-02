from PyQt5.QtCore import QSettings, QDir, pyqtSignal
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QPushButton, QGroupBox, QCheckBox, \
        QHBoxLayout, QFileDialog, QLabel, QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox
from PyQt5.QtGui import QIcon

from GUI import SpinBox, HLayout, VLayout

import csv
import random
import string

class UpdateDevicesDialog(QDialog):
    def __init__(self, parent, *args, **kwargs):
        super().__init__()
        
        self.mqtt = parent.mqtt
        self.env = parent.env
                
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)
        self.setWindowIcon(QIcon("icons/compile.png"))
        self.setWindowTitle("Update Devices")

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.settings.beginGroup("BatchCommands")

        gbCommands = QGroupBox("Commands")
        hfl = QFormLayout()
        cols = ["Command", "Parameters"]
        self.tw = QTableWidget(0,2)
        self.tw.setHorizontalHeaderLabels(cols)
        self.tw.verticalHeader().hide()

        for c in range(2):
            self.tw.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)

        for k in self.settings.childKeys():
            row = self.tw.rowCount()
            self.tw.insertRow(row)
            self.tw.setItem(row, 0, QTableWidgetItem(k))
            self.tw.setItem(row, 1, QTableWidgetItem(self.settings.value(k)))

        hfl.addRow(self.tw)
        
        self.btnAdd = QPushButton("Add")
        self.btnDel = QPushButton("Delete")
        self.btnLayout =  QHBoxLayout()
        self.btnLayout.addWidget(self.btnAdd)
        self.btnLayout.addWidget(self.btnDel)
        hfl.addRow(self.btnLayout)
        gbCommands.setLayout(hfl)
        self.settings.endGroup()
        
        gbDevices = QGroupBox("Devices")
        hfl = QFormLayout()
        self.BatchDevicesFile = QLabel()
        self.BatchDevicesFile.setText(self.settings.value("BatchDevicesFile", ""))
        self.btnDevicesFile = QPushButton("Select File")
        self.devicesFilelayout = QHBoxLayout()
        self.devicesFilelayout.addWidget(self.BatchDevicesFile)
        self.devicesFilelayout.addWidget(self.btnDevicesFile)
        
        hfl.addRow("Devices File: ", self.devicesFilelayout)
        gbDevices.setLayout(hfl)
        
        self.idx = None
        self.tw.clicked.connect(self.select)
        self.btnAdd.clicked.connect(self.add)
        self.btnDel.clicked.connect(self.delete)
        self.btnDevicesFile.clicked.connect(self.devicesFileSelect)
        
        hl2Btn = HLayout()
        btnSave = QPushButton("Save")
        btnExecute = QPushButton("Execute")
        btnCancel = QPushButton("Cancel")
        hl2Btn.addWidgets([btnSave, btnExecute, btnCancel])

        vl = VLayout()
        vl.addWidgets([gbCommands, gbDevices])
        vl.addLayout(hl2Btn)
        
        self.setLayout(vl)
        
        btnSave.clicked.connect(self.accept)
        btnExecute.clicked.connect(self.execute)
        btnCancel.clicked.connect(self.reject)

    def select(self, idx):
        self.idx = idx

    def add(self):
        self.tw.insertRow(self.tw.rowCount())

    def delete(self):
        if self.idx:
            key = self.tw.item(self.idx.row(), 0).text()
            self.settings.remove(key)
            self.tw.removeRow(self.idx.row())
            
    def devicesFileSelect(self):
        fname = QFileDialog.getOpenFileName(self, 'Select Devices File',
        "{}/TDM/Devices/".format(QDir.homePath()),
        "Devices Files (*.csv)")

        if fname[0] != "":
            self.BatchDevicesFile.setText(fname[0])

    def execute(self):
        # Load Device list from the provided CSV file
        # Batch send command messages based on the devices provide in the CSV file 
        with open(self.BatchDevicesFile.text(), newline='') as csvfile:
            devices = csv.reader(csvfile, delimiter=',', quotechar='|')
            grossDevices = netDevices = 0            
            
            # Itterate thru online devices and send batch commmands
            for device in devices:
                grossDevices = grossDevices + 1
                d = self.env.find_device(device[0])
                if d.p['LWT'] == 'Online':
                    netDevices = netDevices + 1
                    for r in range(self.tw.rowCount()):
                        topic = "cmnd/" + d.p['Topic'] + "/" + self.tw.item(r, 0).text() 
                        parameter = self.tw.item(r, 1).text()
                        
                        self.mqtt.publish(topic, parameter)
        
        QMessageBox.information(self, "Batch - Update Devices", str(netDevices) + "/" + str(grossDevices) + " Device(s) were successfully updated with Commands provided")
        
        self.done(QDialog.Accepted)
        
    def accept(self):
        # Save settings to tdm.cfg
        self.settings.beginGroup("BatchCommands")
        for r in range(self.tw.rowCount()):
            key = self.tw.item(r, 0).text()
            val = self.tw.item(r, 1).text()
            self.settings.setValue(key, val)
        self.settings.endGroup()
        
        self.settings.setValue("BatchDevicesFile", self.BatchDevicesFile.text())
        self.settings.sync()      
        QMessageBox.information(self, "Batch - Update Devices", "Batch settings were saved successfully")      
 
        self.done(QDialog.Accepted)