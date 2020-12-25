# -*- coding: utf-8 -*-
# 
from aqt.qt import *
from os.path import dirname, join
from aqt.utils import showInfo
from .miutils import miInfo, miAsk
from datetime import date



class WeeklyScheduler():

    def __init__(self, mw, path, rescheduler):
        self.mw = mw
        self.path = path
        self.rescheduler = rescheduler
        self.ogSchedule = False

    def addScheduleOpts(self, dconf, Dialog):
        row = dconf.gridLayout_3.rowCount()
        wid = QLabel("<b>Review Schedule</b>")
        dconf.gridLayout_3.addWidget(wid, row, 0, 1, 1)
        row += 1
        monl = QLabel('Monday:')
        tuel = QLabel('Tuesday:')
        wedl = QLabel('Wednesday:')
        thul = QLabel('Thursday:')
        fril = QLabel('Friday:')
        satl = QLabel('Saturday:')
        sunl = QLabel('Sunday:')
        dconf.mon = QCheckBox()
        dconf.tue = QCheckBox()
        dconf.wed = QCheckBox()
        dconf.thu = QCheckBox()
        dconf.fri = QCheckBox()
        dconf.sat = QCheckBox()
        dconf.sun = QCheckBox()
        dconfWeekLay = QHBoxLayout()
        dconfWeekLay.addWidget(monl)
        dconfWeekLay.addWidget(dconf.mon)
        dconfWeekLay.addWidget(tuel)
        dconfWeekLay.addWidget(dconf.tue)
        dconfWeekLay.addWidget(wedl)
        dconfWeekLay.addWidget(dconf.wed)
        dconfWeekLay.addWidget(thul)
        dconfWeekLay.addWidget(dconf.thu)
        dconfWeekLay.addWidget(fril)
        dconfWeekLay.addWidget(dconf.fri)
        dconfWeekLay.addWidget(satl)
        dconfWeekLay.addWidget(dconf.sat)
        dconfWeekLay.addWidget(sunl)
        dconfWeekLay.addWidget(dconf.sun)
        dconfWeekLay.addStretch()
        dconf.gridLayout_3.addLayout(dconfWeekLay, row, 0, 1, 3)
    
    def saveSchedule(self, dconf):
        c = dconf.conf['new']
        f = dconf.form
        c['weeklySchedule'] = [f.mon.isChecked(), f.tue.isChecked(), f.wed.isChecked(), f.thu.isChecked(), f.fri.isChecked(), f.sat.isChecked(), f.sun.isChecked()]
        self.rescheduler.initScheduler()
        self.rescheduler.setupCalendars()
        if self.ogSchedule != c['weeklySchedule']:
            miInfo('Please be aware that any schedule changes will not be reflected until the next time the schedule is optimized.')

    def loadSchedule(self, dconf):
       
        c = dconf.conf['new']
        f = dconf.form
        if 'weeklySchedule' not in c:
            c['weeklySchedule'] = [True, True, True, True, True, True, True]
        self.ogSchedule = c['weeklySchedule']
        f.mon.setChecked(c['weeklySchedule'][0])
        f.tue.setChecked(c['weeklySchedule'][1])
        f.wed.setChecked(c['weeklySchedule'][2])
        f.thu.setChecked(c['weeklySchedule'][3])
        f.fri.setChecked(c['weeklySchedule'][4])
        f.sat.setChecked(c['weeklySchedule'][5])
        f.sun.setChecked(c['weeklySchedule'][6])




