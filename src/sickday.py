# -*- coding: utf-8 -*-
# 
from aqt.qt import *
from os.path import dirname, join, exists
from aqt.utils import showInfo
from .miutils import miInfo, miAsk
from . import Pyperclip
import math
from datetime import date
import time
import codecs
import json

class SickScheduler(QWidget):

    def __init__(self, mw, path, find, rescheduler):
        super(SickScheduler, self).__init__()
        self.mw = mw
        self.path = path
        self.cards = False
        self.cardsDay = 0
        self.rescheduler = rescheduler
        self.setWindowTitle("Setup a Catch Up Schedule")
        self.setWindowIcon(QIcon(join(self.path, 'icons', 'migaku.png')))
        self.setWindowModality(Qt.ApplicationModal)
        self.totalCards = QLabel('')
        self.scheduleToday = QCheckBox()
        self.scheduleToday.setToolTip('If checked, cards will be rescheduled starting today.\nIf unchecked, cards will be rescheduled starting tomorrow.')
        self.howManyDays = QSpinBox()
        self.howManyDays.setMinimum(1)
        self.howManyDays.setMaximum(1000)
        self.howManyDays.setValue(10)
        self.cancelButton = QPushButton('Cancel')
        self.confirmButton = QPushButton('Confirm')
        self.cardsPerDay = QLabel('')
        self.resize(400,150)
        self.setupLayout()
        self.initHandlers()
        self.find = find
        self.sickIds = {}
        self.idsToRemove = []
        self.idsToReturn = []

    def clearReturnIds(self, *args):
        self.idsToReturn = []

    def attemptReturnSickIds(self,col):
        if len(self.idsToReturn) > 0:
            self.returnSickIds()
            self.idsToReturn = []

    def returnSickIds(self):
        for entry in self.idsToReturn:
            self.sickIds[entry[0]] = entry[1]
        self.saveSickIds()

    def removeSickIdsByCid(self, col, cids, notes=True):
        edited = False
        for cid in cids:
            strid = str(cid)
            if strid in self.sickIds:
                edited = True
                self.idsToReturn.append([strid, self.sickIds[strid]])
                del self.sickIds[strid]
        if edited: 
            self.saveSickIds()

    def removeMissingSickIds(self, cids):
        self.sickIds = {str(c): self.sickIds[str(c)] for c in cids if str(c) in self.sickIds}


    def updateSickIds(self):
        self.idsToRemove = []
        self.idsToReturn = []
        self.sickIds = self.getSickIds()

    def saveSickIds(self):
        fileName = join(self.mw.col.media.dir(),   '_MigakuSickDayIds.json')
        with open(fileName, 'w') as outfile:
            json.dump(self.sickIds, outfile, ensure_ascii=False)


    def loadFromJSON(self, fileName):
        with codecs.open(fileName, "r", "utf-8") as listFile:
            return json.load(listFile)
       

    def getSickIds(self): 
        fileName = join(self.mw.col.media.dir()  , '_MigakuSickDayIds.json')
        if exists(fileName): 
            return self.loadFromJSON(fileName)
        else:
            return {}
    
    def removeSickIds(self):
        for sickId in self.idsToRemove:
            try:
                del self.sickIds[sickId]
            except:
                continue
        self.idsToRemove = []
        self.saveSickIds()  

    def promptCatchUpRemoval(self, *args):
        cards = len(self.sickIds)
        if cards > 0:
            strcards = str(cards)
            if miAsk('This profile currently has '+ strcards +' cards in the catch up queue. Would you like to clear the catch up queue?\n\nThe catch up queue is the list of cards that have been rescheduled by the Catch Up feature. Migaku Vacation keeps track of these cards so that it can avoid subsequently changing their schedule when “Optimize Schedule” is run.\n\nIf the collection you’re loading is a back-up of the previously loaded collection, clearing the catch up queue will result in cards that had previously been rescheduled by the Catch Up feature being treated as normal cards. Because these cards were originally overdue, if treated as normal cards, they will pile up around the current day when “Optimize Schedule” is run. This could potentially lead to a significantly increased review count in the short term.\n\nFor this reason, if the collection you’re loading is a back-up of the previously loaded collection, you most likely will not want to clear the catch up queue. '):
                if miAsk('Are you absolutely sure you would like to clear the current catch up queue?\n\nThe catch up queue is the list of cards that have been rescheduled by the Catch Up feature. Migaku Vacation keeps track of these cards so that it can avoid subsequently changing their schedule when “Optimize Schedule” is run.\n\nIf the collection you’re loading is a back-up of the previously loaded collection, clearing the catch up queue will result in cards that had previously been rescheduled by the Catch Up feature being treated as normal cards. Because these cards were originally overdue, if treated as normal cards, they will pile up around the current day when “Optimize Schedule” is run. This could potentially lead to a significantly increased review count in the short term.\n\nFor this reason, if the collection you’re loading is a back-up of the previously loaded collection, you most likely will not want to clear the catch up queue. '):
                    self.removeProfSickIds()

    def removeProfSickIds(self):
        self.sickIds = {}
        self.saveSickIds()  

    def setupLayout(self):
        self.layout = QVBoxLayout()
        hlay1 = QHBoxLayout()
        hlay1.addWidget(QLabel('Reschedule cards over:'))
        hlay1.addWidget(self.howManyDays)
        hlay1.addWidget(QLabel('day(s)'))
        hlay1.addStretch()
        self.layout.addLayout(hlay1)

        hlays = QHBoxLayout()
        hlays.addWidget(QLabel('Schedule cards today:'))
        hlays.addWidget(self.scheduleToday)
        hlays.addStretch()
        self.layout.addLayout(hlays)

        hlayt = QHBoxLayout()
        hlayt.addWidget(self.totalCards)
        self.layout.addLayout(hlayt)

        hlay2 = QHBoxLayout()
        hlay2.addWidget(self.cardsPerDay)
        self.layout.addLayout(hlay2)

        hlay3 = QHBoxLayout()
        hlay3.addStretch()
        hlay3.addWidget(self.cancelButton)
        hlay3.addWidget(self.confirmButton)
        self.layout.addLayout(hlay3)
        self.setLayout(self.layout)

    def initHandlers(self):
        self.howManyDays.valueChanged.connect(self.updateCardsPerDay)
        self.cancelButton.clicked.connect(self.hide)
        self.confirmButton.clicked.connect(self.catchup)

    def sickDayPrompt(self, deck=False):
        detail = ' for all decks'
        if deck:
            detail = ' for the "'+ deck + '" deck'  
        howMany = len(self.grabDue(deck))
        if howMany < 1:
            miInfo('You currently have no cards due' + detail + '. Sicks days are only applicable when there are cards due.')
            return
        if miAsk("This will move all reviews"+ detail + " back by one day and then reoptimize the scheduling. Are you sure you would like to take a sick day?"):
            self.mw.checkpoint('Sick Day')
            cids = list(set(self.grabLearning(deck) + self.grabReviews(deck)))
            total = len(cids)
            strTotal = str(total)
            count = 0
            progressWidget, bar, message = self.getProgressBar()
            bar.setMinimum(0)
            bar.setMaximum(total)
            for cid in cids:
                count += 1
                if count % 100 == 0:
                    bar.setValue(count)
                    message.setText('Rescheduling Card ' +  str(count)  + '/' + strTotal + '...')
                    self.mw.app.processEvents()
                card = self.mw.col.getCard(cid)

                if card.odid or card.queue == -1:
                    continue
                if card.type == 1 and card.queue != 3:
                    card.due += 86400
                elif len(str(int(card.due))) > 6:
                    card.due += 86400
                else: 
                    self.adjustLastRep(card)
                    card.due += 1
                card.flush()
            self.rescheduler.loopCol(sickDay = True)
            self.mw.reset()

    def adjustLastRep(self, card):
        try:
            rep  = self.mw.col.db.all('select id, cid, usn, ease, ivl, lastIvl, factor, time, type from revlog where cid = %s order by id desc limit 1'%str(card.id))[0]
            self.mw.col.db.execute('delete from revlog where id = ?', rep[0])
            added = False
            rid = rep[0] + 86400000
            while not added:
                try:
                    self.mw.col.db.execute("insert into revlog values (?,?,?,?,?,?,?,?,?)", rid, rep[1], rep[2], rep[3], rep[4], rep[5], rep[6], rep[7], rep[8])
                    added = True
                except:
                    rid += 1
                    continue
        except:
            return

    def getProgressBar(self):
            progressWidget = QWidget(None)
            textDisplay = QLabel()
            progressWidget.setWindowFlag(Qt.WindowCloseButtonHint, False)
            progressWidget.setWindowIcon(QIcon(join(self.path, 'icons', 'migaku.png')))
            progressWidget.setWindowTitle("Applying Sick Day...")
            textDisplay.setText("Processing... ")
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
               
      
    def grabLearning(self, deck = False):
        if not deck:
            return self.find.Finder(self.mw.col).findCards('is:learn', order= '  c.reps  ')
        else:
            return self.find.Finder(self.mw.col).findCards('"deck:' + deck + '" "is:learn"', order= '  c.reps  ')

    def grabReviews(self,  deck = False):
        if not deck:
            return self.find.Finder(self.mw.col).findCards('is:review', order= ' c.ivl ')
        else:
            return self.find.Finder(self.mw.col).findCards('"deck:' + deck + '" "is:review"', order= ' c.ivl ')

    def breakByDays(self, a, n = 3):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))
       
    def catchup(self):
        self.mw.checkpoint('Catch Up Scheduler')
        first = int((time.time() - self.mw.col.crt) // 86400)
        totalDays = self.howManyDays.value()
        days = 0
        scheduled = 0
        adjust = 0
        self.idsToRemove = []
        if not self.scheduleToday.isChecked():
            first += 1
            adjust = 1
        for cid in self.cards:
            card = self.mw.col.getCard(cid)
            if card.odid:
                continue
            while True:
                potential = first + days
                if potential not in self.rescheduler.restCalendar[str(card.did)]:
                    break
                days += 1
            scheduled += 1
            if card.queue == 1 or card.ivl < 0:
                card.due = int(time.time() + ((days + adjust) * 86400))
            else:
                oldivl = card.ivl
                card.ivl = card.ivl + ((first + days - card.due)/2)
                card.due = first + days
                
                
                lastrep = self.mw.col.db.scalar('select id from revlog where cid = %s order by id desc limit 1'%str(card.id))
                self.mw.col.db.execute('update revlog set ivl = ? where id = ?', card.ivl, lastrep)
            self.sickIds[str(card.id)] = [card.reps, card.note().guid]
            self.idsToRemove.append(str(card.id))
            card.flush()
            if scheduled == self.cardsDay:
                days+= 1
                scheduled = 0
        self.mw.reset()
        self.saveSickIds()
        self.hide()

    
    def getFirstDay(self, cardsPerDay):
        cardsPerDay.sort() 
        return cardsPerDay[0]

    def getProgressBar(self):
        progressWidget = QWidget(None)
        textDisplay = QLabel()
        progressWidget.setWindowFlag(Qt.WindowCloseButtonHint, False)
        progressWidget.setWindowIcon(QIcon(join(self.path, 'icons', 'migaku.png')))
        progressWidget.setWindowTitle("Rescheduling Cards in Catch Up Queue...")
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

    def getDueDateFromTimestamp(self, ts):
        return int(((ts) - self.rescheduler.scheduler.col.crt) // 86400)

    def rescheduleCaughtUpCards(self, cards):
        total = len(cards)
        if total == 0:
            return
        previousBoosts = 0
        cardsPerDay = []
        for idx, card in enumerate(cards):
            if len(str(int(card.due))) > 6:
                dueDate = (self.getDueDateFromTimestamp(card.due))
            else:
                dueDate = card.due
            cards[idx].dueDate = dueDate
            dueDateStr = str(dueDate)
            if dueDateStr not in cardsPerDay:
                cardsPerDay.append(dueDate)
        cards.sort(key=lambda x: x.dueDate)
        tomorrow = int((time.time() - self.mw.col.crt) // 86400) + 1
        first = self.getFirstDay(cardsPerDay)
        if tomorrow < first:
            first = tomorrow
        currentDueDate = False
        days = 0
        progressWidget, bar, message = self.getProgressBar()
        strTotal = str(total)
        divisor = 100
        sickIds = self.mw.miSickSched.sickIds
        if total > 10000:
            divisor = 200
        bar.setMaximum((total))
        bar.setMinimum(0)
        cardCount = 0
        for card in cards:
            cardCount += 1
            if cardCount % divisor == 0:
                bar.setValue(cardCount)
                message.setText('Rescheduling Cards ' +  str(cardCount)  + '/' + strTotal + '...')
                self.mw.app.processEvents()
            if currentDueDate is False:
                currentDueDate = card.dueDate
            elif currentDueDate != card.dueDate:
                currentDueDate = card.dueDate
                days += 1
            while True:
                potential = first + days
                if potential not in self.rescheduler.restCalendar[str(card.did)]:
                    break
                days += 1

            if card.queue == 1 or card.ivl < 0:
                card.due = int(time.time() + (days * 86400))
            else:
                card.due = first + days
            card.flush()



    def updateTotal(self):
        self.totalCards.setText(str(len(self.cards)) + ' total cards to be rescheduled.')

    def updateCardsPerDay(self):
        cardsDay = round(len(self.cards)/self.howManyDays.value(),1)
        self.cardsPerDay.setText('Average of ' + str(cardsDay) + ' cards added per day.')
        self.cardsDay = math.ceil(cardsDay)

    def openWithDeck(self):
        self.openScheduler(self.mw.col.decks.current()['name']) 

    def sickdayWithDeck(self):
        self.sickDayPrompt(self.mw.col.decks.current()['name']) 

    def openScheduler(self, deck = False):
        self.cards = self.grabDue(deck)
        howMany = len(self.cards)
        if howMany < 1:
            detail = ' for all decks'
            if deck:
                detail = ' for the "'+ deck + '" deck' 
            miInfo('You currently have no cards due' + detail + '. Catch up functionality is only available when there are cards due.')
            return
        self.updateTotal()
        self.updateCardsPerDay()
        self.show()
    
    def grabDue(self, deck):
        if not deck:
            return self.find.Finder(self.mw.col).findCards('is:due', order= ' c.ivl ')
        else:
            return self.find.Finder(self.mw.col).findCards('"deck:' + deck + '" "is:due"', order= ' c.ivl ')

