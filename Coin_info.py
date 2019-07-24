# 给定公链项目地址，获取其每日活跃地址数，日交易量，算力，合约数量，dapp数量

# HASHRATE 算力
# TX PER DAY 日交易量
# 每日活跃地址数   https://api.blockchain.info/v2/eth/data/blocks?page=1&size=100
#
#
import requests
from lxml import etree
import time
from selenium import webdriver
from Github import Crawler
from selenium.webdriver.chrome.options import Options
import re
import datetime
import pymysql


db = pymysql.connect("202.108.211.135", "root", "DtsWdLMhm1Kv3Eck", "bcsmonitor")
cursor = db.cursor()
dapp = ["eth", "eos", "nas", "trx", "ont"]
contact = ["ETH", "EOS", "TRX", "ONT"]

class Coin():

    def __init__(self):
        options = Options()
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        options.add_argument('--headless')
        self.coin_data = {}
        self.driver = webdriver.Chrome(options=options)
        self.h = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"}
        self.addr = "https://{}.tokenview.com/v2api/chart/?coin={}&type=daily_active_address&splice=14"
        self.tokenview = "https://{}.tokenview.com/cn/"
        self.dapp = "https://dappstore.tokenview.com/cn/{}/all"

    def start(self):
        """获取算力、日交易量"""
        now_time = datetime.datetime.now()
        now_time = (now_time + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
        for i in range(1, 3):
            cursor.execute('SELECT id, github,brief_name FROM bcsmonitor.b_project where chain_type={} and github != " ";'.format(i))
            data = cursor.fetchall()

            for d in data:
                print(d)
                self.coin_data = {}
                if d[2] in contact:
                    self.coin_data["contract"] = self.get_contact(d[2])
                else:
                    self.coin_data["contract"] = 0
                self.coin_data.update(Crawler(d[2]).start())
                if i == 1:
                    brief = d[2].lower()
                    if brief == 'eos':
                        self.coin_data.update(self.eos_data())
                    else:
                        if brief == 'bsv':
                            brief = 'bchsv'
                        self.coin_data.update(self.get_tokenview(brief, now_time))
                    self.coin_data["dapps"] = self.get_dapp(brief)
                    self.save_data(i, self.coin_data, now_time, d[0])
                else:
                    self.save_data(i, self.coin_data, now_time, d[0])
                print(d[2], "完成更新")
                print(self.coin_data)

                # self.driver.close()

    def get_tokenview(self, brief_name, now_time):
        u = self.tokenview.format(brief_name)
        self.driver.get(u)
        time.sleep(2)
        data = {}
        try:
            rate = self.driver.find_element_by_xpath('//li[@class="item hashrate"]//p[2]').get_attribute(
                'textContent')
            data["rate"] = int(rate.replace("(", "").replace(")", "").replace(" ", ""))
        except Exception as e:
            data["rate"] = 0
        try:
            data["tx_day"] = self.driver.find_element_by_xpath('//li[@class="item trans"]//p[2]').get_attribute(
                'textContent')
            data["tx_day"] = int(data["tx_day"].replace(",", ""))
        except Exception as e:
            data["tx_day"] = 0
        try:
            act_num = requests.get(self.addr.format(brief_name, brief_name), headers=self.h).json()
            if not act_num["data"]:
                data["addr_num"] = 0
            else:
                for k, i in enumerate(act_num["data"]):
                    for j in i:
                        if j == str(now_time):
                            data["addr_num"] = i[j]
        except Exception as e:
            data["addr_num"] = 0
        return data

    def eos_data(self):
        data = {}
        res = requests.get("https://www.spiderdata.com/blockchains/eos").text
        data["tx_day"] = float(re.findall(r'"tx_tx_of_yesterday":(.*?),"', res)[0])
        data["addr_num"] = float(re.findall(r'"ua_of_yesterday":(.*?),"', res)[0])
        data["dapps"] = re.findall(r'"new_dapps_sum":(.*?),"', res)[0]
        data["rate"] = 0
        return data

    def get_dapp(self, brief_name):
        try:
            if brief_name not in dapp:
                return 0
            if brief_name == 'eos':
                data = self.eos_data()
                return data["dapps"]
            res = requests.get(self.dapp.format(brief_name), headers=self.h).text
            html_data = etree.HTML(res)
            dapp_num = html_data.xpath('//div[@class="total"]/p[2]/text()')
            return int(dapp_num[0])
        except Exception as e:
            return 0

    def get_contact(self, brief_name):
        if brief_name == 'TRX':
            brief_name = 'tron'
        brief_name = brief_name.lower()
        self.driver.get("https://www.spiderdata.com/blockchains/{}".format(brief_name))
        time.sleep(5)
        contact = self.driver.find_elements_by_xpath('//div[@class="blockchainheadcontent"]/div[2]/div/h3')
        str = contact[-1].get_attribute('textContent')
        if '万' in str:
            str = float(str.strip('万')) * 10000
        return int(str)

    def save_data(self, type, coin_data, now_time, id):
        db.ping()
        t_date = datetime.datetime.now()
        t_date = (t_date + datetime.timedelta(days=-2)).strftime("%Y-%m-%d")
        cursor.execute("select active_num, volume, calculate_power from b_important_track where project_id={} and track_date='{}'".format(id, now_time))
        res = cursor.fetchall()
        if res:
            return True
        if type == 2:

            cursor.execute("""INSERT INTO b_important_track(
            project_id, 
            track_date, 
            developer_num, 
            star_num, 
            fork_num, 
            submit_num) VALUES ({},'{}',{},{},{},{});
            """ .format(id, now_time, coin_data["contributors"], coin_data["star"], coin_data["fork"], coin_data["commit"]))
        else:
            cursor.execute("select active_num, volume, calculate_power from b_important_track where project_id={} and track_date='{}'".format(id, t_date))
            data = cursor.fetchone()
            active_num_trend = volume_trend = calculate_power_trend = 0
            if data:
                if data[2] and coin_data["rate"]:
                    power = re.findall(r'[0-9.]+', data[2])
                    power1 = float(power[0])
                    print(coin_data["rate"])
                    power = re.findall(r'[0-9.]+', (coin_data["rate"]))
                    power2 = float(power[0])
                    calculate_power_trend = '%.2f' % float((power2 - power1) / power1)
                else:
                    calculate_power_trend = 0
                if data[0]:
                    active_num_trend = '%.2f' % float((coin_data["addr_num"] - data[0]) / float(data[0]))
                if data[1]:
                    volume_trend = '%.2f' % float((coin_data["tx_day"] - data[1]) / float(data[1]))
            cursor.execute("""INSERT INTO b_important_track(
            project_id, 
            track_date, 
            active_num,
            active_num_trend,
            volume,
            volume_trend,
            developer_num, 
            star_num, 
            fork_num, 
            submit_num,
            calculate_power,
            calculate_power_trend,
            contract_num,
            dapp_num) VALUES ({},'{}',{},{},{},{},{},{},{},{},'{}',{},{},{});
            """ .format(id, now_time, coin_data["addr_num"], active_num_trend, coin_data["tx_day"], volume_trend, coin_data["contributors"], coin_data["star"],
                       coin_data["fork"], coin_data["commit"], coin_data["rate"], calculate_power_trend, coin_data["contract"], coin_data["dapps"]
                       ))
        db.commit()


if __name__ == '__main__':
    Coin().start()
    #
    # https://dash.tokenview.com/v2api/chart/?coin=dash&type=daily_active_address&splice=14
    # https://dash.tokenview.com/v2api/chart/?coin=xmr&type=daily_active_address&splice=14
