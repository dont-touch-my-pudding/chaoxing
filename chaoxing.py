import hashlib
import json
import re
import time
from rich.table import Table
from rich.console import Console
import requests
import base64
from lxml import etree
import configparser
config_file = 'chaoxing.conf'
sess = requests.session()
console = Console()
conf = configparser.ConfigParser()
url = "http://passport2.chaoxing.com/fanyalogin"


def base64_btoa(password):
    """
    对密码进行加密
    """
    return base64.b64encode(password.encode("utf-8")).decode("utf-8")


def format_time():
    """
    初始化一个(毫秒)时间戳
    """
    return int(time.time() * 1000)


def md5value(key):
    input_name = hashlib.md5()
    input_name.update(key.encode("utf-8"))
    return (input_name.hexdigest()).lower()


def get_user():
    """
    读取配置文件
    :return: 返回读取到的用户名和密码
    """
    conf.read(config_file)
    username = conf.get('user', 'username')
    password = conf.get('user', 'password')
    return username, password


def set_user(username, password):
    """
    读取配置文件
    :param self:
    :return: 返回读取到的用户名和密码
    """
    conf.read(config_file)
    conf.set('user', 'username', username)
    conf.set('user', 'password', password)
    conf.write(open(config_file, "w"))


def login(username, password):
    """
    登录超星学习通
    :param username: 用户名
    :param password: 密码
    :return:
    """
    password = base64_btoa(password)
    headers = {
        "Referer": "http://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.chaoxing.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
    }
    data = {
        "fid": "-1",
        "uname": username,
        "password": password,
        "refer": "http%3A%2F%2Fi.chaoxing.com",
        "t": "true",
        "forbidotherlogin": "0"
    }
    result = sess.post(url, data=data, headers=headers)
    return result.json()["status"]


def get_completed_courses():
    """
    查看我的课程
    :return:
    """
    try:
        url = "http://mooc1-1.chaoxing.com/visit/courselistdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
            "Referer": "http://mooc1-1.chaoxing.com/visit/interaction?s=6ee9f45690a5ed2c5fc29427766f10b6"
        }
        data = {
            "courseType": 1,
            "courseFolderId": 0,
            "courseFolderSize": 0
        }
        response = sess.post(url, headers=headers, data=data)
        result = etree.HTML(response.text)
        title_list = [i.text for i in result.xpath(
            "//h3[@class='inlineBlock']/a/span")]
        link_list = ["https://mooc2-ans.chaoxing.com/mycourse/studentcourse?" +
                     i.split("?")[-1] for i in result.xpath("//h3[@class='inlineBlock']/a/@href")]
        table = Table(title="课程目录")
        table.add_column("编号", overflow='fold')
        table.add_column("名字", overflow='fold')
        for i, v in enumerate(title_list):  # 展示课程列表
            table.add_row(str(i), v, end_section=True)
        console.print(table)
        code_id = console.input("输入编号,输入[red]logout[/red]退出登录")
        if code_id.isdigit():
            code_id = int(code_id)
        elif code_id == "logout":
            console.log("退出登录,3秒后推出软件")
            set_user("", "")
            time.sleep(3)
            return
        try:
            get_course(title_list[code_id], link_list[code_id])
        except IndexError:
            console.input("[red]这个视频好像还没有解锁,如果解锁了,重试一遍,还不行就说明我可能生病了!!![/red]")
            get_completed_courses()
        except KeyError:
            console.input("[red]这好像不是一个视频,如果是重试一遍,如果还有问题说明我又生病了[/red]")
            get_completed_courses()
    except Exception as e:
        console.print("[red]出现严重的错误:[/red]" + str(e))
        console.print("5秒后尝试回到首页")
        time.sleep(5)
        get_completed_courses()


