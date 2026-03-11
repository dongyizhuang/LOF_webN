import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 页面与时间配置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
st.set_page_config(page_title="LOF T-1 官方净值看板", layout="wide")

# 2. 核心配置修正：162411 是华宝油气，160416 是华安石油
META = {
    "160723": {"idx": "gb_799001", "tg": "原油指数", "co": "嘉实基金"},
    "160416": {"idx": "gb_799001", "tg": "石油指数", "co": "华安基金"},
    "501018": {"idx": "gb_799001", "tg": "原油指数", "co": "南方基金"},
    "162411": {"idx": "gb_799001", "tg": "标普油气", "co": "华宝基金"}, # 修正
    "161226": {"idx": "sz399991", "tg": "白银期货", "co": "国投瑞银"},
    "161129": {"idx": "gb_XAU", "tg": "黄金主题", "co": "易方达"}
}
PRICE_SYMBOLS = ["sz160723", "sz160416", "sh501018", "sz162411", "sz161226", "sz161129"]
NAV_SYMBOLS = ["f_160723", "f_160416", "f_501018", "f_162411", "f_161226", "f_161129"]
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

st.title("📊 LOF 基金官方净值监控 (专业版)")
st.caption(f"当前查询时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 数据源：新浪财经")

raw = get_all_data()
if raw:
    data = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', raw)}
    rows = []
    
    for sid in PRICE_SYMBOLS:
        fid = sid[2:]
        meta, p_dat = META[fid], data.get(sid)
        n_dat, i_dat = data.get(f"f_{fid}"), data.get(meta["idx"])
        
        if not p_dat or not n_dat: continue

        price = float(p_dat[3])
        last = float(p_dat[2])
        p_chg = f"{((price - last) / last * 100):+.2f}%" if last > 0 else "0.00%"
        
        # 官方净值解析
        official_nav = float(n_dat[1]) 
        official_date = n_dat[4] # 这里是关键：显示新浪接口里该净值的真实日期
        
        # 指数涨幅
        idx_chg = "--"
        if i_dat:
            if "gb_" in meta["idx"]:
                idx_chg = f"{float(i_dat[3]):+.2f}%" if len(i_dat) > 3 else "0.00%"
            else:
                p_now, p_pre = float(i_dat[3]), float(i_dat[2])
                idx_chg = f"{((p_now - p_pre) / p_pre * 100):+.2f}%" if p_pre > 0 else "0.00%"

        premium = f"{((price - official_nav) / official_nav * 100):+.2f}%" if official_nav > 0 else "0.00%"

        rows.append({
            "代码": fid, "名称": p_dat[0][:4], "现价": f"{price:.3f}", "涨幅": p_chg,
            "成交(万)": f"{float(p_dat[9])/10000:.1f}",
            "官方净值": f"{official_nav:.4f}",
            "净值日期": official_date, # 增加日期列，识别 T-1 还是 T-2
            "标的": meta["tg"], "指数涨幅": idx_chg, "溢价率": premium
        })

    df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
    st.dataframe(df.style.applymap(color_val, subset=['涨幅', '溢价率', '指数涨幅']), 
                 use_container_width=True, hide_index=True, height=450)
    
    st.info("💡 **注意**：若‘净值日期’非前一交易日，说明新浪数据尚未同步。QDII 净值更新通常在上午 9-10 点。")
    if st.button('🔄 刷新报价'): st.rerun()
else:
    st.error("无法获取数据")
