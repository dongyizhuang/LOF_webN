import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 强制定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))
now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')

# 页面配置
st.set_page_config(page_title="LOF实时监控", layout="wide")

st.title("📊 LOF 基金实时溢价监控")
# 显示北京时间
st.caption(f"数据来源：新浪财经 | 北京时间：{now_beijing}")

# 基金配置 (包含您新增的 161226 和 161129)
FUNDS = [
    {"symbol": "sz160723", "name": "嘉实原油"},
    {"symbol": "sz160416", "name": "华宝油气"},
    {"symbol": "sh501018", "name": "南方原油"},
    {"symbol": "sz162411", "name": "华宝医疗"},
    {"symbol": "sz161226", "name": "瑞银白银"},
    {"symbol": "sz161129", "name": "黄金主题"}
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
    if isinstance(val, str) and '%' in val:
        try:
            num = float(val.replace('%', ''))
            color = '#ef4444' if num > 0 else '#22c55e' # 红色/绿色
            return f'color: {color}; font-weight: bold;'
        except:
            return ''
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
        
        change = ((price - last_close) / last_close * 100) if last_close > 0 else 0
        premium = ((price - iopv) / iopv * 100) if iopv > 0 else 0
        
        rows.append({
            "市场": "上证" if symbol_code.startswith('sh') else "深市",
            "代码": symbol_code[2:],
            "名称": parts[0][:4],
            "实时价格": f"{price:.3f}",
            "当日涨跌": f"{change:+.2f}%",
            "净值/IOPV": f"{iopv:.3f}",
            "溢价率": f"{premium:+.2f}%"
        })

    df = pd.DataFrame(rows)
    
    # 使用 st.dataframe 渲染，它在手机上支持横向滑动且更美观
    st.dataframe(
        df.style.applymap(color_style, subset=['当日涨跌', '溢价率']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.error("数据获取失败，正在尝试重新连接...")

# 刷新按钮
if st.button('🔄 立即刷新数据'):
    st.rerun()

st.divider()
st.info("💡 提示：场内价格相对于净值，红字代表溢价（买贵了），绿字代表折价（买便宜了）。")
