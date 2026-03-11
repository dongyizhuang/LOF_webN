import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 时间与页面配置
beijing_tz = timezone(timedelta(hours=8))
now_bj = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
st.set_page_config(page_title="LOF专业监控", layout="wide")

# 2. 基金与指数配置
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
    # 构造请求列表
    s_list = [f["s"] for f in FUNDS] + list(set([m["idx"] for m in FUND_META.values()]))
    url = f"http://hq.sinajs.cn/list={','.join(s_list)}"
    headers = {
        "Referer": "http://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'gbk'
        return r.text
    except Exception as e:
        st.warning(f"接口连接超时: {e}")
        return None

def color_v(v):
    if not isinstance(v, str) or '%' not in v: return ''
    try:
        val = float(v.replace('%', '').replace('+', ''))
        return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'
    except: return ''

st.title("🛡️ LOF 基金专业行情看板")
st.caption(f"北京时间：{now_bj} | 自动刷新：30秒")

raw = get_data()
if raw:
    # 更加宽松的正则匹配
    data = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', raw)}
    rows = []
    
    for f in FUNDS:
        fid, sid = f["id"], f["s"]
        meta = FUND_META[fid]
        fd = data.get(sid)
        idat = data.get(meta["idx"])
        
        # 只要有基本价格数据就显示，不强求31个字段
        if not fd or len(fd) < 5: continue

        try:
            price = float(fd[3])  # 现价
            last = float(fd[2])   # 昨收
            iopv = float(fd[1])   # T-2净值
            
            # 计算涨幅
            chg = ((price - last) / last * 100) if last > 0 else 0
            # 计算溢价
            pre = ((price - iopv) / iopv * 100) if iopv > 0 else 0
            
            # 成交额 (万元)
            vol = float(fd[9]) / 10000 if len(fd) > 9 else 0
            # 日期处理
            dt = fd[30][5:10] if len(fd) > 30 else "--"

            # T-1 指数涨幅处理 (处理海外指数和国内指数差异)
            idx_chg_str = "0.00%"
            if idat and len(idat) > 3:
                # 海外指数昨收在 [2]，现价在 [3]；国内指数类似
                try:
                    i_now, i_pre = float(idat[3]), float(idat[2])
                    if i_pre > 0:
                        ic = (i_now - i_pre) / i_pre * 100
                        idx_chg_str = f"{ic:+.2f}%"
                except: pass

            rows.append({
                "代码": fid, 
                "名称": fd[0][:4], 
                "现价": f"{price:.3f}",
                "涨幅": f"{chg:+.2f}%", 
                "成交(万)": f"{vol:.1f}",
                "T-2净值": f"{iopv:.4f}", 
                "日期": dt,
                "标的": meta["tg"], 
                "T-1指数涨幅": idx_chg_str, 
                "溢价率": f"{pre:+.2f}%"
            })
        except Exception as e:
            continue # 跳过解析出错的行

    if rows:
        df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
        st.dataframe(
            df.style.applymap(color_v, subset=['涨幅', '溢价率', 'T-1指数涨幅']), 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("当前非交易时段或接口暂无实时行情数据。")

    if st.button('🔄 手动刷新'): st.rerun()
else:
    st.error("无法获取原始数据，请检查网络环境。")
