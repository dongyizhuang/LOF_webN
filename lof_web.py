import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 时间配置：计算北京时间和 T-2 净值日期
beijing_tz = timezone(timedelta(hours=8))
now_bj = datetime.now(beijing_tz)
# 自动计算 T-2 日期 (例如今天 03-11，显示 03-09)
t2_date_str = (now_bj - timedelta(days=2)).strftime('%m-%d')
now_str = now_bj.strftime('%Y-%m-%d %H:%M:%S')

# 2. 页面配置：专业宽屏模式
st.set_page_config(page_title="LOF专业套利监控", layout="wide")

# --- 核心配置：关联基金与指数 ---
# idx: 关联指数代码，用于计算 T-1 指数涨幅
FUND_META = {
    "160723": {"idx": "gb_799001", "tg": "原油指数", "fe": "1.50%"},
    "160416": {"idx": "gb_799001", "tg": "标普油气", "fe": "1.50%"},
    "501018": {"idx": "gb_799001", "tg": "南方原油", "fe": "1.50%"},
    "162411": {"idx": "gb_XBI", "tg": "标普生物", "fe": "1.20%"},
    "161226": {"idx": "sz399991", "tg": "白银期货", "fe": "0.60%"},
    "161129": {"idx": "gb_XAU", "tg": "黄金主题", "fe": "1.50%"}
}
FUNDS = [
    {"s": "sz160723", "id": "160723"}, {"s": "sz160416", "id": "160416"},
    {"s": "sh501018", "id": "501018"}, {"s": "sz162411", "id": "162411"},
    {"s": "sz161226", "id": "161226"}, {"s": "sz161129", "id": "161129"}
]

def get_data():
    """从新浪接口批量获取实时行情"""
    s_list = [f["s"] for f in FUNDS] + list(set([m["idx"] for m in FUND_META.values()]))
    url = f"http://hq.sinajs.cn/list={','.join(s_list)}"
    headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        return r.text
    except: return None

def calculate_idx_chg(idx_code, parts):
    """专门处理全球指数(gb_)和国内指数的涨跌幅解析"""
    try:
        if "gb_" in idx_code:
            # 全球指数：parts[1]当前价, parts[26]昨收, parts[3]实时涨跌幅字符串
            return f"{float(parts[3]):+.2f}%" if len(parts) > 3 else "0.00%"
        else:
            # 国内指数：parts[3]当前价, parts[2]昨收
            now, pre = float(parts[3]), float(parts[2])
            return f"{((now - pre) / pre * 100):+.2f}%" if pre > 0 else "0.00%"
    except: return "0.00%"

def color_v(v):
    """数值着色：红涨绿跌"""
    if not isinstance(v, str) or '%' not in v: return ''
    try:
        val = float(v.replace('%', '').replace('+', ''))
        return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'
    except: return ''

st.title("🛡️ LOF 基金专业行情看板")
st.caption(f"北京时间：{now_str} | 自动刷新：30秒")

raw = get_data()
if raw:
    data = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', raw)}
    rows = []
    
    for f in FUNDS:
        fid, sid = f["id"], f["s"]
        meta = FUND_META[fid]
        fd = data.get(sid)
        idat = data.get(meta["idx"])
        
        if not fd or len(fd) < 5: continue

        # 基础数据
        price, last, iopv = float(fd[3]), float(fd[2]), float(fd[1])
        chg = ((price - last) / last * 100) if last > 0 else 0
        pre = ((price - iopv) / iopv * 100) if iopv > 0 else 0
        vol = float(fd[9]) / 10000 if len(fd) > 9 else 0
        
        # 指数解析 (修正 T-1 涨幅逻辑)
        idx_chg_display = calculate_idx_chg(meta["idx"], idat) if idat else "--"

        rows.append({
            "代码": fid, 
            "名称": fd[0][:4], 
            "现价": f"{price:.3f}",
            "涨幅": f"{chg:+.2f}%", 
            "成交(万)": f"{vol:.1f}",
            "T-2净值": f"{iopv:.4f}", 
            "T-2净值日期": t2_date_str, # 按照要求修改
            "相关标的": meta["tg"], 
            "T-1指数涨幅": idx_chg_display, 
            "溢价率": f"{pre:+.2f}%"
        })

    # 生成数据表并按照溢价率降序排列
    df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
    
    # 渲染增强型表格
    st.dataframe(
        df.style.applymap(color_val, subset=['涨幅', '溢价率', 'T-1指数涨幅']), 
        use_container_width=True, 
        hide_index=True,
        height=450
    )
    
    if st.button('🔄 立即手动刷新行情'): st.rerun()
else:
    st.error("行情抓取中，请稍后...")
