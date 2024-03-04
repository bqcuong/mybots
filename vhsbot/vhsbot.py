import logging
import time
import yaml

import requests as requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

BOT_NAME = "VHSBot"

class VHSBot:
    __log__ = logging.getLogger(BOT_NAME)

    def __init__(self, config_file_path: str):
        with open(config_file_path, 'r') as file:
            self.config = yaml.safe_load(file)["vhsbot"]

        bot_config = self.config["telegram"]
        self.bot_token = bot_config["token"]
        self.sleep_time = bot_config["sleep_time"]  # in seconds
        self.receiver_ids = bot_config["receiver_ids"]

        self.vhs_config = self.config["vhs_api"]

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
        rsp_data = self.crawl_vhs_web(self.vhs_config["course_list_url"])

        if rsp_data is None:
            ctx.bot.send_message(ctx.job.context, "Có lỗi lúc check thông báo! Thử lại sau nhé!")
        elif rsp_data["total"] == 0:
            ctx.bot.send_message(ctx.job.context, "Chưa có gì đâu bạn ơi!\n%s" % rsp_data)
        elif rsp_data["total"] > 0:
            ctx.bot.send_message(ctx.job.context,
                                "Wow! Ngon rồi bạn ơi! Đã có lớp mới mở!\n%s" % rsp_data)
        else:
            ctx.bot.send_message(ctx.job.context, "Lỗi này là lỗi gì thì tao cũng chịu! Thử lại sau nhé!")

    def crawl_and_broadcast(self):
        rsp_data = self.crawl_vhs_web(self.vhs_config["course_list_url"])
        if rsp_data is not None and rsp_data["total"] > 0:
            self.broadcast("Wow! Ngon rồi bạn ơi! Đã có lớp mới mở!\n%s" % rsp_data)
        # else:
            # do nothing

    def crawl_vhs_web(self, course_list_url):
        try:
            url = course_list_url
            content = requests.get(url).text
            soup = BeautifulSoup(content, 'html.parser')
            course_statuses = soup.select('tr > td:nth-child(4)')

            rsp = {'total': 0, 'available_courses': []}

            for status_node in course_statuses:
                status_text = status_node.text.strip()
                if status_text != 'Voll':
                    course_node = status_node.parent
                    course_rsp = {
                        'name': course_node.select('td:nth-child(1)')[0].text.strip(),
                        'start_date': course_node.select('td:nth-child(2)')[0].text.strip(),
                        'location': course_node.select('td:nth-child(3)')[0].text.strip(),
                        'status': status_text
                    }
                    rsp['available_courses'].append(course_rsp)

            rsp['total'] = len(rsp['available_courses'])
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
    bot = VHSBot("config.yml")
    bot.launch()
