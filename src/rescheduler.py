# -*- coding: utf-8 -*-
# 
# 
from os.path import  join, dirname
import re
from anki.hooks import addHook
from aqt import mw
from aqt.qt import QAction
from aqt.utils import showInfo
from aqt.qt import *
import json
from datetime import datetime
from datetime import date
from aqt.browser import DataModel
from .miutils import miInfo, miAsk
import time
from anki.sched import Scheduler
import anki.schedv2
import random


class MIRescheduler():

    def __init__(self, mw, path):
        self.restCalendar = {}
        self.mw = mw
        self.path = path
        self.reRepped = {}
        self.allCards = []
        self.okCards = 0
        self.badCards = 0
        self.examining = []
        self.config = self.getConfig()


    def getToday(self):
        return int((time.time() - self.mw.col.crt) // 86400)

    def initScheduler(self):
        self.scheduler = self.mw.col.sched
        self.today = self.getToday()
        self.reRepped = {}
        self.allCards = []
        self.okCards = 0
        self.badCards = 0
        self.examining = []
        self.config = self.getConfig()


    def repairFails(self, tag):
        self.mw.checkpoint('Failed Card Repair')
        self.today = self.getToday()
        retirementDeck = False
        if hasattr(self.mw, 'runMigakuRetirement'):
            try:
                deckName = self.mw.addonManager.getConfig('1666520655')['Retirement Deck Name']
                retirementDeck = self.mw.col.decks.byName(deckName)['id']
            except:
                retirementDeck = False
        cids = self.grabAllCards()
        for cid in cids:
            card = self.mw.col.getCard(cid)
            reps = self.getAllReps(cid)
            if not reps:
                continue
            if reps[0][2] == 2:
                multiplier = self.scheduler._lapseConf(card)['mult']
                card.ivl, newDue = self.getFailedIntervalDue(reps, multiplier)
                if len(str(int(card.due))) < 7:
                    card.due = int((newDue - self.scheduler.col.crt)//86400)
                else:
                    card.due = int(newDue)
                if card.did == retirementDeck:
                    card.queue = 2
                card.flush()
                self.mw.col.db.execute('update revlog set ivl = ? where id = ?', card.ivl, reps[0][0])
                if tag:
                    note = card.note()
                    note.tags.append('repairedFail')
                    note.flush()
        self.mw.reset()

    def getFailedIntervalDue(self, reps, mult):
        fails = 0
        ivl = 1
        finished = False
        try:
            for rep in reps:
                if rep[2] == 2:
                    fails += 1
                    day = rep[0] 
                elif rep[2] == 1:
                    ivl = rep[1]
                    day = rep[0]
                    finished = True
                    break
        except: 
            pass
        if not finished:
            return 1, self.today
        finalIvl = self.getReasonableInterval(ivl, mult, fails)
        return finalIvl, (day/1000 + (finalIvl * 86400))

    def getReasonableInterval(self, ivl, mult, fails):
        for i in range(0, fails):
            ivl = mult * ivl
        return max(1, int(ivl))


    def getAllReps(self, cid):
        try:
            last = self.mw.col.db.all(
                    "select id, lastIvl, type from revlog where cid = ? "
                    "order by id desc", cid)
            if last:
                last = list(last)
                return last
            else:
                return False
        except:
            return False

    def grabAllCards(self):
        return list(self.mw.col.find_cards(''))

    def ifVacationOrOptimize(self, vacations, optimize, maintain):
        for prof in self.restCalendar:
            if len(self.restCalendar[prof]) > 0:
                return True
        if optimize or maintain:
            return True
        return False

    def runDaily(self, retirement = False):
        newConfig = self.getConfig()
        dailyRun = newConfig['runDaily']
        self.optimize = False
        if self.config['optimizeSchedule'] != 0:
            self.optimize = self.config['optimizeSchedule']
        if not self.ifVacationOrOptimize(newConfig['vacations'], self.optimize, newConfig['maintainEase']):
            return False
        if dailyRun:
            runHistory = newConfig['runHistory']
            prof = self.mw.pm.name
            today = self.getToday()
            lastRun = -1
            if prof in runHistory:
                if lastRun and ',' not in str(lastRun):
                    lastRun = runHistory[prof]
            if today != lastRun:
                self.loopCol(retirement = retirement)  
                runHistory[prof] = today
                self.mw.addonManager.writeConfig(__name__, newConfig)
                return True
        return False

    def getAppropriateDate(self,curdue, future, did, learn = False):
        if self.optimize:
            return self.calculateDueDate(curdue, curdue, future, did, learn)
        else:
            return self.calculateUnoptimizedDueDate(curdue, future, did)

    def reRep(self, card, ease, lastReps):  
        self.allCards.append(card.id)
        lrnRelrnNew = False
        future = False
        relearned = False
        if card.due >= self.today:
            future = True
        if ease:
            relearned = False
            if lastReps[0][6] == 2:
                relearned = True
            card.factor = lastReps[0][4]
            reviewDate = int(((lastReps[0][0]) - self.scheduler.col.crt) // 86400)
            if card.type == 1 or card.queue in [1, 3] or len(lastReps) < 2 or lastReps[0][6] in [0, 3] or (relearned and card.ivl < 0):
                dueDate = reviewDate
                lrnRelrnNew = True
            else:
                if ease != 1 and not lrnRelrnNew:
                    if relearned:
                        card.ivl = lastReps[0][2]
                    else:
                        card.ivl = lastReps[0][3]
                dueDate = int(((lastReps[1][8]) - self.scheduler.col.crt) // 86400)
            if lrnRelrnNew:  ## relearned cards, cards in learning queue, sick day cards, and cards that were previously new cards honor their previous interval as well as possible
                    if card.queue in [1, 3]:
                        if card.queue == 1:
                            curDue = int(((card.due) - self.scheduler.col.crt) // 86400) ###learning card due date
                        else: 
                            curDue = card.due
                        if curDue >= self.today:
                            future = True

                        nextDue = self.getAppropriateDate(curDue, future, card.did, True)
                        if card.queue == 1:
                            card.due = int(time.time() + ((nextDue - self.today) *86400))
                        else:
                            card.due = nextDue
                    else:
                        curDue = card.due
                        nextDue = self.getAppropriateDate(curDue, future, card.did)
                        card.due = nextDue
                    interval = card.ivl
                    self.okCards += 1
            else:
                if self.optimize:
                    nextDue = self.getDueDate(card, ease, dueDate, reviewDate, lastReps[0][2], future, relearned)
                else:
                    nextDue = self.calculateUnoptimizedDueDate(card.due, future, card.did)
                interval = nextDue - reviewDate
                card.due = nextDue
        else:
            self.okCards += 1
            interval = card.ivl
            due = card.due
            nextDue = self.getAppropriateDate(due, future, card.did)
            card.due = nextDue
        card.ivl = interval
        if not lrnRelrnNew and not relearned: 
            lastrep = self.mw.col.db.scalar('select id from revlog where cid = %s order by id desc limit 1'%str(card.id))
            self.mw.col.db.execute('update revlog set ivl = ? where id = ?', interval, lastrep)
        if self.config['maintainEase']:
            card.factor = 2500
        card.flush()



    def getDueDate(self, card, ease, dueDate, reviewDate, oldi, future, relearned):
        conf = self.scheduler._lrnConf(card)
        if ease == 1:
            ivl = card.ivl
            mindue, maxdue = self.getMinMaxDue(ivl,ivl, reviewDate)
            nextDue = self.calculateDueDate(mindue, maxdue, future, card.did)
            self.okCards += 1
        else:
            onedaysep = False
            if relearned:
                nextIvl = card.ivl
                if card.ivl < 8:
                    onedaysep = True 
            else:
                nextIvl = self.scheduler.getReviewInterval(card, ease, dueDate, reviewDate)
            minv, maxv = self.scheduler._fuzzIvlRange(nextIvl)
            mindue, maxdue = self.getMinMaxDue( minv,maxv, reviewDate)
            nextDue = self.calculateDueDate(mindue, maxdue, future, card.did, onedaysep)
            if oldi >= minv and oldi <= maxv:
                self.okCards += 1
            else:
                self.badCards += 1
                self.examining.append(card.id)

        return nextDue 



    def getWeeklySchedule(self, did):
        settings = mw.col.decks.confForDid(did)
        if 'new' not in settings or 'weeklySchedule' not in settings['new']:
            setting = [True, True, True, True, True, True, True]
        else:
            setting = settings['new']['weeklySchedule']
        return self.formatRestdays(setting)

    def setupCalendars(self, *args):    
        self.restCalendar = {}
        self.today = self.getToday()
        vacationSchedule = self.getVacations()
        dids = self.mw.col.decks.allIds()
        for did in dids:
            weekends = self.getWeeklySchedule(did)
            dayofweek = time.localtime().tm_wday
            self.restCalendar[did] = []
            dName = self.mw.col.decks.get(did)['name']
            for day in range(self.today, self.today + 1095):
                if dayofweek in weekends:
                    self.restCalendar[did].append(day)
                if dayofweek == 6:
                    dayofweek = 0
                else:
                    dayofweek += 1

            if dName in vacationSchedule:
                self.restCalendar[did] += vacationSchedule[dName]



    def getVacations(self, profile = True):
        vacations = self.getConfig()['vacations']
        vacationSchedule = {}
        curProfile = self.mw.pm.name
        for v in vacations:
            if v['profile'] == curProfile:
                for deck in v['decks']:
                    if deck in vacationSchedule:
                        vacationSchedule[deck].append([v['start'], v['length']])
                    else:
                        vacationSchedule[deck] = [[v['start'], v['length']]]
        for dVacs in vacationSchedule:
            vacationSchedule[dVacs] = self.getVacationsCalendar(vacationSchedule[dVacs])
        return vacationSchedule

    def getVacationsCalendar(self, vacations):
        calendar = []
        for idx, vacation in enumerate(vacations):
            start = int((self.getTimestamp(vacation[0]) - self.mw.col.crt )//86400) + 1
            end = start + vacation[1]
            for day in range(start, end + 1):
                if day not in calendar:
                    calendar.append(day)
        return calendar

    def getLastReps(self, cid):
        last = self.mw.col.db.all(
                "select id, ease, ivl, lastIvl, factor, time, type from revlog where cid = ? "
                "order by id desc limit 2", cid)
        if last:
            last = list(last)
            for idx,l in enumerate(last):
                last[idx] = list(last[idx])
                last[idx][0] = last[idx][0]/1000
                last[idx].append(str(datetime.fromtimestamp(last[idx][0])))
                if last[idx][2] < 0:
                    dueDate = (last[idx][0]) + abs(last[idx][2])
                else:
                    dueDate = (last[idx][0]) + ( last[idx][2] * 86400)
                last[idx].append(dueDate)
            return last
        else:
            return False


    def getAdjustment(self, default, length, ratio):
        adjustment = 3
        if default <= adjustment: 
            ivlBasedAdj = int(length * ratio)
            if ivlBasedAdj > adjustment:
                adjustment = ivlBasedAdj
        return adjustment


    def getValidDates(self, mindue, maxdue, future, learn, did):
        valid = []
        sep = 3
        mindue = round(mindue)
        maxdue = round(maxdue)
        if learn:
            sep = 1
        else:
            alternateSep = int((maxdue - mindue) * .5)
            if alternateSep > 3:
                sep = alternateSep
        if future:
            og1 = mindue
            og2 = maxdue
            if mindue < self.today and maxdue < self.today:
                minmaxSep = round((maxdue - mindue)/2)
                mindue, maxdue = self.today, self.today + minmaxSep
            elif mindue < self.today:
                mindue = self.today
        while True:
            for day in range(mindue, maxdue+1):
                if (future and day < self.today) or day in self.restCalendar[str(did)]:
                    continue
                valid.append(day)
            if len(valid) > 0:
                return valid
            mindue, maxdue = self.getExpandedRange(mindue, maxdue, sep)
            valid = []
            
                
    def intoThirds(self, a, n = 3):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


    def getExpandedRange(self, minDue, maxDue, sep):
        return minDue - sep, maxDue + sep;

    def calculateUnoptimizedDueDate(self, due, future, did):
        dueDate = False
        validDates = self.getValidDates(due, due, future, True, did)
        return random.choice(validDates)


    def calculateDueDate(self, mindue, maxdue, future, did, learn = False):
        dueDate = False
        validDates = self.getValidDates(mindue, maxdue, future, learn, did)
        strDid = str(did)
        if strDid not in self.reRepped:
            self.reRepped[strDid] = {}
        first, second, third = self.intoThirds(validDates)
        if len(third) < 1:
            if len(second) < 1:
                third = False
                second = first
                first = False
            else:
                third = False
                second = second
                first = first
        dueDate = self.decideFinalDate(first, second ,third, strDid)
        graphDate = dueDate - self.today
        self.updateReRepped(str(graphDate), graphDate, strDid)
        return dueDate

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)

    def decideFinalDate(self, begRange, midRange, lastRange, strDid):
        options = False
        if midRange and begRange and not lastRange:
            options = 2
        elif midRange and begRange and lastRange:
            options = 3
        midDue, midLeast = self.getDueLeast(midRange, strDid)   
        if options == 2:
            begDue, begLeast = self.getDueLeast(begRange, strDid)
            if begLeast < midLeast:
                return begDue
        elif options == 3:
            begDue, begLeast = self.getDueLeast(begRange, strDid)
            lastDue, lastLeast = self.getDueLeast(lastRange, strDid)
            if lastLeast < midLeast and lastLeast <= begLeast:
                return lastDue
            elif begLeast < midLeast:
                return begDue

        return midDue

    def updateProfLevel(self, due, nDue):
        if due in self.reRepped:
            self.reRepped[due] += 1
        else:
            self.reRepped[due] = 1

    def updateDeckLevel(self, due, nDue, strDid):
        if due in self.reRepped[strDid]:
            self.reRepped[strDid][due] += 1
        else:
            self.reRepped[strDid][due] = 1


    def updateReRepped(self, due, nDue, strDid):
        if self.optimize == 1:
            self.updateDeckLevel(due, nDue, strDid)
        else:
            self.updateProfLevel(due, nDue)
       


    def dueDateToTimestamp(self, day):
         return time.time() + (day - self.today) * 86400

    def getDueLeastProf(self, drange):
        least = False
        value = False
        msg = ''
        for day in drange:
                sday = str(day - self.today) 
                if sday in self.reRepped:
                    if not least:
                        least = self.reRepped[sday]
                        value = day
                    elif least >= self.reRepped[sday]:
                        least = self.reRepped[sday]
                        value = day
                else:
                    least = 0
                    value = day
        return value, least;

    def getDueLeastDeck(self, drange, strDid):
        least = False
        value = False
        msg = ''
        for day in drange:
                sday = str(day - self.today) 
                if sday in self.reRepped[strDid]:
                    if not least:
                        least = self.reRepped[strDid][sday]
                        value = day
                    elif least >= self.reRepped[strDid][sday]:
                        least = self.reRepped[strDid][sday]
                        value = day
                else:
                    least = 0
                    value = day
        return value, least;

    def getDueLeast(self, drange, strDid):
        if self.optimize == 1:
            return self.getDueLeastDeck(drange, strDid)
        else:
            return self.getDueLeastProf(drange)
        
            
    def getTimestamp(self, date):
        return time.mktime(datetime.strptime(date, "%Y,%m,%d").timetuple())

    def getReppedToday(self):
        return len(list(self.mw.col.find_cards('rated:1')))

    def deckLevelReppedToday(self):
        dids = self.mw.col.decks.allIds()
        for did in dids:
            strDid = str(did)
            dName = self.mw.col.decks.get(did)['name']
            repped = len(list(self.mw.col.find_cards('"rated:1" "deck:' + dName + '"')))
            self.reRepped[strDid] = {}
            self.reRepped[strDid]["0"] = repped

    def noRepsForEmptyDecks(self):
        dids = self.mw.col.decks.allIds()
        for did in dids:
            dName = self.mw.col.decks.get(did)['name']
            dRepped = len(list(self.mw.col.find_cards('"is:due" "deck:' + dName + '"')))
            if dRepped == 0:
                if did not in self.restCalendar:
                    self.restCalendar[did] = []
                self.restCalendar[did].append(self.today)

    def getDueCount(self):
        return len(list(self.mw.col.find_cards('is:due')))

    def retirementConflictCheck(self, repped):
        if self.optimize and hasattr(self.mw, "runMigakuRetirement"):
            due = self.getDueCount()
            if repped > 0 and due > 0:
               if not miAsk('You have not yet finished your reps and you have the Migaku Retirement Addon installed. Due to how Anki stores card '
                + 'rep information the optimization algorithm may schedule extra reviews today in proportion to how many ' + 
                'cards were retired during your review session. It is recommended that you finish your reviews before reoptimizing your schedule if you wish to avoid these potential extra reviews. ' +
                'Would you like to execute the optimization algorithm?'):
                    return False
            else:
                return True
        return True

    def getDueDateFromTimestamp(self, ts):
        return int(((ts) - self.scheduler.col.crt) // 86400) -  self.today 

    def loopCol(self, edit = False, retirement = False, sickDay = False):
        self.initScheduler()
        self.setupCalendars()
        self.creationOffset = self.mw.col.conf.get("creationOffset")
        self.config = self.getConfig()
        if self.creationOffset is not None:
            self.today = int((time.time() - self.mw.col.crt + (self.creationOffset * 60)) // 86400)
        else:
            self.today = self.getToday()
        reppedToday = self.getReppedToday()
        self.optimize = False
        if self.config['optimizeSchedule'] != 0:
            self.optimize = self.config['optimizeSchedule']
        if not self.retirementConflictCheck(reppedToday):
            return
        if not sickDay:
            if retirement:
                self.mw.checkpoint('Schedule Optimization and Retirement')
            else:
                self.mw.checkpoint('Schedule Optimization')
        self.config = self.getConfig()
        self.reRepped = {}
        if self.optimize == 1:
            self.deckLevelReppedToday()
        else:
            self.reRepped['0'] = reppedToday
        self.noRepsForEmptyDecks()
        progressWidget, bar, message = self.getProgressBar()
        sched2 = False
        if self.scheduler.name != 'std':
            sched2 = True
        learningCards = self.grabLearning()
        reviewCards = self.grabReviews()
        learningReviewing = list(set(learningCards + reviewCards))
        self.mw.miSickSched.removeMissingSickIds(learningReviewing)
        caughtUpCards = []
        bar.setMinimum(0)
        cardCount = 1
        total = len(learningReviewing)
        strTotal = str(total)
        bar.setMaximum(total)
        divisor = 100
        sickIds = self.mw.miSickSched.sickIds
        if total > 10000:
            divisor = 200
        onlyMaintainEase = True
        for prof in self.restCalendar:
            if len(self.restCalendar[prof]) > 0:
                onlyMaintainEase = False
        if self.optimize is not False:
            onlyMaintainEase = False
        for cid in learningReviewing:
            if cardCount % divisor == 0:
                bar.setValue(cardCount)
                message.setText('Rescheduling Card ' +  str(cardCount)  + '/' + strTotal + '...')
                mw.app.processEvents()
            cardCount += 1
            card = self.mw.col.getCard(cid)
            strid = str(cid)
            if strid in sickIds:
                oldReps, guid = sickIds[strid]
                if card.note().guid == guid:
                    if card.reps > oldReps:
                        del sickIds[strid]
                    else:
                        if not card.odid and not card.queue == -1:
                            caughtUpCards.append(card)
                            continue
            if card.odid or card.queue == -1:
                continue
            if len(str(card.due)) > 6:
                when = self.getDueDateFromTimestamp(card.due)
            else:
                when = card.due - self.today 
            if when > 365:
                continue
            if onlyMaintainEase:
                card.factor = 2500
                card.flush()
                continue
            lastReps = self.getLastReps(card.id)
            ease = False
            if lastReps:
                ease = lastReps[0][1]
            self.reRep(card, ease, lastReps)
        self.mw.miSickSched.rescheduleCaughtUpCards(caughtUpCards)
        self.mw.miSickSched.saveSickIds()
        self.initScheduler()
        self.mw.reset()

    def formatRestdays(self, setting):
        restdays = []
        for i in range(0,7):
            if not setting[i]:
                restdays.append(i)
        return restdays

    def grabLearning(self):
        return list(self.mw.col.find_cards('is:learn', order= '  c.reps  '))

    def grabReviews(self):
        return list(self.mw.col.find_cards('is:review', order= ' c.ivl '))


    def getCurrentSched(self):
        self.today = self.getToday()
        learningReviewing = list(set(self.grabLearning() + self.grabReviews()))
        currentSched = {}
        firstDue = False
        for cid in learningReviewing:
            card = self.mw.col.getCard(cid)
                
            if card.odid or card.queue == -1: 
                continue
            if card.queue == 1: 
                cdue =  int(((card.due) - self.scheduler.col.crt) // 86400)
            else:
                cdue = int(card.due)
            cdue = cdue - self.today
            due = str(cdue)
            if due in currentSched:
                currentSched[due] += 1
            else:
                currentSched[due] = 1
            if firstDue is False or cdue < firstDue:
                firstDue = cdue

        return self.organizeDueDates(firstDue, currentSched), firstDue;

    def organizeDueDates(self, firstDue, schedule):
        newSched = []
        count = firstDue
        while len(schedule) > 0:
            key = str(count)
            if key in schedule:
                newSched.append([count, schedule[key]])
                del schedule[key]
            else:
                newSched.append([count, 0])
            count += 1

        return newSched
       
    def getMinMaxDue(self, minv, maxv, reviewDate):
        minDue = reviewDate + minv
        maxDue = reviewDate + maxv
        return minDue, maxDue

    def getProgressBar(self):
        progressWidget = QWidget(None)
        textDisplay = QLabel()
        progressWidget.setWindowFlag(Qt.WindowCloseButtonHint, False)
        progressWidget.setWindowIcon(QIcon(join(self.path, 'icons', 'migaku.png')))
        progressWidget.setWindowTitle("Rescheduling Cards...")
        textDisplay.setText("Loading... ")
        progressWidget.setFixedSize(500, 100)
        progressWidget.setWindowModality(Qt.ApplicationModal)
        bar = QProgressBar(progressWidget)
        layout = QVBoxLayout()
        layout.addWidget(textDisplay)
        layout.addWidget(bar)
        progressWidget.setLayout(layout) 
        bar.move(10,10)
        per = QLabel(bar)
        per.setAlignment(Qt.AlignCenter)
        progressWidget.show()
        progressWidget.setFocus()
        return progressWidget, bar, textDisplay;



