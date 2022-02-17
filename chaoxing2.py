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


def get_headers(referer):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
    }
    if referer:
        headers["Referer"] = referer
        return headers
    else:
        return headers


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
    headers = get_headers("http://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.chaoxing.com")
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
    获取进行中的课程
    """
    courses_url = "http://cust.jxjy.chaoxing.com/studyApp/studying"
    response = sess.get(courses_url, headers=get_headers(None))
    result_list = re.findall("autoLoadXqkc\('(.*?)', '(.*?)'\);", response.text)
    for xqid, page in result_list:
        courses_once = f"http://cust.jxjy.chaoxing.com/studyApp/getXskc?xqid={xqid}&page={page}"
        print(courses_once)
        rsp = sess.get(courses_once, headers=get_headers(courses_url))
        match_result = re.match("^<script>", rsp.text.strip())
        if not match_result:
            dom = etree.HTML(rsp.text)
            print(dom.xpath("//a[text()='进入学习']/@href")[0])


def create_table(title, *args, **kwargs):
    """创捷一个table,用于展示目录结构"""
    table = Table(title=title)
    for arg in args:
        table.add_column(arg, overflow='fold')
    if len(kwargs.values()) == 1:
        for i, value in enumerate(list(kwargs.values())[0]):
            table.add_row(str(i), value, end_section=True)
    elif len(kwargs.values()) == 2:
        for i, (value1, value2) in enumerate(zip(list(kwargs.values())[0], list(kwargs.values())[1])):
            table.add_row(str(i), value1, str(value2), end_section=True)
    console.print(table)


def get_courses():
    """
    获取课程
    """
    url = "http://mooc1-2.chaoxing.com/visit/courses"
    rsp = sess.get(url, headers=get_headers(None))
    dom = etree.HTML(rsp.text)
    courses_link = dom.xpath("//a[@class='courseName']/@href")
    courses_title = dom.xpath("//a[@class='courseName']/@title")
    courses_link = ["http://mooc1.chaoxing.com" + i for i in courses_link]
    create_table("我的课程", "编号", "名字", courses_title=courses_title)
    index = int(input("输入序号选择课程"))
    get_class_hours(courses_title[index], courses_link[index])


g_title = None
g_link = None


def get_class_hours_info(prent_div):
    l_class_hours_title = []
    l_class_hours_link = []
    l_class_hours_state = []
    div_levelthrees = prent_div.xpath("./div[contains(@class,'level')]")
    div_levelthreesh3 = prent_div.xpath("./h3[@class='clearfix']")
    for div_levelthree in div_levelthreesh3:
        class_hours_title = div_levelthree.xpath("./a/span[@class='articlename']/@title")[0]
        class_hours_link = div_levelthree.xpath("./a/@href")[0]
        class_hours_state = div_levelthree.xpath("./a/span[@class='icon']/em[@class='orange']/text()")[
                                0] + "个任务" if div_levelthree.xpath(
            "./a/span[@class='icon']/em[@class='orange']") else "已完成"
        l_class_hours_title.append(class_hours_title)
        l_class_hours_link.append(class_hours_link)
        l_class_hours_state.append(class_hours_state)
    if div_levelthrees:
        for div_levelthree in div_levelthrees:
            ll_class_hours_title, ll_class_hours_link, ll_class_hours_state = get_class_hours_info(div_levelthree)
            for class_hours_title, class_hours_link, class_hours_state in zip(ll_class_hours_title, ll_class_hours_link,
                                                                              ll_class_hours_state):
                l_class_hours_title.append(class_hours_title)
                l_class_hours_link.append(class_hours_link)
                l_class_hours_state.append(class_hours_state)

    return l_class_hours_title, l_class_hours_link, l_class_hours_state


def get_class_hours(title, link):
    global g_title, g_link
    """
    获取课时
    """
    g_title, g_link = title, link
    print(f"当前选择的课程为:{title},链接为:{link}")
    resp = sess.get(link, headers=get_headers(None))
    dom = etree.HTML(resp.text)
    prent_div_list = dom.xpath("//div[@class='leveltwo']")
    class_hours_title_list = []
    class_hours_link_list = []
    class_hours_state_list = []
    for prent_div in prent_div_list:
        l_class_hours_title, l_class_hours_link, l_class_hours_state = get_class_hours_info(prent_div)
        for class_hours_title, class_hours_link, class_hours_state in zip(l_class_hours_title, l_class_hours_link,
                                                                          l_class_hours_state):
            class_hours_title_list.append(class_hours_title)
            class_hours_link_list.append(class_hours_link)
            class_hours_state_list.append(class_hours_state)
        # div_levelthrees = prent_div.xpath("./div[@class='levelthree']")
        # if not div_levelthrees:
        #     class_hours_title = prent_div.xpath("./h3[@class='clearfix']/a/span[@class='articlename']/@title")[0]
        #     class_hours_link = prent_div.xpath("./h3[@class='clearfix']/a/@href")[0]
        #     class_hours_state = \
        #         prent_div.xpath("./h3[@class='clearfix']/a/span[@class='icon']/em[@class='orange']/text()")[
        #             0] + "个任务待完成" if \
        #             prent_div.xpath("./h3[@class='clearfix']/a/span[@class='icon']/em[@class='orange']") else "任务已完成"
        #     class_hours_title_list.append(class_hours_title)
        #     class_hours_link_list.append(class_hours_link)
        #     class_hours_state_list.append(class_hours_state)
        # else:
        #     class_hours_title = prent_div.xpath("./h3[@class='clearfix']/a/span[@class='articlename']/@title")[0]
        #     class_hours_link = prent_div.xpath("./h3[@class='clearfix']/a/@href")[0]
        #     class_hours_state = \
        #         prent_div.xpath("./h3[@class='clearfix']/a/span[@class='icon']/em[@class='orange']/text()")[
        #             0] + "个任务待完成" if \
        #             prent_div.xpath("./h3[@class='clearfix']/a/span[@class='icon']/em[@class='orange']") else "任务已完成"
        #     class_hours_title_list.append(class_hours_title)
        #     class_hours_link_list.append(class_hours_link)
        #     class_hours_state_list.append(class_hours_state)
        #     div_levelthreesh3 = div_levelthrees[0].xpath("./h3[@class='clearfix']")
        #     for div_levelthree in div_levelthreesh3:
        #         class_hours_title = div_levelthree.xpath("./a/span[@class='articlename']/@title")[0]
        #         class_hours_link = div_levelthree.xpath("./a/@href")[0]
        #         class_hours_state = prent_div.xpath("./a/span[@class='icon']/em[@class='orange']/text()")[
        #             0] if prent_div.xpath("./a/span[@class='icon']/em[@class='orange']") else 0
        #         class_hours_title_list.append(class_hours_title)
        #         class_hours_link_list.append(class_hours_link)
        #         class_hours_state_list.append(class_hours_state)
    create_table(f"{title}课时", "编号", "名字", "状态", class_hours_title_list=class_hours_title_list,
                 class_hours_state_list=class_hours_state_list)
    index = int(input("输入需要刷的课时id"))
    get_class_info(class_hours_title_list[index], class_hours_link_list[index])


def get_tab_number(link, chapterId, courseId, clazzid):
    link = "http://mooc1.chaoxing.com" + link
    url = "http://mooc1.chaoxing.com/mycourse/studentstudyAjax"
    data = {
        "courseId": courseId,
        "clazzid": clazzid,
        "chapterId": chapterId,
        "cpi": 0,
        "verificationcode": ""
    }
    response = sess.post(url, data=data, headers=get_headers(link))
    dom = etree.HTML(response.text)
    tabs = dom.xpath("//div[@class='tabtags']/span")
    return len(tabs)


def get_class_info(title, link):
    """
    课时信息
    """
    print(f"当前选择的课时为:{title},链接为:{link}")
    chapterId, courseId, clazzid, enc = re.findall("\?chapterId=(.*?)&courseId=(.*?)&clazzid=(.*?)&enc=(.*?)", link)[0]
    num = get_tab_number(link, chapterId, courseId, clazzid)
    for i in range(num):
        url = f"http://mooc1.chaoxing.com/knowledge/cards?clazzid={clazzid}&courseid={courseId}&knowledgeid={chapterId}&num={i}"
        response = sess.get(url, headers=get_headers("http://mooc1.chaoxing.com" + link))
        info = json.loads(re.findall("mArg = (.*?);", response.text)[1])
        attachments_json_list = info["attachments"]
        defaults_json = info["defaults"]
        fid = defaults_json["fid"]
        cpi = defaults_json["cpi"]
        userid = defaults_json["userid"]
        for attachments_json in attachments_json_list:
            try:
                if attachments_json["property"]["type"] == ".mp4":
                    objectid = attachments_json["property"]["objectid"]
                    jobid = attachments_json["jobid"]
                    otherInfo = attachments_json["otherInfo"]
                    duration, dtoken = get_video_info(objectid, fid)
                    is_passed = send_request_demo(
                        cpi, dtoken, clazzid, duration, objectid, otherInfo, jobid, userid)
                    if is_passed:
                        console.print(title + "已通过")
                    else:
                        console.print(title + "通过失败")
            except KeyError:
                console.print("未知错误")
    console.input("回车回到选课界面")
    get_class_hours(g_title, g_link)


def get_video_info(objectid, fid):
    url = f"https://mooc1-1.chaoxing.com/ananas/status/{objectid}"
    params = {"k": fid,
              "flag": "normal",
              "_dc": format_time()}
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


if __name__ == '__main__':
    username, password = get_user()
    if not username and not password:  # 判断用户名和密码不存在的时候
        username = console.input("输入[red]用户名[/red]")
        password = console.input("输入[red]密码[/red]")
    result = login(username, password)
    if result:  # 登陆成功,保存用户名和密码到conf文件
        set_user(username, password)
    get_courses()
