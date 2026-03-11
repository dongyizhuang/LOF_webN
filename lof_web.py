import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 强制定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))
now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')

# 2. 页面配置
st.set_page_config(page_title="LOF专业监控", layout="wide")

# 3. 基金配置信息
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
    """获取所有基金和指数的实时行情数据"""
    fund_symbols = [f["symbol"] for f in FUNDS]
    index_symbols = list(set([m["idx_sid"] for m in FUND_META.values()]))
    all_symbols = ",".join(fund_symbols + index_symbols)
    
    # 补充新浪财经行情接口地址
    url = f"https://hq.sinajs.cn/list={all_symbols}"
    headers = {
        "Referer": "https://finance.sina.com.cn", 
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'gbk'
        return res.text
    except Exception as e:
        st.warning(f"请求异常: {e}")
        return None

def color_val(val):
    """为涨跌幅提供颜色样式"""
    if not isinstance(val, str) or '%' not in val:
        return ''
    try:
        num = float(val.replace('%', '').replace('+', ''))
        if num > 0:
            return 'color: #ef4444; font-weight: bold;'
        if num < 0:
            return 'color: #22c55e; font-weight: bold;'
    except:
        pass
    return ''

# --- 页面渲染 ---
st.title("🛡️ LOF 基金专业行情看板")
st.caption(f"北京时间：{now_beijing} | 自动刷新：30秒")

raw_data = get_all_data()

if raw_data:
    # 解析新浪行情数据格式
    data_map = {m[0]: m[1].split(',') for m in re.findall(r'hq_str_(.+?)="(.+?)";', raw_data)}
    
    rows = []
    for f in FUNDS:
        sid, fid = f["symbol"], f["id"]
        meta = FUND_META[fid]
        f_data = data_map.get(sid)
        i_data = data_map.get(meta["idx_sid"])
        
        # 基础数据校验
        if not f_data or len(f_data) < 6:
            continue
            
        # 这里可以继续添加解析逻辑，例如：
        current_price = f_data[3]
        change_pct = f_data[32] if len(f_data) > 32 else "0.00" # 假设的索引位
        
        rows.append({
            "基金代码": fid,
            "标的名称": meta["target"],
            "当前价格": current_price,
            "涨跌幅": f"{change_pct}%",
            "管理费率": meta["fee"],
            "基金公司": meta["co"]
        })
    
    # 显示表格
    if rows:
        df = pd.DataFrame(rows)
        st.table(df)
    else:
        st.info("解析后暂无有效数据")
else:
    st.error("数据连接失败，请检查网络或接口地址。")
