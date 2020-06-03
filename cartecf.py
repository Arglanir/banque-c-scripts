import sys, subprocess, os, time, contextlib
import preparation
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import JavascriptException, NoSuchElementException

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image, ImageOps
import urllib.request
from collections import namedtuple
import datetime
import re

CURRENTDRIVER = None

niceCountDown = time.sleep

import configuration

@contextlib.contextmanager
def getCarteCFDriver(quit_at_end=True):
    global CURRENTDRIVER
    driver = preparation.getOneDriver()

    CURRENTDRIVER=driver
    # testing
    print("Getting auth page")
    try:
        banque_url, username, password = configuration.carteurl, configuration.carteuser, configuration.cartepassword
    except:
        print("Please write a file in configuration.py missing parameters")
        raise
    print("Going to bank")
    driver.get(banque_url)

    elements = []
    while not elements:
        elements = driver.find_elements_by_class_name("ButtonGroup__BtnStyle-sc-1usw1pe-0")
    print("Accepting cookies...")
    elements[-1].click()
    time.sleep(1)

    element = driver.find_element_by_id('edit-name')
    element.send_keys(username + Keys.RETURN)

    while True:
        digits = driver.find_elements_by_class_name("digit")
        if digits:
            break
        time.sleep(1)

    print("Interpreting digits...")
    digit2button = dict()
    for digit in digits:
        data = digit.get_attribute("src")
        print(data[:20])
        img = Image.open(urllib.request.urlopen(data))
        dnb = pytesseract.image_to_string(ImageOps.invert(img.convert("L")), config="--psm 10")
        digit2button[dnb] = digit
        print("Recognized digit:", repr(dnb))

    for d in password:
        digit2button[d].click()
    
    
    valid = driver.find_element_by_id('edit-submit')
    valid.click()

    time.sleep(2)

    driver.get(configuration.carteurl2)
    time.sleep(2)
    
    try:
        yield driver
    finally:
        print("End of session")
        if quit_at_end:
            driver.quit()

DATETEXTPATTERN = re.compile(r"(?P<day>\d\d?)/(?P<month>\d\d?)\s(?P<hour>\d\d)(?P<minute>\d\d)$")
DATEPATTERN = re.compile(r"(?P<day>\d\d?)/(?P<month>\d\d?)/(?P<year>\d\d\d\d)")

class CarteCFEntry(namedtuple("Entry", "date text amount mode card")):
    @property
    def datetime(self):
        date1m = DATEPATTERN.search(self.date)
        finaldate = datetime.datetime(int(date1m.group("year")),
                                  int(date1m.group("month")),
                                  int(date1m.group("day")))
        date2m = DATETEXTPATTERN.search(self.text)
        if date2m is not None:
            # beware change of year
            finaldate = datetime.datetime(
                int(date1m.group("year"))
                if int(date2m.group("month")) <= int(date1m.group("month"))
                # when month in text == 12 and month in date == 1, change year
                else int(date1m.group("year"))-1,
                int(date2m.group("month")),
                int(date2m.group("day")),
                int(date2m.group("hour")),
                int(date2m.group("minute"))
                )
        return finaldate

    def __str__(self):
        return str(self.datetime) + ":" + super().__str__()

def listOperations(driver):
    table = driver.find_element_by_id("creditHistory")
    operations = []
    for tr in table.find_elements_by_tag_name("tr"):
        td = tr.find_elements_by_tag_name("td")
        if not td or len(td) < 5: continue
        date = td[0].text.strip()
        text = td[1].text.strip()
        try:
            amount = float(td[2].text.strip().replace(",", ".").replace(" €", ""))
        except ValueError as e:
            print("  ", e)
            continue
        mode = td[3].text.strip()
        card = td[4].text.strip()
        operations.append(CarteCFEntry(date, text, amount, mode, card))
    return operations
    

if __name__ == '__main__':
    preparation.HEADLESS = False
    with getCarteCFDriver( False ) as driver:
        print(*listOperations(driver), sep="\n")
