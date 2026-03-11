import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 基础配置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
st.set_page_config(page_title="LOF T-1 精准看板", layout="wide")

# 2. 基金配置 (去除了所有可能导致截断的长字符串)
META = {
    "160723": "gb_799001", "160416": "gb_799001",
    "501018": "gb_799001", "162411": "gb_799001",
    "161226": "sz399991", "161129": "gb_XAU"
}
FUNDS = ["160723", "160416", "501018", "162411", "161226", "161129"]

def get_sina():
    """获取价格"""
    ids = [f"sh{f}" if f.startswith('5') else f"sz{f}" for f in FUNDS]
    idxs = list(set(META.values()))
    url = f"https://hq.sinajs.cn/list={','.join(ids + idxs)}"
    headers = {"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        return {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', r.text)}
    except: return {}

def get_nav(fid):
    """获取天天基金官方净值"""
    url = f"https://fundmobapi.eastmoney.com/FundMApi/FundNetList.ashx?FCODE={fid}&PAGEINDEX=1&PAGESIZE=1"
    try:
        res = requests.get(url, timeout=10).json()
        if res and "Datas" in res and len(res["Datas"]) > 0:
            d = res["Datas"][0]
            return float(d['DWJZ']), d['FSRQ']
    except: pass
    return 0.0, "--"

def color_v(v):
    if not isinstance(v, str) or '%' not in v: return ''
    val = float(v.replace('%', '').replace('+', ''))
    return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'

st.title("🛡️ LOF 基金 T-1 精准监控看板")
st.caption(f"当前时间：{now.strftime('%H:%M:%S')} | 混合数据源：新浪价+天天基金净值")

data = get_sina()
rows = []

if data:
    for fid in FUNDS:
        sid = f"sh{fid}" if fid.startswith('5') else f"sz{fid}"
        fd = data.get(sid)
        idat = data.get(META[fid])
        t1_nav, t1_dt = get_nav(fid)
        
        if not fd or len(fd) < 4: continue

        price, last = float(fd[3]), float(fd[2])
        chg = f"{((price - last) / last * 100):
