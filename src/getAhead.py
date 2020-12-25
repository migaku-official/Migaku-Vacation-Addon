# -*- coding: utf-8 -*-
# 
from aqt.qt import *
from os.path import dirname, join, exists
from .miutils import miInfo, miAsk
import time


class GetAhead(QWidget):

    def __init__(self, mw, path, find):
        super(GetAhead, self).__init__()
        self.mw = mw
        self.path = path
        self.cids = []
        self.find = find
        self.cardsDay = 0
        self.today = False
        self.tomorrowMessage = 'There are %s review cards due tomorrow with an interval greater than 1 day.'
        self.otherDayMessage = 'You have no review cards due %s, but there are %s review cards with an interval greater than 1 day due in %s days.'
        self.setWindowTitle("Get Ahead")
        self.setWindowIcon(QIcon(join(self.path, 'icons', 'migaku.png')))
        self.setWindowModality(Qt.ApplicationModal)
        self.totalCards = QLabel('')
        self.howManyCards = QSpinBox()
        self.howManyCards.setMinimum(1)
        self.cancelButton = QPushButton('Cancel')
        self.confirmButton = QPushButton('Confirm')
        self.setupLayout()
        self.initHandlers()

    def grabDueNext(self, deck, days = '1'):
        return self.find.Finder(self.mw.col).findCards('"deck:' + deck + '" "is:duenext'+ days + '"', order= '  c.ivl  ')

    ###set the maximum cards to the number of cards due tomorrow
    def initHandlers(self):
        self.cancelButton.clicked.connect(self.hide)
        self.confirmButton.clicked.connect(self.scheduleToday)

    def setupLayout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.totalCards)

        hlays = QHBoxLayout()
        hlays.addWidget(QLabel('How many cards of these cards would you like to study today?'))
        self.howManyCards.setFixedWidth(120)
        hlays.addWidget(self.howManyCards)
        hlays.addStretch()
        self.layout.addLayout(hlays)

        hlay3 = QHBoxLayout()
        hlay3.addStretch()
        hlay3.addWidget(self.cancelButton)
        hlay3.addWidget(self.confirmButton)
        self.layout.addLayout(hlay3)
        self.setLayout(self.layout)

    def noneDue(self):
        if len(self.cids) == 0:
            return True
        return False


    def displayDueTomorrow(self, due):
        self.totalCards.setText(self.tomorrowMessage%due)

    def displayDueLater(self, count, due):
        if count == 2:
            message = 'tomorrow'
        else:
            message = 'in the next %s days'%str(count-1)
        self.totalCards.setText(self.otherDayMessage%(message, due, str(count)))

    def setMinMaxCards(self, due):
        self.howManyCards.setMaximum(due)
        if due > 10:
            self.howManyCards.setValue(10)
        else:
            self.howManyCards.setValue(due)

    def cardsStillDue(self, deck):
        return len(self.find.Finder(self.mw.col).findCards('"deck:' + deck + '" "is:due"')) > 0

    def openGetAhead(self):
        deck = self.mw.col.decks.current()['name']
        self.today = int((time.time() - self.mw.col.crt) // 86400)
        if self.cardsStillDue(deck):
            miInfo('To use the Get Ahead feature you must first complete all of today\'s reviews for this deck.')
            return
        self.cids = self.grabDueNext(deck)
        if self.noneDue():
            count = 2
            while True:
                self.cids = self.grabDueNext(self.mw.col.decks.current()['name'], str(count))
                if not self.noneDue():
                    break
                count+= 1
                if count == 15:
                    miInfo('You have no valid review cards due within the next 2 weeks.')
                    return
            due = len(self.cids)
            self.displayDueLater(count, str(due))
        else:
            due = len(self.cids)
            self.displayDueTomorrow(str(due))
        self.setMinMaxCards(due)
        self.show()
        return

    def scheduleToday(self):
        self.mw.checkpoint('Get Ahead')
        howMany = self.howManyCards.value()
        self.cids.reverse()
        for cid in self.cids[:howMany]:
            card = self.mw.col.getCard(cid)
            difference = card.due - self.today
            ivl = card.ivl - difference
            if ivl < 1:
                ivl = 1
            card.ivl = ivl
            card.due = self.today
            card.flush()
        self.mw.reset()
        self.hide()