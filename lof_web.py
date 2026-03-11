import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime

# 页面配置
st.set_page_config(page_title="LOF实时监控", layout="wide")

st.title("📊 LOF 基金实时溢价监控")
st.caption(f"数据来源：新浪财经 | 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 基金配置
FUNDS = [
    {"symbol": "sz160723", "name": "嘉实原油"},
    {"symbol": "sz160416", "name": "华宝油气"},
    {"symbol": "sh501018", "name": "南方原油"},
    {"symbol": "sz162411", "name": "华宝医疗"}
]

def get_data():
    symbols = ",".join([f["symbol"] for f in FUNDS])
    url = f"http://hq.sinajs.cn/list={symbols}"
    headers = {
        "Referer": "http://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'
        return response.text
    except:
        return None

def color_style(val):
    """数值着色：涨/溢为红，跌/折为绿"""
    if isinstance(val, str) and '%' in val:
        num = float(val.replace('%', ''))
        color = 'red' if num > 0 else 'green'
        return f'color: {color}; font-weight: bold;'
    return ''

raw_data = get_data()
if raw_data:
    matches = re.findall(r'hq_str_(s[zh]\d+)=\"(.*?)\";', raw_data)
    rows = []
    
    for symbol_code, content in matches:
        parts = content.split(',')
        if len(parts) < 5: continue
        
        price = float(parts[3])
        last_close = float(parts[2])
        iopv = float(parts[1])
        
        # 计算逻辑
        change = ((price - last_close) / last_close * 100) if last_close > 0 else 0
        premium = ((price - iopv) / iopv * 100) if iopv > 0 else 0
        
        rows.append({
            "市场": "上证" if symbol_code.startswith('sh') else "深市",
            "代码": symbol_code[2:],
            "名称": parts[0],
            "实时价格": f"{price:.3f}",
            "当日涨跌": f"{change:+.2f}%",
            "净值/IOPV": f"{iopv:.3f}",
            "溢价率": f"{premium:+.2f}%"
        })

    df = pd.DataFrame(rows)
    
    # 渲染表格并着色
    st.table(df.style.applymap(color_style, subset=['当日涨跌', '溢价率']))
else:
    st.error("数据获取失败，请刷新页面重试")

# 自动刷新功能（每30秒）
if st.button('手动刷新数据'):
    st.rerun()

st.info("💡 手机端建议横屏查看或直接上下滑动表格。")
