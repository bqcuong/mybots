# MofaBot
## Introduction
A Telegram bot that helps you to keep looking for signature status (introduced or not) of the employee in your local government authority (who signed your documents) in the  public service system of VN MOFA - Consular Department.
The purpose of this bot is related to the application for [CERTIFICATION/LEGALISATION OF DOCUMENTS (CHỨNG NHẬN LÃNH SỰ/HỢP PHÁP HÓA LÃNH SỰ)](https://hopphaphoa.lanhsuvietnam.gov.vn/Legalization/Legalized-Introduction.aspx) at MOFA, for people being less lucky like me. 
It might not help us much with our application process but give me a chance to put my trust in the authority.

## Installation (Linux)
MofaBot requires Python 3.7+ for running and Pip 20+. You can download and install Python3 from [here](https://www.python.org/downloads/), and Pip from [here](https://pip.pypa.io/en/stable/installation/).
Then you could create a virtual environment and install the dependencies if you do not want them to exist as your machine's system files, 
otherwise, you can ignore this step.

First, clone this repository:
```
$ git clone https://github.com/bqcuong/mofabot.git /opt/mofabot
```

Then, install the dependencies:

```
$ cd /opt/mofabot
$ pip install -r requirements.txt
```

Next, install the service to your Linux machine by coping it to `/etc/systemd/system` directory. 
You could configure the service file as you like.
```
$ cp mofabot.service /etc/systemd/system/mofabot.service
```
## Configuration
Before running MofaBot for the first time, copy the `config.yml.sample` to `config.yml`. 
The `telegram` and `mofa_api` sections are required to filled. 
```
mofabot:
  # Configurations for your telegram bot.
  # For creating a new bot, check https://core.telegram.org/bots#6-botfather, easy as piece of cake
  # <token> is the token of your bot after you created it with BotFather
  # <sleep_time> in seconds between the loop iterations for checking result
  # <receiver_ids> are the initial id list of the users you want to send the message to, you could leave it empty
  telegram:
    token: ""
    sleep_time: 3600
    receiver_ids:
      - 123456789

  # Parameters for the request to Mofa API for checking our result
  # <gov_agency_name> is the name of authority you want to check, e.g., UBND H. AbC, T. XyZ
  # <employee_name> is the name of the authority employee whose F*CKING SIGNATURE hasn't been updated to the Mofa system,
  #   e.g., NGUYỄN VĂN PHÈN
  # <group_id> is the required header for the request to Mofa API, you can get it by inspecting the request header
  # when you are filling the form at https://dichvucong.mofa.gov.vn/web/cong-dich-vu-cong-bo-ngoai-giao/to-khai-truc-tuyen
  mofa_api:
    gov_agency_name: ""
    employee_name: ""
    group_id: ""
```
## Usage

### Server side
To run MofaBot service on your server machine, you could run the following command:
```
$ systemctl start mofabot
```
And stop the service
```
$ systemctl stop mofabot
```
To see the running logs, check the file `/var/log/mofabot.log`
```
$ tail -f /var/log/mofabot.log
```

### Client side
After running your bot on server side, you could test the bot by sending several commands via Telegram messages:

- `/subscribe`: to subscribe for receiving notifications of signature status from the bot, the `receiver_ids` list you put in `config.yml` is automatically added to the list of subscribers
- `/unsubscribe`: as clear as day, to unsubscribe you from the subscriber list
- `/check`: perform an immediate check of the signature status and send the result back to you right after that

*The below message is what you will get if your lucky day has come:*
```
Ôh ồh ôh Ôh ồh! Ngon rồi bạn ơi! Chữ ký đã được giới thiệu!
{'total': 1, 'data': [{'MA_CQQL': '12xxx', 'TEN_CHUC_VU': 'Chủ tịch UBND', 'MA_CHUC_VU': 'xxxx', 'MA': 'abc123xxx', 'TEN': 'Nguyễn Văn Phèn', 'TEN_CQQL': 'UBND H. AbC, T. XyZ'}]}
```

## Contributing
Pull requests are welcome, as well as issues. Fixing/Improving the documentation is highly appreciated. 

*Fact: Half of the effort to write this README file was contributed by [Github Copilot](https://copilot.github.com/).*  
