# Author: Dan Clark
# Start Date: 04/01/2022
# Public Commit Date: 05/04/2022

import requests
import time
import csv
from selenium import webdriver

# Here you need to set the margins you want for it to alert on.  So for a higher $ for pickier deals and to sell higher than low if direct pricing is not available
# On the reverse, the buy margin should be as low as you want it to set your buylist prices as cheap as possible.
pricingDict = {'dealMargin' : 1, 'buyMargin' : 1, 'sellOverLow' : 1}

class Card:
    def __init__(self, uuid, condition, printing, tcgplayer):
        self.uuid = uuid
        
        # Here you need a way to query the MTGJSON data for the uuid
        #
        #self.db = Database(credentials)
        #data = self.db.readDB(f'SELECT * FROM cards WHERE uuid = "{uuid}";')
        data = data[0]

        try:
            self.buylist = data[-1]
            if self.buylist == None:
                self.buylist = 0
        except:
            self.buylist = 0

        try:
            self.ckEtchedId = data[5]
        except:
            self.ckEtchedId = None

        try:  
            self.ckFoilId = data[6]
        except:
            self.ckEtchedId = None

        try:
            self.ckId = data[7]
        except:
            self.ckId = None

        self.finishes = data[19]
        self.frameVersion = data[23]
        self.frameEffect = data[22]
        self.fullArt = data[33]

        try:
            self.mcmId = data[52]
        except:
            self.mcmId = None

        self.name = data[-33]
        self.number = data[60]
        self.prices = []
        self.printing = printing
        self.printings = data[67]
        self.promo = data[37]
        self.promoTypes = data[68]
        self.rarity = data[70]
        self.setCode = data[76]
        self.scryfallId = data[78]

        try:
            self.shopifyId = data[-2]
        except:
            self.shopifyId = None

        self.skus = {}

        try:
            self.tcgEtchedId = data[-11]
        except:
            self.tcgEtchedId = None

        try:    
            self.tcgId = data[-10]
        except:
            self.tcgId = None

        self.textless = data[43]
        self.timeshifted = data[44]
        self.variations = data[-4]
        self.woke = data[26]
        
        self.skus = tcgplayer.getSku(self.tcgId)

        for item in self.skus:
            itemCondition = item['conditionId']
            language = item['languageId']
            foil = item['printingId']
            sku = item['skuId']

            if itemCondition == condition and foil == printing:
                if language == 1:
                    price = tcgplayer.checkPrice(sku)
                    directLow = price[0]
                    realLow = price[1]
                    market = price[2]
                    buy = tcgplayer.checkBuylistPrice(sku)
                    high = buy[0]
                    buyMarket = buy[1]
                    p = {condition : {'sku' : sku, 'condition' : condition, 'directLow': directLow, 'realLow' : realLow,'marketPrice': market, 'buylistHigh' : high, 'buylistMarket' : buyMarket}}
                    self.prices.append(p)

