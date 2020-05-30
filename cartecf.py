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

def listOperations(driver):
    table = driver.find_element_by_id("creditHistory")
    operations = []
    for tr in table.find_elements_by_tag_name("tr"):
        td = tr.find_elements_by_tag_name("td")
        if not td or len(td) < 5: continue
        date = td[0].text
        text = td[1].text
        try:
            amount = float(td[2].text.strip().replace(",", ".").replace(" €", ""))
        except ValueError as e:
            print("  ", e)
            continue
        mode = td[3].text
        card = td[4].text
        operations.append((date, text, amount, mode, card))
    return operations
    

if __name__ == '__main__':
    preparation.HEADLESS = False
    with getCarteCFDriver( False ) as driver:
        print(*listOperations(driver), sep="\n")
