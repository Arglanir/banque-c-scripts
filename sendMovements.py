"""Ce script envoie les derniers mouvements journaliers aux adresses indiquées"""

from banquec import getBanqueCDriver, goToAccounts, listAccounts, displayMovements, listMovements
from configuration import smtphost, smtpuser, smtppassword, sendMovementsTo, encrypt, decrypt
import sys, os
import pickle
import datetime

import smtplib
import html

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


DB = dict()
    # lastUpdate = last update time
    # accountXXXXXX = [lastupdatetime, (date, text, amount)]
DBFILE = "sentMovements.db"

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
            if "account%s" % number not in DB:
                DB["account%s" % number] = []
            known = set(DB["account%s" % number])
            firstchange = True
            changes = []
            # analyse de chaque mouvement
            for movement in movements:
                if movement in known:
                    continue
                if firstchange:
                    DB["account%s" % number].append(datetime.datetime.now())
                    firstchange = False
                DB["account%s" % number].append(movement)
                changes.append(movement)
            if not changes:
                continue
            
            informationToSend.append("{} mouvements sur le {} {} de {}, reste {}€"
                                         .format(len(changes),
                                         name, number, owner, amount))

            table = "<table>\n<tr><th>Date</th><th>Quoi</th><th>Combien</th></tr>\n"
            for date, text, amount in changes:
                table += '''<tr>
<td class="date">{}</td>
<td class="text">{}</td>
<td class="amount">{:+.2f}</td>
</tr>\n'''.format(date, html.escape(text).replace('\n', '<br/>'), amount)
            table += "</table>"
            informationToSend.append(table)
        save()
    # create e-mail
    if not informationToSend:
        print("Nothing to send.")
        return

    print("Preparing e-mail...")    
    me = smtpuser
    you = sendMovementsTo

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Mouvements des comptes"
    msg['From'] = me
    msg['To'] = you

    # Create the body of the message (a plain-text and an HTML version).
    text = ""
    for info in informationToSend:
        text += "<div>{}</div>\n".format(info)
    
    
    htmldata = """\
    <html>
      <head></head>
      <body>
        {}
      </body>
    </html>
    """.format(text)
    

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
        print("Sending email to", you, "...")
        s.sendmail(me, you, msg.as_string())
        s.quit()
    print("Done!")
    
if __name__ == '__main__':
    main()
