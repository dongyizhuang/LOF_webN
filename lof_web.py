import streamlit as st
import requests
import re
import pandas as pd
import json
from datetime import datetime, timedelta, timezone

# 1. 基础配置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
st.set_page_config(page_title="LOF T-1 精准监控", layout="wide")

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
    symbols = []
    for f in FUNDS:
        symbols.append(f"sh{f}" if f.startswith('5') else f"sz{f}")
    idx_symbols = list(set([m["idx"] for m in META.values()]))
    url = f"http://hq.sinajs.cn/list={','.join(symbols + idx_symbols)}"
    try:
        r = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=5)
        r.encoding = 'gbk'
        return {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', r.text)}
    except: return {}

def get_tt_official_nav(fid):
    """获取天天基金官方最新公布的净值 (历史净值列表接口)"""
    # 使用天天基金移动端接口，抓取净值列表的第一条数据（即最新官方净值）
    url = f"https://fundmobapi.eastmoney.com/FundMApi/FundNetList.ashx?FCODE={fid}&PAGEINDEX=1&PAGESIZE=1"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if data and "Datas" in data and len(data["Datas"]) > 0:
            latest = data["Datas"][0]
            # DWJZ: 单位净值, FSRQ: 净值日期
            return float(latest['DWJZ']), latest['FSRQ']
    except:
        pass
    return 0.0, "--"

def color_val(v):
    if not isinstance(v, str) or '%' not in v: return ''
    try:
        val = float(v.replace('%', '').replace('+', ''))
        return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'
    except: return ''

st.title("🛡️ LOF 基金 T-1 精准行情看板")
st.caption(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 数据源：新浪行情 + 天天基金官方净值")

sina_data = get_sina_price()
rows = []

if sina_data:
    for fid in FUNDS:
        symbol = f"sh{fid}" if fid.startswith('5') else f"sz{fid}"
        meta = META[fid]
        p_dat = sina_data.get(symbol)
        i_dat = sina_data.get(meta["idx"])
        
        # 调用天天基金官方净值接口
        t1_nav, t1_date = get_tt_official_nav(fid)
        
        if not p_dat or t1_nav == 0: continue

        price = float(p_dat[3])
        last = float(p_dat[2])
        p_chg = f"{((price - last) / last * 100):+.2f}%" if last > 0 else "0.00%"
        
        # 指数涨幅解析
        idx_chg = "--"
        if i_dat:
            if "gb_" in meta["idx"]:
                # 全球指数：index 3 通常是百分比涨跌幅字符串
                idx_chg = f"{float(i_dat[3]):+.2f}%" if len(i_dat) > 3 else "0.00%"
            else:
                p_now, p_pre = float(i_dat[3]), float(i_dat[2])
                idx_chg = f"{((p_now - p_pre) / p_pre * 100):+.2f}%" if p_pre > 0 else "0.00%"

        # 计算溢价率
        premium = f"{((price - t1_nav) / t1_nav * 100):+.2f}%"

        rows.append({
            "代码": fid, 
            "名称": p_dat[0][:4], 
            "现价": f"{price:.3f}", 
            "涨幅": p_chg,
            "成交(万)": f"{float(p_dat[9])/10000:.1f}",
            "T-1净值": f"{t1_nav:.4f}",
            "净值日期": t1_date,
            "相关标的": meta["tg"], 
            "指数涨幅": idx_chg, 
            "溢价率": premium
        })

    if rows:
        df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
        st.dataframe(
            df.style.applymap(color_val, subset=['涨幅', '溢价率', '指数涨幅']), 
            use_container_width=True, 
            hide_index=True, 
            height=450
        )
        if st.button('🔄 立即强制刷新'):
            st.rerun()
    else:
        st.warning("数据解析中，请稍后...")
else:
    st.error("行情接口连接失败，请检查网络。")
