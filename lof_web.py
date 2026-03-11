import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

###1. 强制定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))
now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')

###2. 页面配置
st.set_page_config(page_title="LOF专业监控", layout="wide")

###3. 基金配置信息
FUND_META = {
"160723": {"idx_sid": "gb_799001", "target": "原油指数", "fee": "1.50%", "co": "嘉实基金"},
"160416": {"idx_sid": "gb_799001", "target": "标普油气指数", "fee": "1.50%", "co": "华宝基金"},
"501018": {"idx_sid": "gb_799001", "target": "南方原油指数", "fee": "1.50%", "co": "南方基金"},
"162411": {"idx_sid": "gb_XBI", "target": "标普生物科技", "fee": "1.20%", "co": "华宝基金"},
"161226": {"idx_sid": "sz399991", "target": "白银期货指数", "fee": "0.60%", "co": "国投瑞银"},
"161129": {"idx_sid": "gb_XAU", "target": "黄金主题指数", "fee": "1.50%", "co": "易方达"}
}

FUNDS = [
{"symbol": "sz160723", "id": "160723"},
{"symbol": "sz160416", "id": "160416"},
{"symbol": "sh501018", "id": "501018"},
{"symbol": "sz162411", "id": "162411"},
{"symbol": "sz161226", "id": "161226"},
{"symbol": "sz161129", "id": "161129"}
]

def get_all_data():
fund_symbols = [f["symbol"] for f in FUNDS]
index_symbols = list(set([m["idx_sid"] for m in FUND_META.values()]))
all_symbols = ",".join(fund_symbols + index_symbols)
url = f"{all_symbols}"
headers = {"Referer": "", "User-Agent": "Mozilla/5.0"}
try:
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'gbk'
return res.text
except:
return None

def color_val(val):
if not isinstance(val, str) or '%' not in val: return ''
try:
num = float(val.replace('%', '').replace('+', ''))
if num > 0: return 'color: #ef4444; font-weight: bold;'
if num < 0: return 'color: #22c55e; font-weight: bold;'
except: pass
return ''

st.title("🛡️ LOF 基金专业行情看板")
st.caption(f"北京时间：{now_beijing} | 自动刷新：30秒")

raw = get_all_data()
if raw:
data_map = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.?)="(.?)";', raw)}
rows = []
for f in FUNDS:
sid, fid = f["symbol"], f["id"]
meta, f_data = FUND_META[fid], data_map.get(sid)
i_data = data_map.get(meta["idx_sid"])
if not f_data or len(f_data) < 30: continue

else:
st.error("数据连接失败，请稍后重试。")
