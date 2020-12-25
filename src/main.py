# -*- coding: utf-8 -*-
# 
from os.path import  join, dirname
import re
import aqt
from anki.hooks import addHook, wrap
from aqt import mw
import anki.find
from aqt.qt import QAction
from aqt.utils import showInfo, shortcut
from aqt.qt import *
import json
from datetime import datetime
from aqt.browser import DataModel
import time
from anki.sched import Scheduler
import anki.schedv2
import math
from anki.stats import CollectionStats
from .rescheduler import MIRescheduler
from .vacations import VacationPicker
from .sickday import SickScheduler
from .weeklySchedule import WeeklyScheduler
from aqt.overview import Overview
from .settings import VacationSettings
from .getAhead import GetAhead
from anki.collection import _Collection
from aqt.deckconf import DeckConf
import aqt.importing
from anki.lang import _
from anki import Collection

colYoung = "#7c7"
colMature = "#070"
colCum = "rgba(0,0,0,0.9)"
colLearn = "#00F"
colRelearn = "#c00"
colCram = "#ff0"
colIvl = "#077"
colHour = "#ccc"
colTime = "#770"
colUnseen = "#000"
colSusp = "#ff0"



addon_path = dirname(__file__)


mw.MigakuRescheduler = MIRescheduler(mw, addon_path)

mw.migakuGetAhead = GetAhead(mw, addon_path)

mw.miSickSched = SickScheduler(mw, addon_path, mw.MigakuRescheduler)

VacationScheduler = VacationPicker(mw, addon_path, mw.MigakuRescheduler)

WeeklySched = WeeklyScheduler(mw, addon_path, mw.MigakuRescheduler)

mw.miVacSettings = False


def openVacationSettings():
    if not mw.miVacSettings:
        mw.miVacSettings  = VacationSettings(mw, addon_path, openVacationSettings)
    mw.miVacSettings.show()
    if mw.miVacSettings.windowState() == Qt.WindowMinimized:
           mw.miVacSettings.setWindowState(Qt.WindowNoState)
    mw.miVacSettings.setFocus()
    mw.miVacSettings.activateWindow()


def setupGuiMenu():
    addMenu = False
    if not hasattr(mw, 'MigakuMainMenu'):
        mw.MigakuMainMenu = QMenu('Migaku',  mw)
        addMenu = True
    if not hasattr(mw, 'MigakuMenuSettings'):
        mw.MigakuMenuSettings = []
    if not hasattr(mw, 'MigakuMenuActions'):
        mw.MigakuMenuActions = []

    setting = QAction("Vacation Settings", mw)
    setting.triggered.connect(openVacationSettings)    
    mw.MigakuMenuSettings.append(setting)
    action = QAction("Optimize Schedule", mw)
    action.triggered.connect(mw.MigakuRescheduler.loopCol)
    action2 = QAction("Vacation Scheduler", mw)
    action2.triggered.connect(VacationScheduler.start)
    action3 = QAction("Sick Day (All Decks)", mw)
    action3.triggered.connect(mw.miSickSched.sickDayPrompt)
    action4 = QAction("Catch Up (All Decks)", mw)
    action4.triggered.connect(mw.miSickSched.openScheduler)
    mw.MigakuMenuActions.append(action)
    mw.MigakuMenuActions.append(action2)
    mw.MigakuMenuActions.append(action3)
    mw.MigakuMenuActions.append(action4)
    mw.MigakuMainMenu.clear()
    for act in mw.MigakuMenuSettings:
        mw.MigakuMainMenu.addAction(act)
    mw.MigakuMainMenu.addSeparator()
    for act in mw.MigakuMenuActions:
        mw.MigakuMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.MigakuMainMenu)  

def miLinkHandler(self, url):
    if url == "catchup":
        mw.miSickSched.openWithDeck()
    elif url == "sickday":
        mw.miSickSched.sickdayWithDeck()
    elif url == "getahead":
        mw.migakuGetAhead.openGetAhead()

