from datetime import datetime
import logging
import re
import time
import yaml

import requests as requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

BOT_NAME = "HHSBot"

class HHSBot:
    __log__ = logging.getLogger(BOT_NAME)

    def __init__(self, config_file_path: str):
        with open(config_file_path, 'r') as file:
            self.config = yaml.safe_load(file)["hhsbot"]

        bot_config = self.config["telegram"]
        self.bot_token = bot_config["token"]
        self.sleep_time = bot_config["sleep_time"]  # in seconds
        self.receiver_ids = bot_config["receiver_ids"]

        self.hhs_config = self.config["hhs_api"]

        self.updater = None
        self.setup()

    def launch(self):
        while True:
            self.crawl_and_broadcast()
            time.sleep(self.sleep_time)

    def setup(self):
        self.updater = Updater(self.bot_token)
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(CommandHandler("subscribe", self.subscribe))
        dispatcher.add_handler(CommandHandler("unsubscribe", self.unsubscribe))
        dispatcher.add_handler(CommandHandler("check", self.check))

        self.updater.start_polling()

    def subscribe(self, update: Update, context: CallbackContext) -> None:
        new_chat_id = update.message.chat_id
        if new_chat_id not in self.receiver_ids:
            self.receiver_ids.append(new_chat_id)
            update.message.reply_text("Đăng ký nhận thông báo từ {} thành công!".format(BOT_NAME))
        else:
            update.message.reply_text("Bạn đã đăng ký rồi mà???")

    def unsubscribe(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.message.chat_id
        if chat_id in self.receiver_ids:
            self.receiver_ids.remove(chat_id)
            update.message.reply_text("Hủy nhận thông báo từ {} thành công!".format(BOT_NAME))
        else:
            update.message.reply_text("Bạn đã đăng ký đâu mà đòi hủy???")

    def check(self, update: Update, context: CallbackContext) -> None:
        jq = self.updater.dispatcher.job_queue
        chat_id = update.message.chat_id
        self.remove_job_if_exists(str(chat_id), jq)

        jq.run_once(self.run_check, 0, context=chat_id, name=str(chat_id))

    def run_check(self, ctx: CallbackContext) -> None:
        rsp_data = self.crawl_data()

        if rsp_data is None:
            ctx.bot.send_message(ctx.job.context, "Có lỗi lúc check thông báo! Thử lại sau nhé!")
        else:
            ctx.bot.send_message(ctx.job.context, "Thông tin termin mới nhất ở đây nhé!\n%s" % rsp_data)

    def crawl_and_broadcast(self):
        rsp_data = self.crawl_data()
        if rsp_data is not None and rsp_data["notified"] > 0:
            self.broadcast("Wow! Ngon rồi bạn ơi! Đã có termin mới ngon hơn!\n%s" % rsp_data)
        # else:
            # do nothing

    def crawl_data(self):
        try:
            cookies = {
                "NfkParameters": '{"ServiceShortName":"DigiTermin","Ars":"020000000000","LeikaId":""}',
                "DigiTermin": self.hhs_config["digitermin_id"],
                "__RequestVerificationToken_" + self.hhs_config["cookie_verify_token_key"]: self.hhs_config["cookie_verify_token_value"]
            }

            # Step 1: Obtain CSRF Token
            url = self.hhs_config["kundenzentrum_url"]
            content = requests.get(url, cookies=cookies).text
            soup = BeautifulSoup(content, 'html.parser')
            csrf_token_input = soup.find_all(lambda t: t.name == "input" and t.has_attr("name") and "__RequestVerificationToken" in t.get("name"))

            if len(csrf_token_input) == 0:
                raise Exception("Could not obtain the CSRF token!")

            rsp = {'notified': 0, 'am_schnellsten': ''}
            csrf_token = csrf_token_input[0].get("value")

            # Step 2: Request TerminSuchen API
            url = self.hhs_config["terminsuchen_url"]
            request_body = {
                "__RequestVerificationToken": csrf_token,
                "GewuenschterTermin.VonTag": datetime.now().strftime("%d.%m.%Y"),
                "GewuenschterTermin.ZeitraumVon": "07:00",
                "GewuenschterTermin.ZeitraumBis": "19:00",
                "GewuenschterTermin.MoeglicherTagMontag": "false",
                "GewuenschterTermin.MoeglicherTagDienstag": "false",
                "GewuenschterTermin.MoeglicherTagMittwoch": "false",
                "GewuenschterTermin.MoeglicherTagDonnerstag": "false",
                "GewuenschterTermin.MoeglicherTagFreitag": "false",
                "GewuenschterTermin.MoeglicherTagSamstag": "false",
                "GewuenschterTermin.MoeglicherTagSonntag": "false",
                "HasOrtsteilbezug": "False"
            }
            rsp_json = requests.post(url, cookies=cookies, data=request_body).json()
            info = rsp_json["result"]["amSchnellsten"].split("\n")
            lines = list(map(lambda x: x.strip(), info))
            for line in lines:
                if line.startswith("ab"):
                    termin_date = re.findall("\d\d\.\d\d", line)[0]
                    termin_date += ".2024" if termin_date.endswith("11") or termin_date.endswith("12") else ".2025"
                    termin_time = re.findall("\d\d\:\d\d", line)[0]
                    rsp['am_schnellsten'] = termin_date + " " + termin_time
                    am_schnellsten_termin = datetime.strptime(termin_date + " " + termin_time, "%d.%m.%Y %H:%M")
                    current_termin = datetime.strptime(self.hhs_config["current_termin"], "%d.%m.%Y")
                    if am_schnellsten_termin < current_termin:
                        rsp['notified'] = 1
                    break
            return rsp

        except Exception as e:
            self.__log__.error("Error when crawling the web API %s", e)
            raise(e)
            return None

    def broadcast(self, message):
        if self.receiver_ids is None:
            return
        for chat_id in self.receiver_ids:
            # broadcasting messages should go with the job queue
            jq = self.updater.dispatcher.job_queue
            self.remove_job_if_exists(str(chat_id), jq)
            jq.run_once(lambda ctx: ctx.bot.send_message(ctx.job.context, message), 0, context=chat_id, name=str(chat_id))

    @staticmethod
    def remove_job_if_exists(name: str, job_queue: JobQueue) -> bool:
        """Remove job with given name. Returns whether job was removed."""
        current_jobs = job_queue.get_jobs_by_name(name)
        print("-----> ", current_jobs)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True


if __name__ == '__main__':
    bot = HHSBot("config.yml")
    bot.launch()
