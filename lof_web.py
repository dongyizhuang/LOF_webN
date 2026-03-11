import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 基础配置
bj_tz = timezone(timedelta(hours=8))
now = datetime.now(bj_tz)
st.set_page_config(page_title="LOF T-1 精准看板", layout="wide")

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
    symbols = [f"sh{f}" if f.startswith('5') else f"sz{f}" for f in FUNDS]
    idx_symbols = list(set([m["idx"] for m in META.values()]))
    # 使用 https 协议提高稳定性
    url = f"https://hq.sinajs.cn/list={','.join(symbols + idx_symbols)}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        return {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.*?)=\"(.*?)\";', r.text)}
    except Exception as e:
        st.error(f"价格接口请求失败: {e}")
        return {}

def get_tt_official_nav(fid):
    """获取天天基金官方最新公布的单位净值"""
    # 接口1：移动端净值列表接口 (最准)
    url = f"https://fundmobapi.eastmoney.com/FundMApi/FundNetList.ashx?FCODE={fid}&PAGEINDEX=1&PAGESIZE=1&deviceid=123456&plat=Android"
    try:
        r = requests.get(url, timeout=10)
        res = r.json()
        if res and "Datas" in res and len(res["Datas"]) > 0:
            data = res["Datas"][0]
            return float(data['DWJZ']), data['FSRQ']
    except:
        # 接口2：备用估值接口
        try:
            url_bak = f"https://fundgz.1234567.com.cn/js/{fid}.js"
            r_bak = requests.get(url_bak, timeout=5)
            content = re.search(r"\((.*)\)", r_bak.text).group(1)
            import json
            j = json.loads(content)
            return float(j['dwjz']), j['jzrq']
        except:
            pass
    return 0.0, "--"

def color_val(v):
    if not isinstance(v, str) or '%' not in v: return ''
    try:
        val = float(v.replace('%', '').replace('+', ''))
        return f'color: {"#f87171" if val > 0 else "#4ade80"}; font-weight: bold;'
    except: return ''

st.title("🛡️ LOF 基金 T-1 精准监控看板")
st.caption(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 数据源：新浪(实时价) + 天天基金(官方净值)")

# 执行抓取
sina_data = get_sina_price()
rows = []

if sina_data:
    for fid in FUNDS:
        symbol = f"sh{fid}" if fid.startswith('5') else f"sz{fid}"
        meta = META[fid]
        p_dat = sina_data.get(symbol)
        i_dat = sina_data.get(meta["idx"])
        
        # 获取 T-1 净值
        t1_nav, t1_date = get_tt_official_nav(fid)
        
        # 即使净值暂时拿不到，也尝试解析价格数据
        if not p_dat or len(p_dat) < 4: continue

        try:
            price = float(p_dat[3])
            last = float(p_dat[2])
            p_chg = f"{((price - last) / last * 100):+.2f}%" if last > 0 else "0.00%"
            
            # 指数涨幅解析
            idx_chg = "--"
            if i_dat and len(i_dat) > 3:
                if "gb_" in meta["idx"]:
                    idx_chg = f"{float(i_dat[3]):+.2f}%"
                else:
                    p_now, p_pre = float(i_dat[3]), float(i_dat[2])
                    idx_chg = f"{((p_now - p_pre) / p_pre * 100):+.2f}%" if p_pre > 0 else "0.00%"

            # 计算溢价率
            premium = "--"
            if t1_nav > 0:
                premium = f"{((price - t1_nav) / t1_nav * 100):+.2f}%"

            rows.append({
                "代码": fid, 
                "名称": p_dat[0][:4], 
                "现价": f"{price:.3f}", 
                "涨幅": p_chg,
                "成交(万)": f"{float(p_dat[9])/10000:.1f}" if len(p_dat) > 9 else "0",
                "T-1净值": f"{t1_nav:.4f}" if t1_nav > 0 else "等待更新",
                "净值日期": t1_date,
                "相关标的": meta["tg"], 
                "指数涨幅": idx_chg, 
                "溢价率": premium
            })
        except:
            continue

    if rows:
        df = pd.DataFrame(rows).sort_values("溢价率", ascending=False)
        st.dataframe(
            df.style.applymap(color_val, subset=['涨幅', '溢价率', '指数涨幅']), 
            use_container_width=True, 
            hide_index=True, 
            height=450
        )
        if st.button('🔄 强制刷新数据'):
            st.rerun()
    else:
        st.warning("解析后的数据列表为空，请检查接口返回内容。")
else:
    st.error("无法获取新浪价格行情，请检查网络或稍后重试。")