class TcgCard:
    def __init__(self, productId, condition, printing, tcgplayer, pricingDict, skuId=None,):
        print(f'INFO: Initializing a card for TCGPLayer')
        self.dealMargin = pricingDict['dealMargin']
        self.buyMargin = pricingDict['buyMargin']
        self.sellLow = pricingDict['sellOverLow']

        #Here you will need to have a way to query the MTGJSON data for the TCGPlayer productId
        #
        #db = Database(credentials)

        try:
            #uuid = db.uuidLookupTcg(productId)
            print(f'INFO: Found {uuid} from {productId}, initializing card with condition {condition}')
        except:
            try:
               # uuid = db.uuidLookupTcgEtched(productId)
               print(f'INFO: Found UUID {uuid}')
            except:
                print(f'ERROR: Cannot find UUID from {productId}')

        self.card = Card(uuid, condition, printing, tcgplayer)
        
        if skuId:
            priceList = tcgplayer.checkPrice(skuId)
            self.directLow = priceList[0]
            self.realLow = priceList[1]
            self.market = priceList[2]
            buyPrices = tcgplayer.checkBuylistPrice(skuId)
            self.buyHigh = buyPrices[0]
            self.buyMarket = buyPrices[1]
            self.price = self.setPrices('direct')
            self.buyPrice = self.setBuylistPrice()
            self.premium = self.findDeals()

        else:

            skuList = self.card.skus
            self.tcgSku = skuList[condition]['skuId']
            priceList = self.card.prices
            self.directLow = priceList[0][condition]['directLow']
            self.realLow = priceList[0][condition]['realLow']
            self.market = priceList[0][condition]['marketPrice']
            self.buyHigh = priceList[0][condition]['buylistHigh']
            self.buyMarket = priceList[0][condition]['buylistMarket']
            self.price = self.setPrices('direct')
            self.buyPrice = self.setBuylistPrice()
            self.premium = self.findDeals()

    def calculateBuylistMargin(self):
        buyPrice = float(self.buyPrice)
        sellPrice = float(self.price)
        buyFee = buyPrice * .10
        sellFee = self.calculateFees(0)
        self.buyMargin = sellPrice - buyPrice - buyFee - sellFee

        return self.buyMargin

    def calculateFees(self, syp):
        price = float(self.price)
        sift = 0
        if syp == 1:
            if price < 0.25:
                sift = 0.01
            
            if price >= 0.25 and price <= 0.49:
                sift = 0.07
            
            if price > 0.5:
                sift = 0.1

        if syp == 0:
            sift = 0.00

        if price < 3:
            self.totalFee = (price / 2) + sift
            return self.totalFee

        if price >= 3:    
            marketCommission = 0.0895 * price 
            proFee = 0.025 * price
            paypalFee = (0.025 * price) + 0.3
            self.totalFee = sift + marketCommission + paypalFee + price + proFee
            return self.totalFee

    def calculateMargin(self, buyPrice):
        self.margin = self.price - buyPrice - self.totalFee
        return self.margin
   
    def findDeals(self):
    
        if self.realLow * self.dealMargin < self.directLow:
            margin = self.calculateMargin(self.realLow)
            if margin > 1:
                self.premium = margin

        else:
            self.premium = 0

    def setBuylistPrice(self):
        sellPrice = float(self.price)
        buylistHigh = float(self.buyHigh)

        try:
            buylistMarket = float(self.buyMarket)
        except:
            buylistMarket = 0.01

        self.buyPrice = 0.01

        if sellPrice >= 10:
            margin = sellPrice * self.buyMargin

            if buylistHigh < margin:
                if buylistHigh < buylistMarket:
                    self.buyPrice = buylistHigh
                if buylistMarket < buylistHigh:
                    self.buyPrice = buylistMarket

            if margin < buylistHigh:
                if margin < buylistMarket:
                    self.buyPrice = margin
                if buylistMarket < margin:
                    self.buyPrice = buylistMarket

        if sellPrice > 7.50 and sellPrice < 10:
            self.buyPrice = 3

        if sellPrice > 5 and sellPrice <= 7.50:
            self.buyPrice = 2

        if sellPrice > 3 and sellPrice <= 5:
            self.buyPrice = 1

        if sellPrice < 3 and sellPrice > 2:
            self.buyPrice = 0.75

        if sellPrice < 2 and sellPrice > 0.50:
            self.buyPrice= 0.05                      

        return self.buyPrice
              
    def setPrices(self, type):
        if type == 'direct':
            if not self.market and not self.directLow:
                market = float(self.realLow) * self.sellLow
               # print('INFO: No Direct price Found')

            elif not self.market and self.directLow:
                market = self.directLow
               # print('INFO: No Market Price Found')

            misprice = float(self.market) * 0.8
            directlow = float(self.directLow)

            if directlow >= misprice:
                self.price  = float(directlow)
                return self.price
            else:
                self.price = float(market)
                print('INFO: Direct Found! Adjusted Pricing')
                return self.price

        if type == 'low':
            self.price = float(self.realLow) * self.sellLow
            print('INFO: Low Price Found')

        if type == 'buylist':
            self.price = float(self.realLow)

        else:
            self.price = float(market)
            ('WARN: No TCGLOW pricing found?')

        return self.price

