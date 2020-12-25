# -*- coding: utf-8 -*-
# 
from aqt.qt import *
from anki.utils import isMac, isWin, isLin
from os.path import dirname, join
from aqt.utils import showInfo
from .miutils import miInfo, miAsk
from . import Pyperclip
from datetime import date

class VacationPicker(QWidget):

    def __init__(self, mw, path, rescheduler):
        super(VacationPicker, self).__init__()
        self.mw = mw
        self.path = path
        self.rescheduler = rescheduler
        self.vacationScheduler = False
        self.addVacationButton = QPushButton('Schedule a New Vacation')
        self.setWindowIcon(QIcon(join(self.path, 'icons', 'migaku.png')))
        self.setWindowTitle("Migaku Vacation Browser")
        self.vacations = self.getVacationsTable()
        self.addVacationButton.clicked.connect(self.addVacation)
        self.resize(400,400)
        self.setupLayout()
        
    def deleteOldVacations(self):
        newConfig = self.getConfig()
        vacations = newConfig['vacations']
        toDelete = []
        for idx,v in enumerate(vacations):
            if self.mw.pm.name == v['profile']:
                year, month, day = v['start'].split(',')
                today = date.today()
                today = QDate(today.year, today.month, today.day)   
                start = QDate(int(year), int(month), int(day))
                end = start.addDays(v['length'])
                dif = today.daysTo(end)
                if dif < 0:
                    toDelete.append(idx)
        if len(toDelete) > 0:
            for idx in reversed(toDelete):
                del vacations[idx]
            miInfo('<span>Welcome back from your time off! Good luck on your studies today!&nbsp;&nbsp;&nbsp;&nbsp;</span>')
            self.mw.addonManager.writeConfig(__name__, newConfig)

    def setupLayout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.vacations)
        self.layout.addWidget(self.addVacationButton)
        self.setLayout(self.layout)


    def start(self):
        self.loadVacationsTable()
        self.show()

    def getVacationsTable(self):
        macLin = False
        if isMac  or isLin:
            macLin = True
        vacationsTable = QTableWidget()
        vacationsTable.setColumnCount(4)
        tableHeader = vacationsTable.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(2, QHeaderView.Fixed)
        tableHeader.setSectionResizeMode(3, QHeaderView.Fixed)
        vacationsTable.setRowCount(0)
        vacationsTable.setSortingEnabled(False)
        vacationsTable.setEditTriggers(QTableWidget.NoEditTriggers)
        vacationsTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        vacationsTable.setColumnWidth(2, 40)
        vacationsTable.setColumnWidth(3, 40)
        tableHeader.hide()
        return vacationsTable

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)

    def loadVacationsTable(self):
        vacations = self.getConfig()['vacations']
        self.vacations.setRowCount(0)
        row = 0
        for vacation in vacations:
            if vacation['profile'] == self.mw.pm.name:
                rc = self.vacations.rowCount()
                self.vacations.setRowCount(rc + 1)
                self.vacations.setItem(rc, 0, QTableWidgetItem(vacation['name']))
                self.vacations.setItem(rc, 1, QTableWidgetItem(vacation['range'] ))
                editButton =  QPushButton("Edit");
                editButton.setFixedWidth(40)
                editButton.clicked.connect(self.editVacationRow(row))
                self.vacations.setCellWidget(rc, 2, editButton)   
                deleteButton =  QPushButton("X");
                deleteButton.setFixedWidth(40)
                deleteButton.clicked.connect(self.removeVacationRow(row))
                self.vacations.setCellWidget(rc, 3, deleteButton)
            row += 1

    def editVacation(self, idx):
        newConfig = self.getConfig()
        vacation = newConfig['vacations'][idx]
        if not self.vacationScheduler:
            self.vacationScheduler = VacationScheduler(self.mw, self)
        self.vacationScheduler.loadForEdit(idx, vacation)
        if self.vacationScheduler.windowState() == Qt.WindowMinimized:
            self.vacationScheduler.setWindowState(Qt.WindowNoState)
        self.vacationScheduler.setFocus()
        self.vacationScheduler.activateWindow()

    def removeVacationRow(self, x):
        return lambda: self.removeVacation(x)

    def editVacationRow(self, x):
        return lambda: self.editVacation(x)

    def removeVacation(self, row):
        if miAsk('Are you sure you would like to remove this vacation from the schedule? This action will happen immediately and is not un-doable.', self):
            newConfig = self.getConfig()
            vacations = newConfig['vacations']
            del vacations[row]
            self.mw.addonManager.writeConfig(__name__, newConfig)
            self.loadVacationsTable()
            self.rescheduler.initScheduler()
            self.rescheduler.setupCalendars()
            miInfo('Please be aware that your review schedule will not be updated until the next time it is optimized.')


    def addVacation(self):
        
        if not self.vacationScheduler:
            self.vacationScheduler = VacationScheduler(self.mw, self)
        self.vacationScheduler.show()
        if self.vacationScheduler.windowState() == Qt.WindowMinimized:
            self.vacationScheduler.setWindowState(Qt.WindowNoState)
        self.vacationScheduler.setFocus()
        self.vacationScheduler.activateWindow()


