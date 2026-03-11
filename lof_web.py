import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 基础配置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
st.set_page_config(page_title="LOF T-1 精准看板", layout="wide")

# 2. 基金配置
META = {
    "160723": {"idx": "gb_799001", "tg": "原油指数"},
    "160416": {"idx": "gb_799001", "tg": "标普油气"},
    "501018": {"idx": "gb_799001", "tg": "南方原油"},
    "162411": {"idx": "gb_799001", "tg": "华宝油气"},
    "161226": {"idx": "sz399991", "tg": "白银期货"},
    "161129": {"idx": "gb_XAU", "tg": "黄金主题"}
}
FUNDS = ["160723", "160416", "501018", "162411", "161226", "161129"]

def get_sina_price():
    """获取场内价格和指数 (新浪行情接口)"""
    symbols = [f"sh{f}" if f.startswith('5') else f"sz{f}" for f in FUNDS]
    idx_symbols = list(set([m["idx"] for m in META.values()]))
    # 使用 https 协议提高稳定性
    url = f"https://hq.sinajs.cn/list={','.join(symbols + idx_symbols)}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        return {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', r.text)}
    except Exception as e:
        st.error(f"价格接口请求失败: {e}")
        return {}

def get_tt_official_nav(fid):
    """获取天天基金官方最新公布的单位净值"""
    # 接口1：移动端净值列表接口 (最准)
    url = f"https://fundmobapi.eastmoney.com/FundMApi/FundNetList.ashx?FCODE={fid}&PAGEINDEX=1&PAGESIZE=1&deviceid=123456&plat=Android"
    try:
        r = requests.get(url, timeout=10)
        res = r.json()
        if res and "Datas" in res and len(res["Datas"]) > 0:
            data = res["Datas"][0]
            return float(data['DWJZ']), data['FSRQ']
    except:
        # 接口2：备用估值接口
        try:
            url_bak = f"https://fundgz.1234