def get_course(title, link):
    """
    获取选则课程的所有课程目录
    :param title: 获取选则课程的标题
    :param link: 获取选则课程的链接
    :return:
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
    }
    console.print(f"当前课程是{title},链接为{link}")
    response = sess.get(link, headers=headers)
    result = etree.HTML(response.text)
    title_list = [i.strip() for i in result.xpath(
        "//div[@class='chapter_item']/@title") if i.strip()]
    link_list = [i for i in result.xpath(
        "//div[@class='chapter_item']/@onclick")]
    # title_list = [i.strip() for i in result.xpath(
    #     "//div[@class='catalog_level']/ul/li/div[@class='chapter_item']/@title") if i.strip()]
    # link_list = [i for i in result.xpath(
    #     "//div[@class='catalog_level']/ul/li/div[@class='chapter_item']/@onclick")]
    # result_list = [i.strip() for i in result.xpath(
    #     "//div[@class='catalog_level']/ul/li/div[@class='chapter_item']/div[@class='catalog_title']/div[@class='catalog_task']//span[@class='bntHoverTips']/text()")]
    table = Table(title=f"课程{title}目录")
    table.add_column("编号", overflow='fold')
    table.add_column("名字", overflow='fold')
    for i, v in enumerate(title_list):
        table.add_row(str(i), v, end_section=True)
    console.print(table)
    choose = input("请选则一件通过的课程,输入非数字回到首页")
    if not choose.isdigit():
        get_completed_courses()
        return
    choose = int(choose)
    is_passed, title_child = get_uri_dir_params(
        title_list[choose], link_list[choose])
    if is_passed:
        console.print(title_child + "已通过")
    else:
        console.print(title_child + "通过失败")
    console.input("回车回到选课界面")
    get_course(title, link)


def get_uri_dir_params(title, link):
    courseid, knowledgeid, clazzid = re.findall(
        "toOld\('(.*?)', '(.*?)', '(.*?)'\)", link)[0]
    url = f"http://mooc1.chaoxing.com/knowledge/cards?clazzid={clazzid}&courseid={courseid}&knowledgeid={knowledgeid}"
    console.print(f"当前课程为{title}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "Referer": link
    }
    response = sess.get(url, headers=headers)
    big_json = json.loads(re.findall("mArg = (.*?);", response.text)[1])
    attachments_json = big_json["attachments"]
    defaults_json = big_json["defaults"]
    otherInfo = attachments_json[0]["otherInfo"]
    jobid = attachments_json[0]["jobid"]
    objectid = attachments_json[0]["property"]["objectid"]
    cpi = defaults_json["cpi"]
    userid = defaults_json["userid"]
    duration, dtoken = get_video_info(objectid)
    is_passed = send_request_demo(
        cpi, dtoken, clazzid, duration, objectid, otherInfo, jobid, userid)
    return is_passed, title


def get_video_info(objectid):
    url = f"https://mooc1-1.chaoxing.com/ananas/status/{objectid}"
    params = {"k": "6237",
              "flag": "normal",
              "_dc": "1629633101301"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "Referer": "https://mooc1-1.chaoxing.com/ananas/modules/video/index.html?v=2021-0618-1850"
    }
    result = sess.get(url, headers=headers, params=params).json()
    duration = result["duration"]  # 视频时长
    dtoken = result["dtoken"]  # url必要路径
    return duration, dtoken


def send_request_demo(cpi, dtoken, clazzid, duration, objectid, otherInfo, jobid, userid):
    """
    发送通过请求,将播放时长设置成为视频的最大时间,以通过视频
    """
    url = f"https://mooc1.chaoxing.com/multimedia/log/a/{cpi}/{dtoken}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62",
        "Referer": "http://mooc1.chaoxing.com/ananas/modules/video/index.html?v=2021-1216-1435"
    }
    data = {
        "clazzId": clazzid,
        "playingTime": duration,
        "duration": duration,
        "clipTime": f"0_{duration}",
        "objectId": objectid,
        "otherInfo": otherInfo,
        "jobid": jobid,
        "userid": userid,
        "isdrag": 0,
        "view": "pc",
        "enc": "",
        "rt": "0.9",
        "dtype": "Video",
        "_t": format_time(),
    }
    format = "[%s][%s][%s][%s][%s][%s][%s][%s]" % (
        data["clazzId"], data["userid"], data["jobid"], data["objectId"], data["playingTime"] *
        1000, "d_yHJ!$pdA~5",
        data["duration"] * 1000, data["clipTime"])
    enc = md5value(format)
    data["enc"] = enc
    result = sess.get(url, headers=headers, params=data)
    return result.json()["isPassed"]


username, password = get_user()  # 获取配置文件的登录用户名
if username and password:
    status = login(username, password)
else:
    username = console.input("输入[blue]用户名[/blue]")
    password = console.input("输入[blue]密码[/blue]")
    status = login(username, password)
    if status:  # 判断登陆成功,将用户名保存到本地配置文件
        set_user(username, password)

if status:
    console.log("用户已登陆")
    get_completed_courses()
else:
    console.log("用户名或者密码错误")
