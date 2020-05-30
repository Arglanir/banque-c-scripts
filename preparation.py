import sys, subprocess, os


EXECUTABLEFOLDER = "drivers"
SCRIPTFOLDER = os.path.dirname(os.path.abspath(__file__))

HEADLESS = True

try:
    import pip
except ImportError:
    print("Installing pip")
    # TODO: download pip
    # TODO: install pip


try:
    import cryptography
except ImportError:
    print("Installing cryptography")
    p = subprocess.Popen([sys.executable, "-m", "pip", "install", "-U", "cryptography"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    print(p.communicate())
    import cryptography

try:
    import selenium
except ImportError:
    print("Installing Selenium")
    p = subprocess.Popen([sys.executable, "-m", "pip", "install", "-U", "selenium"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    print(p.communicate())
    import selenium
from selenium import webdriver


FILESTOFETCH = {
# https://github.com/mozilla/geckodriver/releases
webdriver.Firefox: "https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-win64.zip",
# https://chromedriver.chromium.org/downloads
webdriver.Chrome: "https://chromedriver.storage.googleapis.com/83.0.4103.39/chromedriver_win32.zip"
}
# installing firefox driver
#   
#   

DRIVER = webdriver.Firefox

def DRIVERCREATION():
    from selenium.webdriver.firefox.options import Options
    options = Options()
    options.headless = HEADLESS
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/plain,text/html")
    profile.set_preference("browser.download.folderLis", "1")
    return DRIVER(firefox_profile = profile, options=options)

def getOneDriver():
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
    return driver
