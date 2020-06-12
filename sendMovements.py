"""Ce script envoie les derniers mouvements journaliers aux adresses indiquées"""

from banquec import getBanqueCDriver, goToAccounts, listAccounts, displayMovements, listMovements
from configuration import smtphost, smtpuser, smtppassword, sendMovementsTo, encrypt, decrypt, updateDb, updateEntry
import sys, os
import pickle
import datetime

import smtplib
import html
import math


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


DB = dict()
    # lastUpdate = last update time
    # accountXXXXXX = [lastupdatetime, (date, text, amount)]
    # accountXXXXXXtotal = total
ACCOUNTKEY = "account%s"
ACCOUNTTOTAL = "account%stotal"
DBFILE = "sentMovements.db"

TEST = False
if TEST:
    import shutil
    shutil.copyfile(os.path.join(os.path.dirname(__file__), DBFILE),
                    os.path.join(os.path.dirname(__file__), DBFILE)+"_temp")
    DBFILE += "_temp"

# method for amount equality
isclose = lambda a,b: math.isclose(a,b,abs_tol=0.001)

def read():
    global DB
    filetoopen = os.path.join(os.path.dirname(__file__), DBFILE)
    if not os.path.exists(filetoopen):
        return
    with open(filetoopen, "rb") as fin:
        data = decrypt(fin.read())
    DB = pickle.loads(data)

def save():
    DB["lastUpdate"] = datetime.datetime.now()
    data = encrypt(pickle.dumps(DB))
    with open(os.path.join(os.path.dirname(__file__), DBFILE), "wb") as fout:
        fout.write(data)

def main():
    read()
    updateDb(DB)
    informationToSend = []
    with getBanqueCDriver() as driver:
        goToAccounts(driver)
        accounts = listAccounts(driver)
        for _element, owner, name, number, amount in accounts:
            displayMovements(driver, number)
            movements = listMovements(driver)
            # vérification
            if len(set(movements)) != len(movements):
                informationToSend.append("Double écriture présente sur le {} {} de {}"
                                         .format(
                                         name, number, owner))
            if ACCOUNTKEY % number not in DB:
                DB[ACCOUNTKEY % number] = []
            if ACCOUNTTOTAL % number not in DB:
                DB[ACCOUNTTOTAL % number] = 0
            predicted = DB[ACCOUNTTOTAL % number]
            known = set(DB[ACCOUNTKEY % number])
            firstchange = True
            changes = []
            # analyse de chaque mouvement
            for movement in movements:
                if movement in known:
                    continue
                if firstchange:
                    DB[ACCOUNTKEY % number].append(datetime.datetime.now())
                    firstchange = False
                DB[ACCOUNTKEY % number].append(movement)
                changes.append(movement)
                predicted += movement[-1]
            if not changes:
                continue
            # affichage d'information
            informationToSend.append("{} mouvements sur le {} {} de {}, reste <b>{:.2f}&nbsp;€</b>"
                                         .format(len(changes),
                                         name, number, owner, amount))
            if not isclose(predicted, amount):
                informationToSend.append("Normalement il devrait y avoir <b>{:.2f}&nbsp;€</b>, il manque <b>{:+.2f}&nbsp;€</b>."
                                         .format(predicted, amount - predicted))
            DB[ACCOUNTTOTAL % number] = amount
            # affichage des mouvements
            table = "<table>\n<tr><th>Date</th><th>Quoi</th><th>Combien</th></tr>\n"
            for entry in changes:
                entry2 = updateEntry(entry)
                date, text, amount = entry2
                title = "" if text == entry.text else entry.text
                table += '''<tr>
<td class="mvt date">{}</td>
<td class="mvt text" title="{}"><small>{}</small></td>
<td class="mvt amount">{:+.2f}</td>
</tr>\n'''.format(date, html.escape(title), html.escape(text).replace('\n', '<br/>'), amount)
            table += "</table><hr/>"
            informationToSend.append(table)
        save()
    # create e-mail
    if not informationToSend:
        print("Nothing to send.")
        return

    print("Preparing e-mail...")    
    me = smtpuser

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Mouvements des comptes"
    msg['From'] = smtpuser
    msg['To'] = ", ".join(sendMovementsTo)

    # Create the body of the message (a plain-text and an HTML version).
    text = ""
    for info in informationToSend:
        text += "<div>{}</div>\n".format(info)
    
    
    htmldata = """\
    <html>
      <head></head>
      <style type="text/css">
.mvt.text {{ font-size: 75%; }}
      </style>
      <body>
        {}
      </body>
    </html>
    """.format(text)

    if TEST:
        print(htmldata)
        return

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(htmldata, 'html')

    # Attach parts into message container.
    msg.attach(part1)
    msg.attach(part2)

    # Send the message via SMTP server.
    print("Connecting to", smtphost, "...")
    with smtplib.SMTP_SSL(smtphost) as s:
        #s.ehlo()
        s.login(smtpuser, smtppassword)
        # sendmail function takes 3 arguments: sender's address, recipient's address
        # and message to send - here it is sent as one string.
        print("Sending email to", msg['To'], "...")
        s.sendmail(smtpuser, sendMovementsTo, msg.as_string())
        s.quit()
    print("Done!")
    
if __name__ == '__main__':
    main()