class TcgPlayer:
    def __init__(self, store):
        self.client = store[0]
        self.secret = store[1]
        self.access = store[2]

        print(f'INFO: Initializing TCGPLayer API')
        self.headers = self.getTCGToken()
        self.key = self.storeKey()
        print(f'INFO: Found TCG Keys')
        self.getTCGInventory()
        print(f'INFO: Found Inventory')
        self.getTCGBuylist()
        print(f'INFO: Found Buylist')

    def checkBuylistPrice(self, skuId):
        url =  f'https://api.tcgplayer.com/pricing/buy/sku/{skuId}'
        r = requests.request("GET", url, headers=self.headers)
        results = r.json()

        if results['success'] == True:
            high = results['results'][0]['prices']['high']     
            market = results['results'][0]['prices']['market']

            return high, market
        else:
            print(f'WARN: Could not Check buylist price for {skuId}, {r.status_code}, {r.text}')
            return 0, 0

    def checkOffset(self, url, originalResults):
        results = originalResults[0]
        totalItems = results['totalItems']
        results = results['results']
        length = len(results)
        remainingItems = totalItems - length
        more = 100
        offset = 100
        print(f'INFO: Appended up to {length} / {totalItems}')
        while remainingItems > 0:
            time.sleep(0.01)
            newUrl = url + f'&offset={offset}'
            response = requests.request("GET", newUrl, headers=self.headers)
            newData = response.json()
            items = newData['results']
            if items == []:
                length = len(results)
                print(f'INFO: Finished Fetching Results {length} / {totalItems}')       
                return results

            else:
                items = newData['results']
                for i in items:
                    results.append(i)
                length = len(results)
                print(f'INFO: Appended up to {length} / {totalItems}')

                if remainingItems < 100 and remainingItems > 0:
                    offset = totalItems - length
                else:
                    offset = offset + 100
                more = more + 100

    def checkPrice(self, skuId):
        url =  f'https://api.tcgplayer.com/pricing/sku/{skuId}'
        r = requests.request("GET", url, headers=self.headers)
        results = r.json()

        if skuId != None:
            if results['success'] == True:
                directlow = results['results'][0]['directLowPrice']
                realLow = results['results'][0]['lowestListingPrice']
                market = results['results'][0]['marketPrice']

            else:
                print(f'Error Finding Price {skuId}, {r.status_code}, {r.text}')

            if directlow == None:
                directlow = realLow
                print(f'WARN: No Direct Pricing for {skuId}')

            if realLow == None:
                realLow = market
                print(f'WARN: No Low Pricing for {skuId}')
        
            return directlow, realLow, market

        else:
            return False

    def exportAll():
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference("browser.download.dir", "C:\AWtemp")
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        driver = webdriver.Firefox(firefox_profile=profile)
        driver.get('https://store.tcgplayer.com/admin/Account/Logon')
        time.sleep(60)
        driver.get('https://store.tcgplayer.com/admin/direct/ExportSYPList?categoryid=1&setNameId=All&conditionId=All')
        time.sleep(5)
        buylist = driver.get('https://store.tcgplayer.com/Admin/Pricing/DownloadMyExportCSV?type=Buylist')
        time.sleep(5)
        pricing = driver.get('https://store.tcgplayer.com/Admin/Pricing/DownloadMyExportCSV?type=Pricing')
        time.sleep(5)

        return buylist, pricing

    def getSku(self, productId):
        url = f"https://api.tcgplayer.com/catalog/products/{productId}/skus"
        response = requests.request("GET", url, headers=self.headers)
        data = response.json()
        results = []
        
        try:
            if data['success'] == True:
                results = data['results']

                return results
            
            else:
                print(f'ERROR: Could not find TCG Sku for {productId}')
        except:
            print(f'ERROR: Key Error with Sku')
            
    def getTCGBuylist(self):
        url = f" https://api.tcgplayer.com/stores/{self.key}/buylist/products?limit=100"

        response = requests.request("GET", url, headers=self.headers)
        data = response.json()
        results = []

        if data['success'] == True:
            results.append(data)
            length = len(data['results'])
            totalItems = data['totalItems']
            print(f'INFO: Buylist has {totalItems} items')

            if totalItems > length:
                results = self.checkOffset(url, results)
            else:
                results =data['results']
        else:
            results = 0
            print(f'WARN: No Buylist Found')

        self.buylist = results

    def getTCGInventory(self):
        url = f"https://api.tcgplayer.com/stores/{self.key}/inventory/products?limit=100"

        response = requests.request("GET", url, headers=self.headers)
        data = response.json()
        results = []
        
        if data['success'] == True:
            results.append(data)
            length = len(data['results'])
            totalItems = data['totalItems']
            print(f'INFO: Inventory has {totalItems} items')

            if totalItems > length:
                results = self.checkOffset(url, results)
        else:
            results = 0
            print(f'WARN: No Inventory Found')
        self.inventory = results

    def getTCGToken(self):
        grant_type = 'client_credentials'
        headers = {"Accept": "application/x-www-form-urlencoded", "grant_type" : grant_type, "X-Tcg-Access-Token" : self.access}
        body = f"grant_type=client_credentials&client_id={self.client}&client_secret={self.secret}"
        url = f"https://api.tcgplayer.com/token"

        response = requests.request("POST", data=body, url=url, headers=headers)
        data = response.json()
        
        try:
            token = data['access_token']
            headers = {"Accept": "application/json", "Content-Type": "text/json", "Authorization": f"Bearer {token}"}

        except:
            print(f'ERROR: Cannot get token {data}')

        return headers 

    def putOnline(self):
        url = f"https://api.tcgplayer.com/stores/{self.key}/status/active"
        response = requests.request("PUT", url, headers=self.headers)
        
        if response.status_code == 200:
            return True
        else:
            return False

    def storeKey(self):
        url = "https://api.tcgplayer.com/stores/self"

        response = requests.request("GET", url, headers=self.headers)
        data = response.json()

        if data['success'] == True:
            storeKey = data['results'][0]['storeKey']
            return storeKey

        else:
            print(f"Could not Find storeKey {response.status_code}")
            return False

    def takeOffline(self):
        url = f"https://api.tcgplayer.com/stores/{self.key}/status/inactive"
        response = requests.request("PUT", url, headers=self.headers)
        
        if response.status_code == 200:
            print('Store Offline')
            return True
        else:
            print(f'ERROR: Could not take store offline! {response.status_code}, {response.text}')
            return False

    def updateBuylist(self, file):
        file = open(file)
        file = csv.DictReader(file)
        output = open('output-buylist.csv', 'w', newline='')
        newFile = csv.DictWriter(output, ['TCGplayer Id', 'Product Line', 'Set Name', 'Product Name', 'Number', 'Rarity', 'Condition', 'Buylist Market Price', 'Buylist High Price', 'Buylist Quantity' ,'Add to Buylist Quantity',	'My Buylist Price' ,'Pending Purchase Quantity'])
        newFile.writeheader()

        for row in file:
            csvCardName = row['Product Name']
            csvId = row['TCGplayer Id']
            csvProduct = row['Product Line']
            csvSet = row['Set Name']
            csvNum = row['Number']
            csvRarity = row['Rarity']
            csvCondition = row['Condition']
            csvBuyMarket = (row['Buylist Market Price'])
            csvBuyHigh = (row['Buylist High Price'])
            csvBuyQty = 4
            csvAddQty = 0
            

            if csvBuyHigh > csvBuyMarket:
                if csvBuyMarket != '':
                    csvBuyPrice = float(csvBuyMarket) * 0.85
                else:
                    csvBuyMarket = csvBuyHigh
                    csvBuyPrice = float(csvBuyHigh) * 0.85

            elif csvBuyMarket > csvBuyHigh:
                if csvBuyHigh != '':
                    csvBuyPrice = float(csvBuyHigh) * 0.85
                else:
                    csvBuyHigh = csvBuyMarket
                    csvBuyPrice = float(csvBuyMarket) * 0.85
            else:
                csvBuyPrice = float(csvBuyMarket) * 0.85
            
            if float(csvBuyMarket) <= 5 or float(csvBuyHigh) <= 5:
                csvBuyPrice = csvBuyPrice * 0.85

            if float(csvBuyMarket) <= 3 or float(csvBuyHigh) <=3:
                csvBuyPrice = csvBuyPrice * 0.85

            if float(csvBuyMarket) <= 1 or float(csvBuyHigh) <= 1:
                csvBuyPrice = 0.03

            csvPending = row['Pending Purchase Quantity']

            newRow = {'TCGplayer Id' : csvId, 'Product Line' : csvProduct, 'Set Name' : csvSet, 'Product Name' : csvCardName, 'Number' : csvNum, 'Rarity' : csvRarity, 'Condition' : csvCondition, 'Buylist Market Price' : csvBuyMarket, 'Buylist High Price' : csvBuyHigh, 'Buylist Quantity' : csvBuyQty, 'Add to Buylist Quantity' : csvAddQty, 'My Buylist Price' : csvBuyPrice, 'Pending Purchase Quantity': csvPending}

            try:
                newFile.writerow(newRow)
            except:
                print(f'ERROR: Could not write row : {newRow}')

        output.close()
        print('All Done')

    def updatePricing(self, quantity = None):
        self.takeOffline()
        length = len(self.inventory)
        print(f'Found {length} cards to update')
        for card in self.inventory:
            try:
                skus = card['skus']
                name = card['name']
                productId = card['productId']
                
                for sku in skus:
                    skuId = sku['skuId']
                    oldPrice = sku['price']
                    printing = sku['foil']

                    if printing == True:
                        printing = 2
                    else:
                        printing = 1

                    condition = sku['condition']['name']
                    quantity = sku['quantity']

                    if quantity > 0:

                        if condition.startswith('Near Mint'):
                            condition  = 1
                        elif condition.startswith('Lightly Played'):
                            condition = 2
                        elif condition.startswith('Moderately Played'):
                            condition = 3
                        elif condition.startswith('Heavily Played'):
                            condition = 4
                        elif condition.startswith('Damaged'):
                            condition = 5

                        try:
                            cardInfo = TcgCard(productId, condition, printing, self, skuId=skuId)
                            try:
                                if cardInfo.price > 5 and cardInfo.price < oldPrice * 0.75:
                                    print(f'WARN: Manually check {skuId} {name}, keeping old price for now')
                                    price = oldPrice
                                
                                else:
                                    price = cardInfo.price
                                    if quantity:
                                        body = {'price' : price, 'quantity' : quantity, 'channelId' : 0}
                                    else:
                                        body = {'price' : price, 'channelId' : 0}

                                    url = f"https://api.tcgplayer.com/stores/{self.key}/inventory/skus/{skuId}/price"

                                    response = requests.request("PUT", url, json=body, headers=self.headers)
                                    data = response.json()

                                    if data['success'] == True:
                                        print(f'SUCCESS: Updated {skuId} {condition} {name} to {price}')
                                    else:
                                        print(f'ERROR: updating {skuId} {name}, {response.status_code}, {response.text}')

                            except:
                                print(f'WARN: Card Found, Pricing dilema')
                        except:
                            print(f'WARN: Could not find Card Info for {card}')
                            price = self.checkPrice(skuId)
                            price = price[0]
                            body = {'price' : price, 'channelId' : 0}
                            url = f"https://api.tcgplayer.com/stores/{self.key}/inventory/skus/{skuId}/price"

                            response = requests.request("PUT", url, json=body, headers=self.headers)
                            data = response.json()

                            if data['success'] == True:
                                print(f'SUCCESS: Updated {skuId} {condition} {name} to {price}')
                            else:
                                print(f'ERROR: updating {skuId} {name}, {response.status_code}, {response.text}')


            except:
                if len(card) > 20:
                    print(f'ERROR: Could not initialize {card}')

        print('All Done')

        self.putOnline()
