#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017

@author: MrFlamez
'''

from src.Spieler import Spieler, Login
from src.HTTPCommunication import HTTPConnection
from src.Messenger import Messenger
from src.Garten import Garden, AquaGarden
from src.Bienen import Honig
from src.Lager import Storage
from src.Marktplatz import Marketplace
from src.Produktdaten import ProductData
from collections import Counter
from src.Wimps import Wimps
from src.Quests import Quest
from src.Bonus import Bonus
from src.Note import Note
import logging, i18n, datetime

i18n.load_path.append('lang')


class WurzelBot(object):
    """
    Die Klasse WurzelBot übernimmt jegliche Koordination aller anstehenden Aufgaben.
    """

    def __init__(self):
        """
        
        """
        self.__logBot = logging.getLogger("bot")
        self.__logBot.setLevel(logging.DEBUG)
        self.__HTTPConn = HTTPConnection()
        self.productData = ProductData(self.__HTTPConn)
        self.spieler = Spieler()
        self.messenger = Messenger(self.__HTTPConn)
        self.storage = Storage(self.__HTTPConn)
        self.garten = []
        self.wassergarten = None
        self.bienenfarm = Honig(self.__HTTPConn)
        self.marktplatz = Marketplace(self.__HTTPConn)
        self.wimparea = Wimps(self.__HTTPConn)
        self.quest = Quest(self.__HTTPConn, self.spieler)
        self.bonus = Bonus(self.__HTTPConn, self.spieler)
        self.note = Note(self.__HTTPConn)

    def __initGardens(self):
        """
        Ermittelt die Anzahl der Gärten und initialisiert alle.
        """
        try:
            tmpNumberOfGardens = self.__HTTPConn.getInfoFromStats("Gardens")
            self.spieler.numberOfGardens = tmpNumberOfGardens
            for i in range(1, tmpNumberOfGardens + 1):
                self.garten.append(Garden(self.__HTTPConn, i))
            
            if self.spieler.isAquaGardenAvailable() is True:
                self.wassergarten = AquaGarden(self.__HTTPConn)

            # See my remarks in launchBot() method
            # if self.spieler.isHoneyFarmAvailable() is True:
            # self.bienenfarm = Honig(self.__HTTPConn)

        except:
            raise


    def __getAllFieldIDsFromFieldIDAndSizeAsString(self, fieldID, sx, sy):
        """
        Rechnet anhand der fieldID und Größe der Pflanze (sx, sy) alle IDs aus und gibt diese als String zurück.
        """
        if (sx == '1' and sy == '1'): return str(fieldID)
        if (sx == '2' and sy == '1'): return str(fieldID) + ',' + str(fieldID + 1)
        if (sx == '1' and sy == '2'): return str(fieldID) + ',' + str(fieldID + 17)
        if (sx == '2' and sy == '2'): return str(fieldID) + ',' + str(fieldID + 1) + ',' + str(fieldID + 17) + ',' + str(fieldID + 18)
        self.__logBot.debug(f'Error der plantSize --> sx: {sx} sy: {sy}')


    def __getAllFieldIDsFromFieldIDAndSizeAsIntList(self, fieldID, sx, sy):
        """
        Rechnet anhand der fieldID und Größe der Pflanze (sx, sy) alle IDs aus und gibt diese als Integer-Liste zurück.
        """
        sFields = self.__getAllFieldIDsFromFieldIDAndSizeAsString(fieldID, sx, sy)
        listFields = sFields.split(',') #Stringarray
                        
        for i in range(0, len(listFields)):
            listFields[i] = int(listFields[i])
            
        return listFields


    def launchBot(self, server, user, pw, lang, portalacc) -> bool:
        """
        Diese Methode startet und initialisiert den Wurzelbot. Dazu wird ein Login mit den
        übergebenen Logindaten durchgeführt und alles nötige initialisiert.
        """
        self.__logBot.info('-------------------------------------------')
        self.__logBot.info(f'Starting Wurzelbot for User {user} on Server No. {server}')
        loginDaten = Login(server=server, user=user, password=pw, language=lang)

        if portalacc == True:
            try:
                self.__HTTPConn.logInPortal(loginDaten)
            except:
                self.__logBot.error(i18n.t('wimpb.error_starting_wbot'))
                return False
        else:
            try:
                self.__HTTPConn.logIn(loginDaten)
            except:
                self.__logBot.error(i18n.t('wimpb.error_starting_wbot'))
                return False

        try:
            self.spieler.setUserNameFromServer(self.__HTTPConn)
        except:
            self.__logBot.error(i18n.t('wimpb.username_not_determined'))
            return False

        try:
            self.spieler.setUserDataFromServer(self.__HTTPConn)
        except:
            self.__logBot.error(i18n.t('wimpb.error_refresh_userdata'))
            return False
        
        # The question leaves open as there is a bonus using in HoneyFarm availability
        # which is not available itself after HoneyFarm buying.
        # my version is below
        try:
            tmpHoneyFarmAvailability = self.bienenfarm.setHoneyFarmAvailability()
        except:
            self.__logBot.error(i18n.t('wimpb.error_no_beehives'))
            return False
        else:
            self.spieler.setHoneyFarmAvailability(tmpHoneyFarmAvailability)

        try:
            tmpAquaGardenAvailability = self.__HTTPConn.isAquaGardenAvailable(self.spieler.getLevelNr())
        except:
            self.__logBot.error(i18n.t('wimpb.error_no_water_garden'))
            return False
        else:
            self.spieler.setAquaGardenAvailability(tmpAquaGardenAvailability)

        try:
            self.__initGardens()
        except:
            self.__logBot.error(i18n.t('wimpb.error_number_of_gardens'))
            return False

        self.spieler.accountLogin = loginDaten
        self.spieler.setUserID(self.__HTTPConn.getUserID())
        self.productData.initAllProducts()
        self.storage.initProductList(self.productData.getListOfAllProductIDs())
        self.storage.updateNumberInStock()
        return True


    def exitBot(self):
        """
        Diese Methode beendet den Wurzelbot geordnet und setzt alles zurück.
        """
        self.__logBot.info(i18n.t('wimpb.exit_wbot'))
        try:
            self.__HTTPConn.logOut()
        except:
            self.__logBot.error(i18n.t('wimpb.exit_wbot_abnormal'))
        else:
            self.__logBot.info(i18n.t('wimpb.logout_success'))
            self.__logBot.info('-------------------------------------------')


    def updateUserData(self):
        """
        Ermittelt die Userdaten und setzt sie in der Spielerklasse.
        """
        try:
            userData = self.__HTTPConn.readUserDataFromServer()
        except:
            self.__logBot.error(i18n.t('wimpb.error_refresh_userdata'))
        else:
            self.spieler.userData = userData


    def waterPlantsInAllGardens(self):
        """
        Alle Gärten des Spielers werden komplett bewässert.
        """
        for garden in self.garten:
            garden.waterPlants()
        
        if self.spieler.isAquaGardenAvailable():
            pass
            #self.waterPlantsInAquaGarden()


    def writeMessagesIfMailIsConfirmed(self, recipients, subject, body):
        """
        Erstellt eine neue Nachricht, füllt diese aus und verschickt sie.
        recipients muss ein Array sein!.
        Eine Nachricht kann nur verschickt werden, wenn die E-Mail Adresse bestätigt ist.
        """
        if (self.spieler.isEMailAdressConfirmed()):
            try:
                self.messenger.writeMessage(self.spieler.getUserName(), recipients, subject, body)
            except:
                self.__logBot.error(i18n.t('wimpb.no_message'))
            else:
                pass

    def getEmptyFieldsOfGardens(self):
        """
        Returns all empty fields of all normal gardens.
        Can be used to decide how many crops to grow.
        """
        emptyFields = []
        try:
            for garden in self.garten:
                emptyFields.append(garden.getEmptyFields())
        except:
            self.__logBot.error(f'Could not determinate empty fields from garden {garden.getID()}.')
        else:
            pass
        return emptyFields

    def getGrowingPlantsInGardens(self):
        growingPlants = Counter()
        try:
            for garden in self.garten:
                growingPlants.update(garden.getGrowingPlants())
        except:
            self.__logBot.error('Could not determine growing plants of garden ' + str(garden.getID()) + '.')
        else:
            pass

        return dict(growingPlants)

    def getAllWimpsProducts(self):
        allWimpsProducts = Counter()
        for garden in self.garten:
            tmpWimpData = self.wimparea.getWimpsData(garden)
            for products in tmpWimpData.values():
                allWimpsProducts.update(products[1])

        return dict(allWimpsProducts)

    def sellWimpsProducts(self, minimal_balance, minimal_profit):
        stock_list = self.storage.getOrderedStockList()
        wimps_data = []
        for garden in self.garten:
            for k, v in self.wimparea.getWimpsData(garden).items():
                wimps_data.append({k: v})

        for wimps in wimps_data:
            for wimp, products in wimps.items():
                if not self.checkWimpsProfitable(products, minimal_profit):
                    self.wimparea.declineWimp(wimp)
                else:
                    if self.checkWimpsRequiredAmount(minimal_balance, products[1], stock_list):
                        print("Selling products to wimp: " + wimp)
                        print(self.wimparea.productsToString(products, self.productData))
                        new_products_counts = self.wimparea.sellWimpProducts(wimp)
                        for id, amount in products[1].items():
                            stock_list[id] -= amount

    def checkWimpsProfitable(self, products, minimal_profit):
        npc_sum = 0
        for id, amount in products[1].items():
            npc_sum += self.productData.getProductByID(id).getPriceNPC() * amount
        if products[0] / npc_sum * 100 >= minimal_profit:
            to_sell = True
        else:
            to_sell = False
        return to_sell

    def checkWimpsRequiredAmount(self, minimal_balance, products, stock_list):
        to_sell = True
        for id, amount in products.items():
            product = self.productData.getProductByID(id)
            minimal_balance = max(self.note.getMinStock(), self.note.getMinStock(product.getName()), minimal_balance)
            if stock_list.get(id, 0) - (amount + minimal_balance) <= 0:
                to_sell = False
                break
        return to_sell

    def getQuestProducts(self, quest_name, quest_number=0):
        return self.quest.getQuestProducts(quest_name, quest_number)

    def getNextRunTime(self):
        garden_time = []
        for garden in self.garten:
            garden_time.append(garden.getNextWaterHarvest())

        self.updateUserData()
        human_time = datetime.datetime.fromtimestamp(min(garden_time))
        print(f"Next time water/harvest: {human_time.strftime('%d/%m/%y %H:%M:%S')} ({min(garden_time)})")
        return min(garden_time)

    def hasEmptyFields(self):
        emptyFields = self.getEmptyFieldsOfGardens()
        amount = 0
        for garden in emptyFields:
            amount += len(garden)

        return amount > 0

    def getWeedFieldsOfGardens(self):
        """
        Gibt alle Unkrau-Felder aller normalen Gärten zurück.
        """
        weedFields = []
        try:
            for garden in self.garten:
                weedFields.append(garden.getWeedFields())
        except:
            self.__logBot.error(f'Could not determinate weeds on fields of garden {garden.getID()}.')
        else:
            pass

        return weedFields

    def clearWeedFields(self, minimal_cash):
        weedFields = self.getWeedFieldsOfGardens()
        if sum(len(g) for g in weedFields) == 0:
            return
        cleared_fields = 0
        for garden in self.garten:
            # for field in weedFields:
            weeds = weedFields[garden.getID()-1]
            for field_id, cost in weeds.items():
                self.spieler.setUserDataFromServer(self.__HTTPConn)
                if self.spieler.getBar() - cost >= minimal_cash:
                    success = garden.clearWeedField(field_id)
                    cleared_fields += success

        print("There were cleared " + str(cleared_fields) + " fields")

    def harvestAllGarden(self):
        # TODO: Add Watergarden
        try:
            for garden in self.garten:
                garden.harvest()
                
            if self.spieler.isAquaGardenAvailable():
                pass#self.waterPlantsInAquaGarden()

            self.storage.updateNumberInStock()
        except:
            self.__logBot.error(i18n.t('wimpb.harvest_not_successful'))
        else:
            self.__logBot.info(i18n.t('wimpb.harvest_successful'))

    def getGrowingPlantsInGardens(self):
        growingPlants = Counter()
        try:
            for garden in self.garten:
                growingPlants.update(garden.getGrowingPlants())
        except:
            self.__logBot.error('Could not determine growing plants of garden ' + str(garden.getID()) + '.')
        else:
            pass

        return dict(growingPlants)

    def growPlantsInGardens(self, productName, amount=-1):
        """
        Pflanzt so viele Pflanzen von einer Sorte wie möglich über alle Gärten hinweg an.
        """
        planted = 0

        product = self.productData.getProductByName(productName)

        if product is None:
            logMsg = f'Plant "{productName}" not found'
            self.__logBot.error(logMsg)
            print(logMsg)
            return -1

        if not product.isPlant() or not product.isPlantable():
            logMsg = f'"{productName}" could not be planted'
            self.__logBot.error(logMsg)
            print(logMsg)
            return -1

        if amount == -1 or amount > self.storage.getStockByProductID(product.getID()):
            amount = self.storage.getStockByProductID(product.getID())

        remainingAmount = amount
        for garden in self.garten:
            planted += garden.growPlant(product.getID(), product.getSX(), product.getSY(), remainingAmount)
            remainingAmount = amount - planted
        
        self.storage.updateNumberInStock()

        return planted

    def printStock(self):
        isSmthPrinted = False
        for productID in self.storage.getKeys():
            product = self.productData.getProductByID(productID)
            
            amount = self.storage.getStockByProductID(productID)
            if amount == 0: continue
            
            print(str(product.getName()).ljust(30) + 'Amount: ' + str(amount).rjust(5))
            isSmthPrinted = True
    
        if not isSmthPrinted:
            print('Your stock is empty')
    
    def getLowestStockEntry(self):
        entryID = self.storage.getLowestStockEntry()
        if entryID == -1: return 'Your stock is empty'
        return self.productData.getProductByID(entryID).getName()

    def getOrderedStockList(self):
        orderedList = ''
        for productID in self.storage.getOrderedStockList():
            orderedList += str(self.productData.getProductByID(productID).getName()).ljust(20)
            orderedList += str(self.storage.getOrderedStockList()[productID]).rjust(5)
            orderedList += str('\n')
        return orderedList.strip()
    
    def getLowestPlantStockEntry(self):
        lowestStock = -1
        lowestProductId = -1
        for productID in self.storage.getOrderedStockList():
            if not self.productData.getProductByID(productID).isPlant() or \
                not self.productData.getProductByID(productID).isPlantable():
                continue

            currentStock = self.storage.getStockByProductID(productID)
            if lowestStock == -1 or currentStock < lowestStock:
                lowestStock = currentStock
                lowestProductId = productID
                continue

        if lowestProductId == -1: return 'Your stock is empty'
        return self.productData.getProductByID(lowestProductId).getName()

    def getLowestSinglePlantStockEntry(self):
        lowestSingleStock = -1
        lowestSingleProductId = -1
        for productID in self.storage.getOrderedStockList():
            if not self.productData.getProductByID(productID).isPlant() or \
                not self.productData.getProductByID(productID).isPlantable() or \
                not self.productData.getProductByID(productID).getName() in self.productData.getListOfSingleFieldPlants():
                continue

            currentStock = self.storage.getStockByProductID(productID)
            if lowestSingleStock == -1 or currentStock < lowestSingleStock:
                lowestSingleStock = currentStock
                lowestSingleProductId = productID
                continue

        if lowestSingleProductId == -1: return 'Your stock is empty'
        return self.productData.getProductByID(lowestSingleProductId).getName()

    def printProductDetails(self):
        self.productData.printAll()
    
    def printPlantDetails(self):
        self.productData.printAllPlants()

    def getAllWimpsProducts(self):
        allWimpsProducts = Counter()
        for garden in self.garten:
            tmpWimpData = self.wimparea.getWimpsData(garden)
            for products in tmpWimpData.values():
                allWimpsProducts.update(products[1])

        return dict(allWimpsProducts)

    def sellWimpsProducts(self, minimal_balance, minimal_profit):
        stock_list = self.storage.getOrderedStockList()
        wimps_data = []
        for garden in self.garten:
            for k, v in self.wimparea.getWimpsData(garden).items():
                wimps_data.append({k: v})

        for wimps in wimps_data:
            for wimp, products in wimps.items():
                if not self.checkWimpsProfitable(products, minimal_profit):
                    self.wimparea.declineWimp(wimp)
                else:
                    if self.checkWimpsRequiredAmount(minimal_balance, products[1], stock_list):
                        print("Selling products to wimp: " + wimp)
                        new_products_counts = self.wimparea.sellWimpProducts(wimp)
                        for id, amount in products[1].items():
                            stock_list[id] -= amount

    def checkWimpsProfitable(self, products, minimal_profit):
        npc_sum = 0
        for id, amount in products[1].items():
            npc_sum += self.productData.getProductByID(id).getPriceNPC() * amount
        if products[0] / npc_sum * 100 >= minimal_profit:
            to_sell = True
        else:
            to_sell = False
        return to_sell

    def checkWimpsRequiredAmount(self, minimal_balance, products, stock_list):
        to_sell = True
        for id, amount in products.items():
            k = self.productData.getProductByID(id).getSX() * self.productData.getProductByID(id).getSY()
            if stock_list.get(id, 0) - (amount + minimal_balance / k) <= 0:
                to_sell = False
                break
        return to_sell

    def getGrowingTime(self, item):
        return self.productData.getProductByID(item[0]).getGrowingTime()

    def getQuestProducts(self, quest_name, quest_number=0):
        quest_products = self.quest.getQuestProducts(quest_name, quest_number)
        if isinstance(quest_products, dict):
            sorted_products = dict(sorted(quest_products.items(), key=self.getGrowingTime, reverse=True))
        elif isinstance(quest_products, list):
            sorted_products = []
            for quest in quest_products:
                sorted_products.append(dict(sorted(quest.items(), key=self.getGrowingTime, reverse=True)))
        return sorted_products

    def getNextRunTime(self):
        garden_time = []
        for garden in self.garten:
            garden_time.append(garden.getNextWaterHarvest())

        self.updateUserData()
        human_time = datetime.datetime.fromtimestamp(min(garden_time))
        print(f"Next time water/harvest: {human_time.strftime('%d/%m/%y %H:%M:%S')} ({min(garden_time)})")
        return min(garden_time)


    def removeWeedInAllGardens(self):
        """
        Entfernt Unrkaut/Maulwürfe/Steine aus allen Gärten.
        """
        #TODO: Wassergarten ergänzen
        try:
            for garden in self.garten:
                garden.removeWeed()
        except:
            self.__logBot.error(i18n.t('wimpb.w_harvest_not_successful'))
        else:
            self.__logBot.info(i18n.t('wimpb.w_harvest_successful'))

    def getDailyLoginBonus(self):
        self.bonus.getDailyLoginBonus()

    # Bienen
    def doSendBienen(self):
        if self.spieler.isHoneyFarmAvailable():
            hives = self.__HTTPConn.getHoneyFarmInfos()[2]
            for hive in hives:
                self.__HTTPConn.sendeBienen(hive)
                self.bienenfarm.harvest()
        else:
            self.__logBot.error('Konnte nicht alle Bienen ernten.')