import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 设置北京时间
beijing_tz = timezone(timedelta(hours=8))
now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')

# 2. 页面配置：使用宽屏模式，贴近专业看板
st.set_page_config(page_title="LOF专业套利监控", layout="wide")

# --- 核心配置：关联基金、指数及元数据 ---
# idx_sid 为关联的指数代码，用于计算 T-1 指数涨幅
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
    url = f"http://hq.sinajs.cn/list={all_symbols}"
    headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'gbk'
        return res.text
    except:
        return None

def color_val(val):
    """红涨绿跌配色"""
    if not isinstance(val, str) or '%' not in val: return ''
    try:
        num = float(val.replace('%', '').replace('+', ''))
        if num > 0: return 'color: #f87171; font-weight: bold;'
        if num < 0: return 'color: #4ade80; font-weight: bold;'
    except: pass
    return ''

st.title("🛡️ LOF 基金专业行情看板")
st.caption(f"当前时间：{now_beijing} | 刷新频率：30秒")

raw = get_all_data()
if raw:
    data_map = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', raw)}
    rows = []
    
    for f in FUNDS:
        sid, fid = f["symbol"], f["id"]
        meta = FUND_META[fid]
        f_data = data_map.get(sid)
        i_data = data_map.get(meta["idx_sid"])
        
        if not f_data or len(f_data) < 30: continue
        
        # 解析场内数据
        price = float(f_data[3])      # 现价
        last_close = float(f_data[2]) # 昨收
        iopv = float(f_data[1])       # T-2净值 (LOF接口中此处常为参考净值)
        amount_wan = float(f_data[9]) / 10000 # 成交额(万元)
        nav_date = f_data[31][5:10] if len(f_data) > 31 else "--"
        
        # 计算
        change = ((price - last_close) / last_close * 100) if last_close > 0 else 0
        premium = ((price - iopv) / iopv * 100) if iopv > 0 else 0
        
        # 指数参考 (T-1涨幅)
        idx_change_str = "0.00%"
        if i_data and len(i_data) > 3:
            try:
                idx_chg = (float(i_data[3]) - float(i_data[2])) / float(i_data[2]) * 100
                idx_change_str = f"{idx_chg:+.2f}%"
            except: pass

        rows.append({
            "代码": fid,
            "名称": f_data[0][:5],
            "现价": f"{price:.3f}",
            "涨幅": f"{change:+.2f}%",
            "成交(万元)": f"{amount_wan:.2f}",
            "T-2净值": f"{iopv:.4f}",
            "净值日期": nav_date,
            "相关标的": meta["target"],
            "T-1指数涨幅": idx_change_str,
            "溢价率": f"{premium:+.2f}%"
        })

    df = pd.DataFrame(rows)
    
    # 按照溢价率降序排列，方便看套利机会
    df['premium_num'] = df['溢价率'].str.replace('%','').astype(float)
    df = df.sort_values('premium_num', ascending=False).drop(columns=['premium_num'])

    # 渲染专业表格
    st.dataframe(
        df.style.applymap(color_val, subset=['涨幅', '溢价率', 'T-1指数涨幅']),
        use_container_width=True,
        hide_index=True,
        height=450
    )
    
    if st.button('🔄 手动刷新数据'):
        st.rerun()
else:
    st.error("数据连接超时，请稍后尝试。")
