import re
import json
import requests
import math
from pyquery import PyQuery
from typing import List


class Linksmate:

    def __init__(self, user_address: str, password: str):
        self.cookies = self._login(user_address, password)

    def _login(self, user_address: str, password: str):
        response = requests.post(
            url="https://linksmate.jp/api/mypage/login",
            data={
                "data[mail]": user_address,
                "data[password]": password
            }
        )

        if not response.status_code == requests.codes.ok:
            raise RuntimeError("ステータスコードが20x,30xじゃないようですよ")

        return response.cookies

    def get_remain_traffic(self):
        mypage_html = self._fetch_html_text("https://linksmate.jp/mypage/")
        remain_traffic = self._scrape_remain_traffic(mypage_html)

        return remain_traffic

    def get_traffic_history_data(self):
        datahistory_html = self._fetch_html_text("https://linksmate.jp/mypage/datahistory/")
        data_history = self._scrape_recently_traffic(datahistory_html)

        return data_history

    def _fetch_html_text(self, url: str):
        response = requests.get(url, cookies=self.cookies)
        if not response.status_code == requests.codes.ok:
            raise RuntimeError("ステータスコードが20x,30xじゃないようですよ")

        return response.text

    def _scrape_remain_traffic(self, mypage_html_text: str):
        """
        残りのデータ通信量を取得する
        当月、先月からの繰越、追加分
        :param mypage_html_text:
        :return:
        """
        pq = PyQuery(mypage_html_text)
        remain_traffic = pq.find("#data > div:nth-child(1) > div.col-6.padding-right-8.padding-left-0 > div:nth-child(2) > div > div.donut-inner > span:nth-child(4)").text()
        this_month_remain_traffic = pq.find("#data > div:nth-child(1) > div.col-6.padding-right-8.padding-left-0 > div:nth-child(3) > div > table > tbody > tr:nth-child(1) > td.text-right").text()
        add_remain_traffic = pq.find("#data > div:nth-child(1) > div.col-6.padding-right-8.padding-left-0 > div:nth-child(3) > div > table > tbody > tr:nth-child(2) > td.text-right").text()
        prev_month_remain_traffic = pq.find("#data > div:nth-child(1) > div.col-6.padding-right-8.padding-left-0 > div:nth-child(3) > div > table > tbody > tr:nth-child(3) > td.text-right").text()

        return RemainTraffic(
            remain_traffic=remain_traffic,
            this_month_remain_traffic=this_month_remain_traffic,
            add_remain_traffic=add_remain_traffic,
            prev_month_remain_traffic=prev_month_remain_traffic
        )

    def _scrape_recently_traffic(self, data_history_html_text: str):
        """
        最近のデータ使用量を取得する
        jsでデータを持つ仕様になっているようなので、scriptタグから強引にデータを取得している
        :param data_history_html_text:
        :return:
        """
        m = re.search(r".*daily_traffic = (\[.*\]).*", data_history_html_text)

        return TrafficHistory.from_response_data(json.loads(m.groups()[0]))


class RemainTraffic:
    def __init__(self,
                 remain_traffic: str,
                 this_month_remain_traffic: str,
                 add_remain_traffic: str,
                 prev_month_remain_traffic: str
                 ):
        self.remain_traffic = remain_traffic
        self.this_month_remain_traffic = this_month_remain_traffic
        self.add_remain_traffic = add_remain_traffic
        self.prev_month_remain_traffic = prev_month_remain_traffic


class Traffic:
    def __init__(self, date: str, dateForDisplay: str, amount: float):
        self.date = date
        self.date_for_display = dateForDisplay
        self.amount = amount


class TrafficHistory:
    def __init__(self, history: List[Traffic]):
        self.history = history

    def head(self, n: int = 5):
        return self.history[0: n]

    @staticmethod
    def from_response_data(response_data: List):
        return TrafficHistory([Traffic(**d) for d in response_data])


if __name__ == '__main__':
    import sys
    args = sys.argv
    if not len(args) == 3:
        print("{} main_address password ッテ実行してください")
        exit(1)
    mail_address = args[1]
    password = args[2]
    linksmate = Linksmate(mail_address, password)
    remain_traffic_data = linksmate.get_remain_traffic()
    traffic_history_data = linksmate.get_traffic_history_data()

    message = """
## 残り通信量
  - 残りデータ通信残量: {remain}
  - 当月データ通信残量: {this_month}
  - 当月追加データ通信残量: {add_this_month} 
  - 繰越データ残量: {prev_month}

## 直近使用量
""".format(
        remain=remain_traffic_data.remain_traffic,
        this_month=remain_traffic_data.this_month_remain_traffic,
        add_this_month=remain_traffic_data.add_remain_traffic,
        prev_month=remain_traffic_data.prev_month_remain_traffic
    )

    for t in traffic_history_data.head():
        message += "  - {date}: {amount}MB\n".format(date=t.date_for_display, amount=math.floor(t.amount))

    print(message)

