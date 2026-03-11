import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 时间配置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
# 自动计算 T-1 日期
t1_date_calc = (now - timedelta(days=1)).strftime('%m-%d')
st.set_page_config(page_title="LOF T-1 真实监控", layout="wide")

# 2. 基金配置
META = {
    "160723": {"idx": "gb_799001", "tg": "原油指数"},
    "160416": {"idx": "gb_799001", "tg": "标普油气"},
    "501018": {"idx": "gb_799001", "tg": "南方原油"},
    "162411": {"idx": "gb_XBI", "tg": "标普生物"},
    "161226": {"idx": "sz399991", "tg": "白银期货"},
    "161129": {"idx": "gb_XAU", "tg": "黄金主题"}
}
# 行情代码 (价格)
PRICE_SYMBOLS = ["sz160723", "sz160416", "sh501018", "sz162411", "sz161226", "sz161129"]
# 净值代码 (T-1官方净值)
NAV_SYMBOLS = ["f_160723", "f_160416", "f_501018", "f_162411", "f_161226", "f_161129"]
# 指数代码
INDEX_SYMBOLS = list(set([m["idx"] for m in META.values()]))

def get_all_data():
    all_ids = PRICE_SYMBOLS + NAV_SYMBOLS + INDEX_SYMBOLS
    url = f"http://hq.sinajs.cn/list={','.join(all_ids)}"
    try:
        r = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=10)
        r.encoding = 'gbk'
        return r.text
    except: return None

def color_val(v):
    if not isinstance(v, str) or '%' not in v: return ''
    try:
        val = float(v.replace('%', '').replace('+', ''))
        return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'
    except: return ''

st.title("🛡️ LOF 基金 T-1 深度监控看板")
st.caption(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 数据源：新浪财经（官方净值接口）")

raw = get_all_data()
if raw:
    # 解析数据字典
    data = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', raw)}
    rows = []
    
    for sid in PRICE_SYMBOLS:
        fid = sid[2:]
        meta = META[fid]
        
        # 1. 抓取实时价格 (来自行情接口)
        price_data = data.get(sid)
        # 2. 抓取官方净值 (来自基金接口 f_代码)
        # f_代码接口解析：parts[1]是最新净值，parts[4]是净值日期
        nav_data = data.get(f"f_{fid}")
        # 3. 抓取指数涨幅
        index_data = data.get(meta["idx"])
        
        if not price_data or not nav_data: continue

        # 实时价格与涨幅
        curr_price = float(price_data[3])
        last_close = float(price_data[2])
        price_chg = f"{((curr_price - last_close) / last_close * 100):+.2f}%" if last_close > 0 else "0.00%"
        
        # T-1 净值 (使用基金专用接口)
        # 如果 f_ 接口已更新，parts[1] 通常就是最新的 T-1 净值
        t1_nav = float(nav_data[1]) 
        t1_nav_date = nav_data[4] # 官方公布的净值日期
        
        # T-1 指数涨幅解析
        idx_chg = "--"
        if index_data:
            if "gb_" in meta["idx"]:
                idx_chg = f"{float(index_data[3]):+.2f}%" if len(index_data) > 3 else "0.00%"
            else:
                p_now, p_pre = float(index_data[3]), float(index_data[2])
                idx_chg = f"{((p_now - p_pre) / p_pre * 100):+.2f}%" if p_pre > 0 else "0.00%"

        # 计算溢价率 (实时价 vs T-1净值)
        premium = f"{((curr_price - t1_nav) / t1_nav * 100):+.2f}%" if t1_nav > 0 else "0.00%"

        rows.append({
            "代码": fid,
            "名称": price_data[0][:4],
            "现价": f"{curr_price:.3f}",
            "涨幅": price_chg,
            "成交(万)": f"{float(price_data[9])/10000:.1f}",
            "T-1净值": f"{t1_nav:.4f}",
            "T-1日期": t1_nav_date,
            "相关标的": meta["tg"],
            "T-1指数涨幅": idx_chg,
            "溢价率": premium
        })

    # 排序
    df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
    
    # 渲染
    st.dataframe(
        df.style.applymap(color_val, subset=['涨幅', '溢价率', 'T-1指数涨幅']), 
        use_container_width=True, 
        hide_index=True,
        height=450
    )
    
    if st.button('🔄 立即同步最新官方净值'): st.rerun()
else:
    st.error("数据接口响应异常，请检查网络。")
