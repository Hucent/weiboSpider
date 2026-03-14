import logging
import os
from datetime import datetime
from urllib.parse import urlparse

import requests

from .writer import Writer

logger = logging.getLogger('spider.openai_writer')

API_URL = 'http://127.0.0.1:8000/msg/new'
IMAGE_ROOT = os.path.join(os.getcwd(), 'tmp_images')


class OpenAIWriter(Writer):
    def __init__(self, filter):
        logger.info('OpenAIWriter init')
        self.session = requests.Session()
        self.filter = filter
        self.user = None

    def write_user(self, user):
        self.user = user

    def ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)

    def sanitize_name(self, value, fallback='unknown'):
        if not value:
            return fallback
        safe = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(value))
        safe = safe.strip('_')
        return safe or fallback

    def get_day_key(self, timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%Y%m%d')

    def pick_image_urls(self, w):
        urls = []
        original = getattr(w, 'original_pictures', None) or []
        retweet = getattr(w, 'retweet_pictures', None) or []
        if original:
            urls.extend(original)
        elif retweet:
            urls.extend(retweet)
        return [url for url in urls if url]

    def get_image_ext(self, image_url):
        try:
            parsed = urlparse(image_url)
            _, ext = os.path.splitext(parsed.path)
            return ext or '.jpg'
        except Exception:
            return '.jpg'

    def download_images(self, w, timestamp):
        image_urls = self.pick_image_urls(w)
        logger.info('weibo image url count: %s weibo_id: %s', len(image_urls), getattr(w, 'id', None))
        if not image_urls:
            return []

        day_dir = os.path.join(IMAGE_ROOT, self.get_day_key(timestamp))
        self.ensure_dir(day_dir)

        safe_user = self.sanitize_name(getattr(self.user, 'nickname', None), 'weibo_user')
        safe_weibo_id = self.sanitize_name(getattr(w, 'id', None), 'weibo')
        saved_paths = []

        for index, image_url in enumerate(image_urls, start=1):
            ext = self.get_image_ext(image_url)
            file_name = f"{int(timestamp)}_{safe_user}_{safe_weibo_id}_{index}{ext}"
            file_path = os.path.join(day_dir, file_name)
            try:
                response = self.session.get(image_url, timeout=30)
                response.raise_for_status()
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                saved_paths.append(file_path)
                logger.info('weibo saved image: %s', file_path)
            except Exception as e:
                logger.exception('weibo download image error: %s', image_url)
                logger.exception(e)
        return saved_paths

    def get_message_type(self, content, image_paths):
        has_text = bool(content and str(content).strip())
        has_images = bool(image_paths)
        if has_text and has_images:
            return 'mixed'
        if has_images:
            return 'image'
        return 'text'

    def write_weibo(self, weibo):
        try:
            for w in weibo:
                try:
                    send_time = getattr(w, 'publish_time', '')
                    datetime_obj = datetime.strptime(send_time, "%Y-%m-%d %H:%M")
                    timestamp = datetime_obj.timestamp()
                    content = getattr(w, 'content', '') or ''
                    image_paths = self.download_images(w, timestamp)
                    payload = {
                        "content": content,
                        "user": getattr(self.user, 'nickname', '微博用户'),
                        "room": "",
                        "time": timestamp,
                        "source": "微博",
                        "message_type": self.get_message_type(content, image_paths),
                        "image_paths": image_paths,
                        "caption": content or None,
                    }
                    logger.info('weibo posting payload: %s', {
                        'user': payload['user'],
                        'message_type': payload['message_type'],
                        'image_count': len(payload['image_paths']),
                        'time': payload['time'],
                        'weibo_id': getattr(w, 'id', None),
                    })
                    response = self.session.post(API_URL, json=payload, timeout=30)
                    logger.info('%s信息写入openai完毕, res:%s', getattr(self.user, 'nickname', '微博用户'), response.text)
                except Exception as e:
                    logger.exception(e)
        except Exception as e:
            logger.exception(e)