def renderWithSickDay(self):
        links = [
            ["O", "opts", _("Options")],
        ]
        if self.mw.col.decks.current()['dyn']:
            links.append(["R", "refresh", _("Rebuild")])
            links.append(["E", "empty", _("Empty")])
        else:
            links.append(["C", "studymore", _("Custom Study")])
            links.append(["F", "cram", _("Filter/Cram")])
            links.append(["", "sickday", _("Sick Day")])
            links.append(["", "catchup", _("Catch Up")])
            links.append(["", "getahead", _("Get Ahead")])
        if self.mw.col.sched.haveBuried():
            links.append(["U", "unbury", _("Unbury")])
        buf = ""
        for b in links:
            if b[0]:
                b[0] = _("Shortcut key: %s") % shortcut(b[0])
            buf += """
<button title="%s" onclick='pycmd("%s")'>%s</button>""" % tuple(b)
        self.bottom.draw(buf)
        self.bottom.web.onBridgeCmd = self._linkHandler

Overview._renderBottom = wrap(Overview._renderBottom, renderWithSickDay)
Overview._linkHandler = wrap(Overview._linkHandler, miLinkHandler, 'before')

setupGuiMenu()

aqt.forms.dconf.Ui_Dialog.setupUi = wrap(aqt.forms.dconf.Ui_Dialog.setupUi, WeeklySched.addScheduleOpts)
DeckConf.loadConf = wrap(aqt.deckconf.DeckConf.loadConf, WeeklySched.loadSchedule)
DeckConf.saveConf = wrap(aqt.deckconf.DeckConf.saveConf, WeeklySched.saveSchedule, "before")


def runOptimizationRetirement():
    if hasattr(mw, 'runMigakuRetirement'):
        mw.refreshRetirementConfig()
        retirement = False
        if mw.RetroactiveRetiring or (mw.DailyRetiring and (time.time() - mw.LastMassRetirement > 86400000)):
            retirement = True
        optimizer = False
        if mw.MigakuRescheduler.runDaily(retirement):
            optimizer = True
        if retirement:
            mw.runMigakuRetirement(optimizer = optimizer)
    else:
        mw.MigakuRescheduler.runDaily()



addHook("profileLoaded", mw.MigakuRescheduler.initScheduler)
addHook("profileLoaded", mw.MigakuRescheduler.setupCalendars)
addHook("profileLoaded", runOptimizationRetirement)
addHook("profileLoaded",VacationScheduler.deleteOldVacations)
addHook("profileLoaded", mw.miSickSched.updateSickIds)

def miReport(self, type=0):
        # 0=days, 1=weeks, 2=months
        self.type = type
        from anki.statsbg import bg
        txt = self.css % bg
        txt += self._section(self.todayStats())
        resetRescheduler()
        currentSched, firstDue = mw.MigakuRescheduler.getCurrentSched()
        txt += self._section(self.miGraph(currentSched, 'ogSchedule' , "Long Term Schedule", "Long-term schedule in days for your entire collection."))
        txt += self._section(self.dueGraph())
        txt += self.repsGraphs()
        txt += self._section(self.introductionGraph())
        txt += self._section(self.ivlGraph())
        txt += self._section(self.hourGraph())
        txt += self._section(self.easeGraph())
        txt += self._section(self.cardGraph())
        txt += self._section(self.footer())
        
        return "<center>%s</center>" % txt

def miGraph(self, schedule, name, t1, t2):

        start = schedule[0][0] 
        if start > 0:
            start = 0
        end = min(365, schedule[len(schedule) -1][0]) + 1
        chunk = 1
        tot = 0
        totd = []
        count = 0
        maxVal = end
        if start < 0:
            abstart = abs(start)
            maxVal += abstart
         
        for day in schedule:

            tot += day[1]
            totd.append((day[0], tot))
            if count == maxVal:
                break
            count += 1
        data = [
            dict(data=schedule, color=colMature, label=_("Due"))
        ]
        if len(totd) > 1:
            data.append(
                dict(data=totd, color=colCum, label=_("Cumulative"), yaxis=2,
                     bars={'show': False}, lines=dict(show=True), stack=False))
        txt = self._title(
            _(t1),
            _(t2))
        xaxis = dict(tickDecimals=0, min=start)
        if end is not None:
            xaxis['max'] = end-0.5
        txt += self._graph(
            id=name, data=data, xunit=chunk, ylabel2=_("Cumulative Cards"),
            conf=dict(
                xaxis=xaxis, yaxes=[
                    dict(min=0), dict(min=0, tickDecimals=0, position="right")]
            ),
        )
        txt += self._dueInfo(tot, len(totd)*chunk)
        return txt