class VacationScheduler(QWidget):
    def __init__(self, mw, parent):
        super(VacationScheduler, self).__init__(parent, Qt.Window)
        self.mw = mw
        self.ledger = parent
        self.calendarStart = VacationCalendar(self)
        self.calendarEnd = VacationCalendar(self)
        self.edit = False
        self.vacationName = QLineEdit()
        self.sd = False
        self.ed = False
        self.selectedDecks = []
        self.startDate = QPushButton('Select Date')
        self.endDate = QPushButton('Select Date')
        self.setWindowTitle("Migaku Vacation Scheduler")
        self.setWindowModality(Qt.ApplicationModal)
        self.decksTable = self.setupDecksTable()
        self.loadDecks()
        self.selectAll = QPushButton('Select All')
        self.removeAll = QPushButton('Remove All')
        self.cancelButton = QPushButton('Cancel')
        self.saveButton = QPushButton('Save')
        self.setupLayout()
        self.initHandlers()
        self.initTooltips()
        self.show()

    def initTooltips(self):
        self.vacationName.setToolTip('The name of the vacation.')
        self.startDate.setToolTip('Select your vacation\'s starting date.')
        self.endDate.setToolTip('Select your vacation\'s end date.')
        self.selectAll.setToolTip('Select to apply this vacation to all decks.')
        self.removeAll.setToolTip('Remove all decks from the current vacation.')
        

    def closeEvent(self, event):
        self.clearHide()

    def initHandlers(self):
        self.startDate.clicked.connect(lambda: self.calendarStart.openCalendar(True))
        self.endDate.clicked.connect(lambda: self.calendarEnd.openCalendar(False))
        self.selectAll.clicked.connect(self.selectAllDecks)
        self.removeAll.clicked.connect(self.removeAllDecks)
        self.cancelButton.clicked.connect(self.clearHide)
        self.saveButton.clicked.connect(self.saveVacation)

    def saveVacation(self):
        newConfig = self.ledger.getConfig()
        currentVacations = newConfig['vacations']
        vacName = self.vacationName.text()
        if not self.sd or not self.ed or len(self.selectedDecks) < 0 or vacName == '':
            miInfo('Please give your vacation a name and select both a start date and end date and at least one deck.')
            return
        if vacName in currentVacations and self.edit is not False:
            miInfo('Vacations must be named uniquely, a vacation with the current name already exists.')
            return

        vacation = {}
        vacation['name'] = vacName
        vacation['profile']  = self.mw.pm.name
        vacation['start'] = str(self.sd.year()) + ',' + str(self.sd.month()) + ',' + str(self.sd.day())   
        vacation['range'] = str(self.sd.month()) + '/' + str(self.sd.day()) + '/' + str(self.sd.year()) + ' - ' + str(self.ed.month()) + '/' + str(self.ed.day()) + '/' + str(self.ed.year()) 
        vacation['length'] = self.sd.daysTo(self.ed)
        vacation['decks'] = self.selectedDecks
        vacation['timestamp'] = str(QDateTime(self.sd).toSecsSinceEpoch())
        if self.edit is not False:
            currentVacations[self.edit] = vacation
        else:
            currentVacations.append(vacation)
        newConfig['vacations']  = sorted(currentVacations, key = lambda i: i['timestamp'])
        self.mw.addonManager.writeConfig(__name__, newConfig)
        self.ledger.loadVacationsTable()
        self.ledger.rescheduler.initScheduler()
        self.ledger.rescheduler.setupCalendars()
        miInfo('Please be aware that your review schedule will not be updated until the next time it is optimized.')
        self.clearHide()


    def loadForEdit(self,idx, vacation):
        self.clearAll()
        self.vacationName.setEnabled(False)
        self.vacationName.setText(vacation['name'])
        start, end = vacation['range'].split(' - ')
        sm, sd, sy = start.split('/')
        em, ed, ey = end.split('/')
        self.sd = QDate(int(sy), int(sm), int(sd))
        self.ed = QDate(int(ey), int(em), int(ed))
        self.startDate.setText(start)
        self.endDate.setText(end)
        self.selectedDecks = vacation['decks']
        self.selectDecks(self.selectedDecks)
        self.calendarEnd.cal.setMinimumDate(self.sd)
        self.calendarStart.cal.setMaximumDate(self.ed)
        self.edit = idx
        self.show()


    def selectDecks(self, decks):
        for i in range(self.decksTable.rowCount()):
            cb = self.decksTable.cellWidget(i, 1)
            deck = self.decksTable.item(i, 0).text()
            if deck in decks:
                cb.setChecked(True)
        
    def clearAll(self):
        self.edit = False
        self.sd = False
        self.ed = False
        self.selectedDecks = []
        self.vacationName.clear()
        self.vacationName.setEnabled(True)
        self.startDate.setText('Select Date')
        self.endDate.setText('Select Date')
        self.calendarEnd.setMinMax()
        self.calendarStart.setMinMax()
        self.removeAllDecks()

    def clearHide(self):
        self.clearAll()
        self.hide()

    def selectAllDecks(self):
        for i in range(self.decksTable.rowCount()):
            cb = self.decksTable.cellWidget(i, 1)
            deck  = self.decksTable.item(i, 0).text()
            if not cb.isChecked():
                cb.setChecked(True)
                self.selectedDecks.append(deck)


    def removeAllDecks(self):
        for i in range(self.decksTable.rowCount()):
            cb = self.decksTable.cellWidget(i, 1)
            deck  = self.decksTable.item(i, 0).text()
            if cb.isChecked():
                cb.setChecked(False)
                if deck in self.selectedDecks:
                    self.selectedDecks.remove(deck)
                

    def setupLayout(self):
        self.layout = QVBoxLayout()

        hlay1 = QHBoxLayout()
        hlay1.addWidget(QLabel('Vacation Name: '))
        hlay1.addWidget(self.vacationName)
        self.layout.addLayout(hlay1)

        hlayp = QHBoxLayout()
        hlayp.addWidget(QLabel('Profile: '))
        hlayp.addWidget(QLabel(self.mw.pm.name))
        self.layout.addLayout(hlayp)

        hlay2 = QHBoxLayout()
        hlay2.addWidget(QLabel('Start Date: '))
        hlay2.addWidget(self.startDate)
        self.layout.addLayout(hlay2)

        hlay3 = QHBoxLayout()
        hlay3.addWidget(QLabel('End Date: '))
        hlay3.addWidget(self.endDate)
        self.layout.addLayout(hlay3)
        self.layout.addWidget(QLabel('Decks'))
        self.layout.addWidget(self.decksTable)

        hlay4 = QHBoxLayout()
        hlay4.addWidget(self.removeAll)
        hlay4.addWidget(self.selectAll)
        hlay4.addStretch()
        self.layout.addLayout(hlay4)

        hlay5 = QHBoxLayout()
        hlay5.addStretch()
        hlay5.addWidget(self.cancelButton)
        hlay5.addWidget(self.saveButton)
        self.layout.addLayout(hlay5)

        self.setLayout(self.layout)


    def loadDecks(self):

        decks = [d['name'] for d in self.mw.col.decks.all() if d['dyn'] == 0]
        decks.sort()
        for deck in decks:
            rc = self.decksTable.rowCount()
            self.decksTable.setRowCount(rc + 1)
            self.decksTable.setItem(rc, 0, QTableWidgetItem(deck))
            checkBox =  QCheckBox()
            checkBox.setFixedWidth(40)
            checkBox.setStyleSheet('QCheckBox{padding-left:10px;}')
            checkBox.clicked.connect(self.getDeckToggler(checkBox, rc))
            self.decksTable.setCellWidget(rc, 1, checkBox)


    def getDeckToggler(self, cb, x):
        return lambda: self.toggleDeck(cb, x)

    def toggleDeck(self,cb,  row):
        deck  = self.decksTable.item(row, 0).text()
        if cb.isChecked():
            self.selectSubdecks(deck)
            if deck not in self.selectedDecks:
                self.selectedDecks.append(deck)
        else:
            self.deselectSubdecks(deck)
            if deck in self.selectedDecks:
                self.selectedDecks.remove(deck)

    
    def selectSubdecks(self, deck):
        for i in range(self.decksTable.rowCount()):
            dn = self.decksTable.item(i, 0).text()
            if dn.startswith(deck + '::'):
                cb = self.decksTable.cellWidget(i, 1)
                cb.setChecked(True)
                if dn not in self.selectedDecks:
                    self.selectedDecks.append(dn)

    def deselectSubdecks(self,deck):
        for i in range(self.decksTable.rowCount()):
            dn = self.decksTable.item(i, 0).text()
            if dn.startswith(deck + '::'):
                cb = self.decksTable.cellWidget(i, 1)
                cb.setChecked(False)
                if dn in self.selectedDecks:
                    self.selectedDecks.remove(dn)

    def setupDecksTable(self):
        macLin = False
        if isMac  or isLin:
            macLin = True
        dictionaries = QTableWidget()
        dictionaries.setColumnCount(2)
        tableHeader = dictionaries.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.Fixed)
        dictionaries.setRowCount(0)
        dictionaries.setSortingEnabled(False)
        dictionaries.setEditTriggers(QTableWidget.NoEditTriggers)
        dictionaries.setSelectionBehavior(QAbstractItemView.SelectRows)
        dictionaries.setColumnWidth(1, 40)
        tableHeader.hide()
        return dictionaries

    def showDate(self, date):
    
      self.lbl.setText(date.toString())

    def loadVacationScheduler(self):
        return

    def clearVacationScheduler(self):
        return

    def updateDate(self, date, starting):
        if starting:
            self.calendarEnd.cal.setMinimumDate(date)
            self.sd = date
            self.startDate.setText(str(date.month()) +'/' + str(date.day()) + '/' + str(date.year()))
        else:
            self.calendarStart.cal.setMaximumDate(date)
            self.ed = date
            self.endDate.setText(str(date.month()) +'/' + str(date.day()) + '/' + str(date.year()))



class VacationCalendar(QWidget):
    def __init__(self, scheduler):
        super(VacationCalendar, self).__init__(scheduler, Qt.Window)
        self.scheduler = scheduler
        self.startingDate = True
        self.cal = QCalendarWidget()
        self.cal.setGridVisible(True)
        self.cal.clicked[QDate].connect(self.dateToScheduler)
        self.layout = QVBoxLayout()
        self.setWindowModality(Qt.ApplicationModal)
        self.layout.addWidget(self.cal)
        self.setLayout(self.layout)
        self.setMinMax()
    
    def setMinMax(self):
        today = date.today()
        self.cal.setMinimumDate(QDate(today.year, today.month, today.day))    
        self.cal.setMaximumDate(QDate(2100, 1, 1)) 

    def openCalendar(self, starting):
        if starting:
            self.startingDate = True
            self.setWindowTitle("Start Date")
        else:
            self.startingDate = False
            self.setWindowTitle("End Date")
        self.show()

    def dateToScheduler(self, date):
      self.scheduler.updateDate(date, self.startingDate)
      self.hide()

    
