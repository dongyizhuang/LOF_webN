import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 时间与页面配置
beijing_tz = timezone(timedelta(hours=8))
now_bj = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
st.set_page_config(page_title="LOF专业监控", layout="wide")

# 2. 核心配置：关联基金与指数 (T-1涨幅参考)
FUND_META = {
    "160723": {"idx": "gb_799001", "tg": "原油指数", "fe": "1.50%"},
    "160416": {"idx": "gb_799001", "tg": "标普油气", "fe": "1.50%"},
    "501018": {"idx": "gb_799001", "tg": "南方原油", "fe": "1.50%"},
    "162411": {"idx": "gb_XBI", "tg": "标普生物", "fe": "1.20%"},
    "161226": {"idx": "sz399991", "tg": "白银期货", "fe": "0.60%"},
    "161129": {"idx": "gb_XAU", "tg": "黄金主题", "fe": "1.50%"}
}
FUNDS = [{"s": "sz160723", "id": "160723"}, {"s": "sz160416", "id": "160416"},
         {"s": "sh501018", "id": "501018"}, {"s": "sz162411", "id": "162411"},
         {"s": "sz161226", "id": "161226"}, {"s": "sz161129", "id": "161129"}]

def get_data():
    s_list = [f["s"] for f in FUNDS] + list(set([m["idx"] for m in FUND_META.values()]))
    url = f"http://hq.sinajs.cn/list={','.join(s_list)}"
    headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        return r.text
    except: return None

def color_v(v):
    if not isinstance(v, str) or '%' not in v: return ''