CollectionStats.miGraph = miGraph
CollectionStats.report = miReport

def miNextRevIvl(self, card, ease, dueDate = False, reviewDate = False):
    "Ideal next interval for CARD, given EASE."
    delay = False
    if dueDate is not False and reviewDate is not False:
        delay = miDaysLate(dueDate, reviewDate)
    else:
        delay = self._daysLate(card)
    conf = self._revConf(card)
    fct = card.factor / 1000
    ivl2 = self.constrainInterval((card.ivl + delay // 4) * 1.2, conf, card.ivl)
    ivl3 = self.constrainInterval((card.ivl + delay // 2) * fct, conf, ivl2)
    ivl4 = self.constrainInterval(
        (card.ivl + delay) * fct * conf['ease4'], conf, ivl3)
    if ease == 2:
        interval = ivl2
    elif ease == 3:
        interval = ivl3
    elif ease == 4:
        interval = ivl4
    return min(interval, conf['maxIvl']); 

def miDaysLate(dueDate, reviewDate):
    return max(0, reviewDate - dueDate)

Scheduler.constrainInterval = Scheduler._constrainedIvl
anki.schedv2.Scheduler.constrainInterval = Scheduler._constrainedIvl
anki.schedv2.Scheduler.getReviewInterval  = miNextRevIvl
Scheduler.getReviewInterval = miNextRevIvl


def miUndoOp(self):
    if self._undo[1] == 'Catch Up Scheduler':
        mw.miSickSched.removeSickIds()

_Collection._undoOp = wrap(_Collection._undoOp, miUndoOp, 'before')
_Collection.remCards = wrap(_Collection.remCards, mw.miSickSched.removeSickIdsByCid)
_Collection.undo = wrap(_Collection.undo, mw.miSickSched.attemptReturnSickIds, 'before')
_Collection.markReview = wrap(_Collection.markReview, mw.miSickSched.clearReturnIds)
_Collection._markOp = wrap(_Collection._markOp, mw.miSickSched.clearReturnIds)

# aqt.importing.onImport = wrap(aqt.importing.onImport, mw.MigakuRescheduler.setupCalendars)

import zipfile
import os
import shutil
import unicodedata
from anki.lang import _, ngettext
from aqt.utils import showWarning, tooltip
from concurrent.futures import Future


def miReplaceWithApkg(mw, filename, backup):
    mw.progress.start(immediate=True)

    def do_import():
        z = zipfile.ZipFile(filename)

        # v2 scheduler?
        colname = "collection.anki21"
        try:
            z.getinfo(colname)
        except KeyError:
            colname = "collection.anki2"

        with z.open(colname) as source, open(mw.pm.collectionPath(), "wb") as target:
            # ignore appears related to https://github.com/python/typeshed/issues/4349
            # see if can turn off once issue fix is merged in
            shutil.copyfileobj(source, target)

        d = os.path.join(mw.pm.profileFolder(), "collection.media")
        for n, (cStr, file) in enumerate(
            json.loads(z.read("media").decode("utf8")).items()
        ):
            mw.taskman.run_on_main(
                lambda n=n: mw.progress.update(
                    ngettext("Processed %d media file", "Processed %d media files", n)
                    % n
                )
            )
            size = z.getinfo(cStr).file_size
            dest = os.path.join(d, unicodedata.normalize("NFC", file))
            # if we have a matching file size
            if os.path.exists(dest) and size == os.stat(dest).st_size:
                continue
            data = z.read(cStr)
            with open(dest, "wb") as file:
                file.write(data)

        z.close()

    def on_done(future: Future):
        mw.progress.finish()

        try:
            future.result()
        except Exception as e:
            print(e)
            showWarning(_("The provided file is not a valid .apkg file."))
            return

        if not mw.loadCollection():
            return
        if backup:
            mw.col.modSchema(check=False)

        tooltip(_("Importing complete."))
        resetRescheduler()
        mw.miSickSched.promptCatchUpRemoval()

    mw.taskman.run_in_background(do_import, on_done)



def resetRescheduler(*args):
    mw.MigakuRescheduler.initScheduler()
    mw.MigakuRescheduler.setupCalendars()


aqt.preferences.Preferences.accept = wrap(aqt.preferences.Preferences.accept, resetRescheduler)
aqt.importing._replaceWithApkg = miReplaceWithApkg

