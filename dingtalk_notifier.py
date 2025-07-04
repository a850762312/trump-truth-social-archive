import json
import os
import requests
from datetime import datetime, timezone, timedelta

from alibabacloud_dingtalk.oauth2_1_0.client import Client as DingTalkOAuth2Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalk_oauth2_models
from alibabacloud_tea_util.client import Client as UtilClient
import random
from googletrans import Translator
import time
class DingTalkService:
    """钉钉API服务类，处理钉钉开放平台接口调用"""

    def __init__(self):
        self.app_key = os.getenv('DINGTALK_APP_KEY')
        self.app_secret = os.getenv('DINGTALK_APP_SECRET')
        self.open_conversation_id = os.getenv('DINGTALK_OPEN_CONVERSATION_ID')
        self.robot_code = os.getenv('DINGTALK_ROBOT_CODE')

    @staticmethod
    def create_client() -> DingTalkOAuth2Client:
        """
        创建钉钉OAuth2客户端实例

        Returns:
            DingTalkOAuth2Client: 钉钉OAuth2客户端实例
        """
        config = open_api_models.Config()
        config.protocol = 'https'
        config.region_id = 'central'
        return DingTalkOAuth2Client(config)

    def get_access_token(self):
        """
        获取钉钉应用的access_token

        Returns:
            str: 成功返回access_token，失败返回None
        """
        client = self.create_client()

        get_access_token_request = dingtalk_oauth2_models.GetAccessTokenRequest(
            app_key=self.app_key,
            app_secret=self.app_secret
        )

        try:
            response = client.get_access_token(get_access_token_request)
            access_token = response.body.access_token
            print(f"获取access_token成功: {access_token}")
            return access_token
        except Exception as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                print(f"获取access_token失败: [{err.code}] {err.message}")
            else:
                print(f"获取access_token失败: {str(err)}")
            return None

    def send_message(self, access_token, message):
        """
        发送钉钉群机器人消息

        参数说明：
        access_token: 调用凭证
        message: 要发送的消息内容
        """
        url = "https://api.dingtalk.com/v1.0/robot/groupMessages/send"

        headers = {
            "Content-Type": "application/json",
            "x-acs-dingtalk-access-token": access_token
        }

        # 构造请求体
        payload = {
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": message}, ensure_ascii=False)
        }

        # 添加可选参数
        if self.open_conversation_id:
            payload["openConversationId"] = self.open_conversation_id
        if self.robot_code:
            payload["robotCode"] = self.robot_code

        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8')
            )

            # 调试信息
            print(f"请求URL: {url}")
            print(f"请求头: {headers}")
            print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            raise Exception(f"HTTP错误: {err}\n响应内容: {response.text}")
        except Exception as err:
            raise Exception(f"请求失败: {str(err)}")


def load_json_data(file_path):
    """加载JSON数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"文件 {file_path} 不存在")
        return []
    except json.JSONDecodeError:
        print(f"文件 {file_path} 格式错误")
        return []


def save_json_data(file_path, data):
    """保存JSON数据"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_sent_ids(file_path):
    """加载已发送的ID列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_sent_ids(file_path, sent_ids):
    """保存已发送的ID列表"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sent_ids, f, ensure_ascii=False, indent=2)


def format_message(created_at, content):
    """格式化消息"""
    # 转换时间格式并转换为北京时间 (UTC+8)
    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    beijing_tz = timezone(timedelta(hours=8))
    beijing_time = dt.astimezone(beijing_tz)
    formatted_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S')

    # 修复转义引号：将错误编码的字符恢复为正常引号
    fixed_content = content.encode('latin-1').decode('utf-8', errors='ignore')

    # 翻译内容
    translated_content = translate_to_chinese(fixed_content)

    # 如果翻译成功，添加到消息末尾
    if translated_content and translated_content != fixed_content:
        return f"🕐 {formatted_time} (北京时间)\n\n{fixed_content}\n\n📝 中文翻译：\n{translated_content}"
    else:
        return f"🕐 {formatted_time} (北京时间)\n\n{fixed_content}"


def translate_to_chinese(text):
    """将英文翻译成中文"""
    try:
        translator = Translator()
        # 添加随机延迟避免请求过快
        time.sleep(random.uniform(0.5, 1.5))

        # 检测语言并翻译
        detection = translator.detect(text)
        if detection.lang == 'zh' or detection.lang == 'zh-cn':
            # 如果已经是中文，直接返回
            return None

        result = translator.translate(text, dest='zh-cn')
        print(result)
        return result.text
    except Exception as e:
        print(f"翻译失败: {e}")
        # 翻译失败时返回None，不影响原消息发送


def main():
    # 文件路径
    data_file = 'data/truth_archive.json'
    sent_ids_file = 'data/sent_ids.json'

    # 加载数据
    truth_data = load_json_data(data_file)
    sent_ids = load_sent_ids(sent_ids_file)

    if not truth_data:
        print("没有数据可处理")
        return

    # 初始化钉钉服务
    dingtalk_service = DingTalkService()
    access_token = dingtalk_service.get_access_token()

    if not access_token:
        print("无法获取钉钉访问令牌")
        return

    # 筛选新内容
    new_posts = []
    for post in truth_data[-15:]:
        if post['id'] not in sent_ids:
            new_posts.append(post)

    if not new_posts:
        print("没有新内容需要推送")
        return

    print(f"发现 {len(new_posts)} 条新内容")

    # 按时间排序（最新的在后面）
    new_posts.sort(key=lambda x: x['created_at'])

    # 修改main()函数中的发送逻辑部分
    newly_sent_ids = []
    for post in new_posts:
        # 检查内容是否为空
        if not post['content'] or post['content'].strip() == '':
            print(f"跳过空内容的帖子: {post['id']}")
            continue

        message = format_message(post['created_at'], post['content'])
        try:
            result = dingtalk_service.send_message(access_token, message)
            print(f"发送消息结果: {result}")
            # 更新判断逻辑：适配钉钉实际响应格式
            if result and ('processQueryKey' in result or 'requestId' in result):
                print(f"成功发送消息: {post['id']}")
                newly_sent_ids.append(post['id'])
            else:
                print(f"发送消息失败: {result}")
                break  # 如果发送失败，停止发送剩余消息
        except Exception as e:
            print(f"发送消息时出错: {e}")
            break

    # 更新已发送ID列表
    if newly_sent_ids:
        sent_ids.extend(newly_sent_ids)
        save_sent_ids(sent_ids_file, sent_ids)
        print(f"成功发送 {len(newly_sent_ids)} 条消息")


if __name__ == "__main__":
    main()
