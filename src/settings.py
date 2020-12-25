# -*- coding: utf-8 -*-
# 
# 
import json
import sys
from aqt.qt import *
from aqt.utils import openLink, tooltip
from anki.utils import isMac, isWin, isLin
import re
import os
from os.path import dirname, join
from .miutils import miInfo, miAsk


verNumber = "1.2.0"

class MigakuSVG(QSvgWidget):
    clicked=pyqtSignal()
    def __init__(self, parent=None):
        QSvgWidget.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()

class MigakuLabel(QLabel):
    clicked=pyqtSignal()
    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()

class VacationSettings(QTabWidget):
    def __init__(self, mw, path, reboot):
        super(VacationSettings, self).__init__()
        self.mw = mw
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setWindowTitle("Migaku Vacation Settings (Ver. " + verNumber + ")")
        self.addonPath = path
        self.setWindowIcon(QIcon(join(self.addonPath, 'icons', 'migaku.png')))
        self.onceDaily = QCheckBox()
        self.profLevel = QRadioButton('Profile Level')
        self.deckLevel = QRadioButton('Deck Level')
        self.noOptimize = QRadioButton('Off')
        self.maintainEase = QCheckBox()
        self.resetButton = QPushButton('Restore Defaults')
        self.cancelButton = QPushButton('Cancel')
        self.applyButton = QPushButton('Apply')
        self.settingsTab = QWidget(self)
        self.setupLayout()
        self.addTab(self.settingsTab, "Settings")
        self.addTab(self.getAboutTab(), "About")
        self.initHandlers()
        self.initTooltips()
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)
        self.reboot = reboot
        self.openSettings()

    def initTooltips(self):
        self.onceDaily.setToolTip('If checked, the rescheduling algorithm will be run once daily on\nAnki start-up for each of your profiles.')
        self.profLevel.setToolTip('If checked, the rescheduling algorithm will balance reviews to avoid\nmajor discrepencies in daily review count. This will happen at the collection level\nassuring the most balanced total review count.')
        self.deckLevel.setToolTip('If checked, the rescheduling algorithm will balance reviews to avoid\nmajor discrepencies in daily review count. This will happen at the deck level\nassuring the most balanced rep count for each individual deck.')
        self.noOptimize.setToolTip('If checked, cards\'s intervals will only be adjusted if they conflict\nwith your review schedule or vacation schedule.')
        self.maintainEase.setToolTip('If checked, the ease of all cards will be maintained at 250%(the default starting\nease). This eliminates the need of the Reset Ease add-on.')

    def openSettings(self):
        self.loadConfig()
        self.show()

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)
        
    def loadConfig(self):
        config = self.getConfig()
        self.onceDaily.setChecked(config['runDaily'])
        opt = config['optimizeSchedule']
        if opt == 0:
            self.noOptimize.setChecked(True)
        elif opt == 1:
            self.deckLevel.setChecked(True)
        else:
            self.profLevel.setChecked(True)
        self.maintainEase.setChecked(config['maintainEase'])

    def resetConfig(self):
        if miAsk('Are you sure you would like to restore the default settings? This will erase all of your currently scheduled vacations for all profiles and cannot be undone. Currently rescheduled sick day cards and weekly schedules will not be affected'):
            conf = self.mw.addonManager.addonConfigDefaults(dirname(__file__))
            self.mw.addonManager.writeConfig(__name__, conf)
            self.close()
            self.mw.miVacSettings = None
            self.reboot()

    def repairFails(self):
        if miAsk('##ONLY RUN THIS PROCESS ONCE EVER##\nA previous version of the add-on caused an issue which causeD failed cards to have a progressively larger intervals.'+
            ' This utility can restore those cards to proper intervals. If you are currently using the Migaku Retirement add-on, any' +
            ' repaired cards in your Retirement Deck will be unsuspended. Be aware that this may lead to a backup of cards. Would you like to continue?'):
            if miAsk('Would you like to also add the "repairedFail" tag to the cards that are repaired?'):
                self.mw.MigakuRescheduler.repairFails(True)
            else:
                self.mw.MigakuRescheduler.repairFails(False)

    def initHandlers(self):
        self.resetButton.clicked.connect(self.resetConfig)
        self.cancelButton.clicked.connect(self.hide)
        self.applyButton.clicked.connect(self.saveConfig)


    def saveConfig(self):
        nc = self.getConfig()
        nc['runDaily'] = self.onceDaily.isChecked()
        if self.deckLevel.isChecked():
            nc['optimizeSchedule'] = 1
        elif self.profLevel.isChecked():
            nc['optimizeSchedule'] = 2
        else:
            nc['optimizeSchedule'] = 0
        nc['maintainEase'] = self.maintainEase.isChecked()
        self.mw.addonManager.writeConfig(__name__, nc)
        self.hide()
        
    def miQLabel(self, text, width):
        label = QLabel(text)
        label.setFixedHeight(30)
        label.setFixedWidth(width)
        return label

    def setupLayout(self):

        self.layout = QVBoxLayout()

        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(QLabel('Run schedule optimization once daily on profile load:'))
        settingsLayout.addWidget(self.onceDaily)
        settingsLayout.addStretch()

        optimizeLay = QHBoxLayout()
        optimizeLay.addWidget(QLabel('Balance daily review count:'))
        optimizeLay.addWidget(self.noOptimize)
        optimizeLay.addWidget(self.deckLevel)
        optimizeLay.addWidget(self.profLevel)
        optimizeLay.addStretch()

        easeLay = QHBoxLayout()
        easeLay.addWidget(QLabel('Maintain ease at 250%:'))
        easeLay.addWidget(self.maintainEase)
        easeLay.addStretch()
        
        self.layout.addLayout(settingsLayout)
        self.layout.addLayout(optimizeLay)
        self.layout.addLayout(easeLay)
        self.layout.addStretch()

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.resetButton)
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.cancelButton)
        buttonsLayout.addWidget(self.applyButton)

        self.layout.addLayout(buttonsLayout)
        self.settingsTab.setLayout(self.layout)


    def getSVGWidget(self,  name):
        widget = MigakuSVG(join(self.addonPath, 'icons', name))
        widget.setFixedSize(27,27)
        return widget

    def getAboutTab(self):
        tab_4 = QWidget()
        tab_4.setObjectName("tab_4")
        tab4vl = QVBoxLayout()
        migakuAbout = QGroupBox()
        migakuAbout.setTitle('Migaku')
        migakuAboutVL = QVBoxLayout()

        migakuAbout.setStyleSheet("QGroupBox { font-weight: bold; } ")
        migakuAboutText = QLabel("This an original Migaku add-on. Migaku seeks to be a comprehensive platform for acquiring foreign languages. The official Migaku website will be published soon!")
        migakuAboutText.setWordWrap(True);
        migakuAboutText.setOpenExternalLinks(True);
        migakuAbout.setLayout(migakuAboutVL)
        migakuAboutLinksTitle = QLabel("<b>Links<b>")
 
        migakuAboutLinksHL3 = QHBoxLayout()


        migakuInfo = QLabel("Migaku:")
        migakuInfoYT = self.getSVGWidget('Youtube.svg')
        migakuInfoYT.setCursor(QCursor(Qt.PointingHandCursor))

        migakuInfoTW = self.getSVGWidget('Twitter.svg')
        migakuInfoTW.setCursor(QCursor(Qt.PointingHandCursor))


        migakuPatreonIcon = self.getSVGWidget('Patreon.svg')
        migakuPatreonIcon.setCursor(QCursor(Qt.PointingHandCursor))
        migakuAboutLinksHL3.addWidget(migakuInfo)
        migakuAboutLinksHL3.addWidget(migakuInfoYT)
        migakuAboutLinksHL3.addWidget(migakuInfoTW)
        migakuAboutLinksHL3.addWidget(migakuPatreonIcon)
        migakuAboutLinksHL3.addStretch()

        migakuAboutVL.addWidget(migakuAboutText)
        migakuAboutVL.addWidget(migakuAboutLinksTitle)
        migakuAboutVL.addLayout(migakuAboutLinksHL3)
        
        migakuContact = QGroupBox()
        migakuContact.setTitle('Contact Us')
        migakuContactVL = QVBoxLayout()
        migakuContact.setStyleSheet("QGroupBox { font-weight: bold; } ")
        migakuContactText = QLabel("If you would like to report a bug or contribute to the add-on, the best way to do so is by starting a ticket or pull request on GitHub. If you are looking for personal assistance using the add-on, check out the Migaku Patreon Discord Server.")
        migakuContactText.setWordWrap(True)

        gitHubIcon = self.getSVGWidget('Github.svg')
        gitHubIcon.setCursor(QCursor(Qt.PointingHandCursor))
        
        migakuThanks = QGroupBox()
        migakuThanks.setTitle('A Word of Thanks')
        migakuThanksVL = QVBoxLayout()
        migakuThanks.setStyleSheet("QGroupBox { font-weight: bold; } ")
        migakuThanksText = QLabel("Thanks so much to all Migaku supporters! I would not have been able to develop this add-on or any other Migaku project without your support!")
        migakuThanksText.setOpenExternalLinks(True);
        migakuThanksText.setWordWrap(True);
        migakuThanksVL.addWidget(migakuThanksText)

        migakuContactVL.addWidget(migakuContactText)
        migakuContactVL.addWidget(gitHubIcon)
        migakuContact.setLayout(migakuContactVL)
        migakuThanks.setLayout(migakuThanksVL)
        tab4vl.addWidget(migakuAbout)
        tab4vl.addWidget(migakuContact)
        tab4vl.addWidget(migakuThanks)
        tab4vl.addStretch()
        tab_4.setLayout(tab4vl)

        migakuPatreonIcon.clicked.connect(lambda: openLink('https://www.patreon.com/Migaku'))
        migakuInfoYT.clicked.connect(lambda: openLink('https://www.youtube.com/c/ImmerseWithYoga'))
        migakuInfoTW.clicked.connect(lambda: openLink('https://twitter.com/Migaku_Yoga'))
        gitHubIcon.clicked.connect(lambda: openLink('https://github.com/migaku-official'))
        return tab_4

