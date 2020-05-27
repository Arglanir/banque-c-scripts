import sys, subprocess, os, time, contextlib
try:
    import selenium
except ImportError:
    print("Installing Selenium")
    p = subprocess.Popen([sys.executable, "-m", "pip", "install", "-U", "selenium"])
    p.communicate()
    import selenium

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import JavascriptException, NoSuchElementException

DRIVER = webdriver.Firefox
def DRIVERCREATION():
    from selenium.webdriver.firefox.options import Options
    options = Options()
    options.headless = True
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/plain,text/html")
    profile.set_preference("browser.download.folderLis", "1")
    return DRIVER(firefox_profile = profile, options=options)

FILESTOFETCH = {
# https://github.com/mozilla/geckodriver/releases
webdriver.Firefox: "https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-win64.zip",
# https://chromedriver.chromium.org/downloads
webdriver.Chrome: "https://chromedriver.storage.googleapis.com/83.0.4103.39/chromedriver_win32.zip"
}
# installing firefox driver
#   
#   
EXECUTABLEFOLDER = "drivers"
SCRIPTFOLDER = os.path.dirname(os.path.abspath(__file__))
JSFOLDER = os.path.dirname(SCRIPTFOLDER)
CURRENTDRIVER = None

niceCountDown = time.sleep

import configuration

@contextlib.contextmanager
def getBanqueCDriver(quit_at_end=True):
    global CURRENTDRIVER
    destfoldertopath = os.path.join(SCRIPTFOLDER, EXECUTABLEFOLDER)
    try:
        if os.path.exists(destfoldertopath):
            print("Update PATH")
            os.environ["PATH"] = os.pathsep.join([os.environ["PATH"], destfoldertopath])
        driver = DRIVERCREATION()
    except:
        if not os.path.exists(destfoldertopath):
            os.makedirs(destfoldertopath)
        import urllib.request, zipfile, io
        urltofetch = FILESTOFETCH.get(DRIVER)
        print("Fetching", urltofetch)
        filestream = urllib.request.urlopen(urltofetch)
        datatowrite = filestream.read()
        zfile = zipfile.ZipFile(io.BytesIO(datatowrite))
        zfile.extractall(destfoldertopath)
        os.environ["PATH"] = os.pathsep.join([os.environ["PATH"], destfoldertopath])
        driver = DRIVERCREATION()

    CURRENTDRIVER=driver
    # testing
    print("Getting auth page")
    try:
        banque_url, username, password = configuration.bankurl, configuration.bankuser, configuration.bankpassword
    except:
        print("Please write a file", credfile, "with url username password")
        raise
    print("Going to bank")
    driver.get(banque_url)

    print("Clicking on first image")
    div = driver.find_element_by_id('gauche')
    a = div.find_elements_by_tag_name('img')[0]
    a.click()

    driver.find_element_by_name("CCPTE").send_keys(username)

    tds = driver.find_elements_by_tag_name("td")
    nb2td = dict()
    for td in tds:
        if not td.get_attribute("onclick"):
            continue
        nb = td.text.replace("&nbsp;","").strip()
        nb2td[nb] = td

    for i in password:
        nb2td[i].click()

    driver.execute_script("ValidCertif();")
    
    try:
        yield driver
    finally:
        print("End of session")
        if quit_at_end:
            driver.quit()

def goToAccounts(driver):
    print("Vers la page principale...")
    while True:
        try:
            driver.find_element_by_class_name("itemactif-bnt-titre-Autrescomptes").click()
            break
        except NoSuchElementException:
            print("Bandeau non encore affiché on dirait")
            time.sleep(1)
    counter = 0
    while True:
        h1s = driver.find_elements_by_tag_name("h1")
        for stink in h1s:
            if "comptes" in stink.text:
                return
        counter += 1
        print("En attente de l'affichage des comptes... %ss\r" % counter)
        time.sleep(1)

    
    

def listAccounts(driver):
    # return list( (element, owner, name, number, amount) )
    toreturn = []
    trs = driver.find_elements_by_tag_name("tr")
    owner = "?"
    for tr in trs:
        tds = tr.find_elements_by_tag_name("td")
        if len(tds) == 1 and "titretetiere" in tds[0].get_attribute("class"):
            owner = tds[0].text.strip()
        if len(tds) < 5: continue
        name = tds[0].text.strip()
        #print("Testing", name)
        try:
            element = tds[0].find_element_by_tag_name("a")
        except:
            continue
        number = tds[2].text.strip()
        if not number:
            continue
        #print("  number", number)
        #print("  ", [k.text.strip() for k in tds[3:]])
        try:
            amount = float(tds[4].text.strip().replace(" ","").replace(",", "."))
        except ValueError as e:
            print("  ", repr(e))
            continue
        #print("  amount", amount)
        toreturn.append((element, owner, name, number, amount))
    return toreturn


def displayMovements(driver, accountelement):
    if isinstance(accountelement, str):
        goToAccounts(driver)
        print("Vers le compte", accountelement, "...")
        accountelement = [k[0] for k in listAccounts(driver) if k[3] == accountelement][0]
    accountelement.click()
    counter = 0
    while True:
        bs = driver.find_elements_by_tag_name("b")
        for bb in bs:
            if "HISTORIQUE" in bb.text.upper():
                return
        counter += 1
        print("En attente de l'affichage de l'historique... %ss %sb\r" % (counter, len(bs)))
        time.sleep(1)

def listMovements(driver):
    # return list (date, text, amount)
    toreturn = []
    for tr in driver.find_elements_by_tag_name("tr"):
        tds = tr.find_elements_by_tag_name("td")
        if len(tds) != 3 and len(tds) != 4:
            continue
        date = tds[0].text.strip()
        text = tds[1].text.strip()
        amount = tds[-1].text.strip().replace(',','.').replace(' ', '')
        try:
            amount = float(amount)
        except ValueError as e:
            print(repr(e))
            continue
        toreturn.append((date, text, amount))
    return toreturn

if __name__ == '__main__':
    with getBanqueCDriver( False ) as driver:
        goToAccounts(driver)
        accounts = listAccounts(driver)
        print(*[k[1:] for k in accounts], sep="\n")
        for account in accounts:
            displayMovements(driver, account[-2])
            movements = listMovements(driver)
            print(*movements, sep="\n")
