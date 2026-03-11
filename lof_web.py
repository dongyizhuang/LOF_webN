import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 基础设置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
st.set_page_config(page_title="LOF T-1看板", layout="wide")

# 2. 数据配置
META = {
    "160723": "gb_799001", "160416": "gb_799001",
    "501018": "gb_799001", "162411": "gb_799001",
    "161226": "sz399991", "161129": "gb_XAU"
}
FUNDS = ["160723", "160416", "501018", "162411", "161226", "161129"]

def get_sina():
    ids = [f"sh{f}" if f.startswith('5') else f"sz{f}" for f in FUNDS]
    idxs = list(set(META.values()))
    url = f"https://hq.sinajs.cn/list={','.join(ids + idxs)}"
    head = {"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=head, timeout=10)
        r.encoding = 'gbk'
        return {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', r.text)}
    except: return {}

def get_nav(fid):
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
    try:
        n = float(v.replace('%', '').replace('+', ''))
        if n > 0: return 'color: #ef4444; font-weight: bold;'
        if n < 0: return 'color: #22c55e; font-weight: bold;'
    except: pass
    return ''

st.title("🛡️ LOF 基金 T-1 精准看板")
st.caption(f"时间：{now.strftime('%H:%M:%S')} | 数据：新浪+天天官方")

data = get_sina()
rows = []

if data:
    for fid in FUNDS:
        # --- 注意：以下部分必须严格缩进 ---
        sid = "sh" + fid if fid.startswith('5') else "sz" + fid
        fd = data.get(sid)
        idat = data.get(META[fid])
        t1_nav, t1_dt = get_nav(fid)
        
        if not fd or len(fd) < 5: 
            continue

        p_curr = float(fd[3])
        p_last = float(fd[2])
        
        # 涨幅计算
        c_str = "0.00%"
        if p_last > 0:
            c_val = (p_curr - p_last) / p_last * 100
            c_str = "{:+.2f}%".format(c_val)
            
        # 指数涨幅
        i_str = "0.00%"
        if idat and len(idat) > 3:
            if "gb_" in META[fid]:
                i_str = "{:+.2f}%".format(float(idat[3]))
            else:
                p_n, p_p = float(idat[3]), float(idat[2])
                if p_p > 0:
                    iv = (p_n - p_p) / p_p * 100
                    i_str = "{:+.2f}%".format(iv)

        # 溢价率
        pre_str = "--"
        if t1_nav > 0:
            pv = ((p_curr - t1_nav) / t1_nav) * 100
            pre_str = "{:+.2f}%".format(pv)

        # 构造行数据
        item = {
            "代码": fid, "名称": fd[0][:4], "现价": "{:.3f}".format(p_curr), 
            "涨幅": c_str, "成交(万)": "{:.1f}".format(float(fd[9])/10000),
            "T-1净值": "{:.4f}".format(t1_nav), "日期": t1_dt,
            "指数涨幅": i_str, "溢价率": pre_str
        }
        rows.append(item)

    # 排序与显示
    if rows:
        df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
        st.dataframe(df.style.applymap(color_v, subset=['涨幅', '溢价率', '指数涨幅']), 
                     use_container_width=True, hide_index=True)
    
    if st.button('🔄 刷新'): 
        st.rerun()
else:
    st.error("获取数据失败")
