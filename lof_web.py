import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 时间配置 (北京时间 T-2)
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
t2_date = (now - timedelta(days=2)).strftime('%m-%d')
st.set_page_config(page_title="LOF专业监控", layout="wide")

# 2. 基金配置
META = {
    "160723": {"idx": "gb_799001", "tg": "原油指数"},
    "160416": {"idx": "gb_799001", "tg": "标普油气"},
    "501018": {"idx": "gb_799001", "tg": "南方原油"},
    "162411": {"idx": "gb_XBI", "tg": "标普生物"},
    "161226": {"idx": "sz399991", "tg": "白银期货"},
    "161129": {"idx": "gb_XAU", "tg": "黄金主题"}
}
FUNDS = ["sz160723", "sz160416", "sh501018", "sz162411", "sz161226", "sz161129"]

def get_raw():
    ids = FUNDS + list(set([m["idx"] for m in META.values()]))
    url = f"http://hq.sinajs.cn/list={','.join(ids)}"
    try:
        r = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=10)
        r.encoding = 'gbk'
        return r.text
    except: return None

def color_val(v):
    if not isinstance(v, str) or '%' not in v: return ''
    val = float(v.replace('%', '').replace('+', ''))
    return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'

st.title("🛡️ LOF 基金专业行情看板")
st.caption(f"更新时间：{now.strftime('%H:%M:%S')} | 刷新：30秒")

raw = get_raw()
if raw:
    data = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', raw)}
    rows = []
    for sid in FUNDS:
        fid = sid[2:]
        meta, fd = META[fid], data.get(sid)
        idat = data.get(meta["idx"])
        if not fd or len(fd) < 5: continue

        # 核心解析逻辑
        price, last, iopv = float(fd[3]), float(fd[2]), float(fd[1])
        chg = f"{((price - last) / last * 100):+.2f}%" if last > 0 else "0.00%"
        pre = f"{((price - iopv) / iopv * 100):+.2f}%" if iopv > 0 else "0.00%"
        
        # 指数涨幅逻辑 (gb_ 索引 3, 国内索引 (3-2)/
