import json
import re
from datetime import datetime

code = {'result': {'standorteMitTermin': None, 'amSchnellsten': '    <label>Hier gibt&#39;s den fr&#252;hesten Termin</label>\r\n        <div class="card">\r\n            <div class="card-body">\r\n                <p>\r\n                    <strong><a class="ignore-cancel-dialog" href="/HamburgGateway/FVP/FV/Bezirke/DigiTermin/Kundenzentrum/SelectKundenzentrum/200">Hamburg Welcome Center for Professionals</a></strong>\r\n                    <br />\r\n                    ab 17.01. verf&#252;gbar, 09:45\r\n                </p>\r\n            </div><!-- ./card-body -->\r\n        </div>\r\n', 'auchVerfuegbar': '', 'hinweise': None, 'count': 1, 'countStandorte': 1, 'neueAdresse': None}, 'ok': True, 'error': None}
info = code["result"]["amSchnellsten"].split("\n")
lines = list(map(lambda x: x.strip(), info))
for line in lines:
    if line.startswith("ab"):
        termin_date = re.findall("\d\d\.\d\d", line)[0]
        termin_date += ".2024" if termin_date.endswith("11") or termin_date.endswith("12") else ".2025"
        termin_time = re.findall("\d\d\:\d\d", line)[0]
        date_object = datetime.strptime(termin_date + " " + termin_time, "%d.%m.%Y %H:%M")
        print(date_object)
        break