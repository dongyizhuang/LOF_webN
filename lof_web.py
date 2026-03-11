import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 时间配置 (将 T-2 全部改为 T-1)
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
# 自动计算 T-1 日期 (例如今天 03-11，显示 03-10)
t1_date_calc = (now - timedelta(days=1)).strftime('%m-%d')
st.set_page_config(page_title="LOF T-1专业监控", layout="wide")

# 2. 基金元数据配置
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
    try:
        val = float(v.replace('%', '').replace('+', ''))
        return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'
    except: return ''

st.title("🛡️ LOF 基金 T-1 行情看板")
st.caption(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 自动刷新：30秒")

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
        # 涨幅计算
        chg = f"{((price - last) / last * 100):+.2f}%" if last > 0 else "0.00%"
        # 溢价率计算 (基于 T-1 净值)
        pre = f"{((price - iopv) / iopv * 100):+.2f}%" if iopv > 0 else "0.00%"
        
        # 指数涨幅逻辑 (T-1 走势参考)
        idx_chg = "--"
        if idat:
            if "gb_" in meta["idx"]:
                idx_chg = f"{float(idat[3]):+.2f}%" if len(idat) > 3 else "0.00%"
            else:
                p_now, p_pre = float(idat[3]), float(idat[2])
                idx_chg = f"{((p_now - p_pre) / p_pre * 100):+.2f}%" if p_pre > 0 else "0.00%"

        # 封装数据，统一使用 T-1 标识
        rows.append({
            "代码": fid,
            "名称": fd[0][:4],
            "现价": f"{price:.3f}",
            "涨幅": chg,
            "成交(万)": f"{float(fd[9])/10000:.1f}",
            "T-1净值": f"{iopv:.4f}",
            "T-1日期": t1_date_calc,
            "相关标的": meta["tg"],
            "T-1指数涨幅": idx_chg,
            "溢价率": pre
        })

    # 按照溢价率降序排列
    df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
    
    # 渲染带有红绿颜色的表格
    st.dataframe(
        df.style.applymap(color_val, subset=['涨幅', '溢价率', 'T-1指数涨幅']), 
        use_container_width=True, 
        hide_index=True,
        height=450
    )
    
    if st.button('🔄 立即刷新数据'): st.rerun()
else:
    st.error("数据连接超时，请检查网络...")
