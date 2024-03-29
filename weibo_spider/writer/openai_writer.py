import logging
import sys
from datetime import datetime, timedelta
import requests
from .writer import Writer

logger = logging.getLogger('spider.openai_writer')


class OpenAIWriter(Writer):
    def __init__(self, filter):
        logger.info('OpenAIWriter init')


    def write_user(self, user):
        self.user = user



    def write_weibo(self, weibo):
        """将爬取的信息写入txt文件"""

        try:
            url =   'http://127.0.0.1:8000/msg/new'
            for w in weibo:
                try :
                    sendTime = w.__dict__['publish_time']
                    #sendTime 转为时间戳
                    datetime_obj = datetime.strptime(sendTime, "%Y-%m-%d %H:%M")
                    timestamp = datetime_obj.timestamp()
                    data = {
                        "content": w.__dict__['content'],
                        "user": self.user.__dict__['nickname'],
                        "room": "",
                        "time": timestamp,
                        "source": "微博"
                    }
                    response = requests.post(url, json=data)
                    logger.info(u'%s信息写入openai完毕, res:%s', self.user.__dict__['nickname'], response.text)
                except Exception as e:
                    logger.exception(e)

        except Exception as e:
            logger.exception(e)
