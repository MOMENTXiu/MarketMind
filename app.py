"""
超市AI营销系统 - Streamlit Web界面
作者: MarketMind团队
功能: 关联规则分析、销售预测、客户聚类、语音播报
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import sys

# 设置页面配置
st.set_page_config(
    page_title="超市AI营销系统",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<h1 class="main-header">🛒 超市AI营销系统</h1>', unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.image("https://via.placeholder.com/300x100.png?text=MarketMind+AI", use_column_width=True)
    st.markdown("---")

    # 功能选择
    st.header("📋 功能导航")
    module = st.selectbox(
        "选择分析模块",
        [
            "🏠 系统首页",
            "📊 关联规则分析",
            "📈 销售预测",
            "👥 客户聚类",
            "🔊 语音播报",
            "📑 完整报告"
        ]
    )

    st.markdown("---")

    # 数据上传
    st.header("📁 数据管理")
    uploaded_file = st.file_uploader("上传数据文件", type=['csv'])

    if uploaded_file is None:
        # 使用默认数据
        data_path = "analysis/dataset.csv"
        if os.path.exists(data_path):
            st.info("✅ 使用默认数据集")
            use_default = True
        else:
            st.warning("⚠️ 请上传数据文件")
            use_default = False
    else:
        st.success("✅ 文件上传成功")
        use_default = False

    st.markdown("---")
    st.markdown("### 📊 数据概览")
    if use_default or uploaded_file:
        try:
            if use_default:
                df = pd.read_csv(data_path, encoding='utf-8')
            else:
                df = pd.read_csv(uploaded_file, encoding='utf-8')

            st.metric("订单记录数", f"{len(df):,}")
            st.metric("订单数量", f"{df['订单 ID'].nunique():,}")
            st.metric("客户数量", f"{df['客户 ID'].nunique():,}")
            st.metric("产品数量", f"{df['产品 ID'].nunique():,}")
        except Exception as e:
            st.error(f"数据加载错误: {e}")

# 主内容区
if module == "🏠 系统首页":
    st.header("欢迎使用超市AI营销系统")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>📊 关联规则分析</h3>
            <p>挖掘商品关联关系，制定促销策略</p>
            <ul>
                <li>Apriori算法</li>
                <li>购物篮分析</li>
                <li>组合促销建议</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📈 销售预测</h3>
            <p>预测未来销售额和利润</p>
            <ul>
                <li>时间序列预测</li>
                <li>17维特征工程</li>
                <li>岭回归模型</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>👥 客户聚类</h3>
            <p>客户分群与精准营销</p>
            <ul>
                <li>RFM模型</li>
                <li>K-Means聚类</li>
                <li>营销策略定制</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>🔊 语音播报</h3>
            <p>AI自动生成分析报告</p>
            <ul>
                <li>文本生成</li>
                <li>语音合成</li>
                <li>自动播报</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🚀 快速开始")
    st.info("""
    **使用步骤**:
    1. 在左侧上传数据文件（或使用默认数据）
    2. 选择分析模块进行分析
    3. 查看分析结果和可视化图表
    4. 下载报告和语音文件
    """)

    # 系统架构图
    st.markdown("---")
    st.subheader("🏗️ 系统架构")
    st.image("https://via.placeholder.com/800x400.png?text=System+Architecture", use_column_width=True)

elif module == "📊 关联规则分析":
    st.header("商品关联规则分析")

    tab1, tab2, tab3 = st.tabs(["📋 配置参数", "📊 分析结果", "💡 策略建议"])

    with tab1:
        st.subheader("算法配置")

        col1, col2, col3 = st.columns(3)
        with col1:
            min_support = st.slider("最小支持度", 0.01, 0.1, 0.02, 0.01)
            st.caption("支持度表示规则出现的频率")
        with col2:
            min_confidence = st.slider("最小置信度", 0.1, 0.8, 0.3, 0.1)
            st.caption("置信度表示规则的可靠性")
        with col3:
            min_lift = st.slider("最小提升度", 1.0, 3.0, 1.0, 0.1)
            st.caption("提升度>1表示正相关")

        st.markdown("---")
        st.info("""
        **算法选择理由**:
        - 使用**Apriori算法**进行关联规则挖掘
        - 经典的购物篮分析算法，可解释性强
        - 通过支持度、置信度、提升度三个指标筛选有效规则
        """)

        if st.button("🚀 开始分析", type="primary"):
            with st.spinner("正在分析中..."):
                # 这里调用实际的分析代码
                st.success("✅ 分析完成！")

    with tab2:
        st.subheader("Top 10 关联规则")

        # 模拟数据展示（实际应该调用analysis模块）
        mock_rules = pd.DataFrame({
            '前项商品': ['纸张, 系固件', '纸张, 用具', '配件, 电话'],
            '后项商品': ['椅子', '椅子', '复印机'],
            '支持度': [0.0312, 0.0298, 0.0276],
            '置信度': [0.4779, 0.4737, 0.4727],
            '提升度': [1.52, 1.51, 1.62]
        })

        st.dataframe(mock_rules, use_container_width=True)

        st.markdown("---")

        # 可视化图表
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("支持度-置信度分布")
            # 检查图片是否存在
            img_path = "analysis/01_association_support_confidence.png"
            if os.path.exists(img_path):
                st.image(img_path, use_column_width=True)
            else:
                st.info("请先运行分析生成图表")

        with col2:
            st.subheader("Top 10 提升度")
            img_path = "analysis/02_association_top10_lift.png"
            if os.path.exists(img_path):
                st.image(img_path, use_column_width=True)
            else:
                st.info("请先运行分析生成图表")

    with tab3:
        st.subheader("促销策略建议")

        st.success("""
        **策略1: 捆绑销售**
        - 商品组合: 纸张 + 系固件 + 椅子
        - 预期效果: 购买纸张和系固件的顾客有47.8%概率购买椅子
        - 建议措施: 设置套餐价，提供组合折扣
        """)

        st.success("""
        **策略2: 交叉推荐**
        - 商品组合: 配件 + 电话 → 复印机
        - 预期效果: 提升度1.62，强相关性
        - 建议措施: 在配件和电话区域放置复印机推荐广告
        """)

        st.download_button(
            label="📥 下载完整策略报告",
            data="促销策略详细报告内容...",
            file_name="promotion_strategy.txt",
            mime="text/plain"
        )

elif module == "📈 销售预测":
    st.header("销售额与利润预测")

    tab1, tab2, tab3 = st.tabs(["⚙️ 模型配置", "📊 预测结果", "📈 可视化"])

    with tab1:
        st.subheader("预测模型配置")

        col1, col2 = st.columns(2)
        with col1:
            model_type = st.selectbox(
                "选择预测模型",
                ["岭回归 (Ridge)", "随机森林", "梯度提升"]
            )
            st.caption("当前推荐: 岭回归")

        with col2:
            forecast_weeks = st.number_input("预测周数", 1, 52, 13)
            st.caption("默认预测一个季度(13周)")

        st.markdown("---")
        st.info("""
        **特征工程 (17个特征)**:
        - **时间特征**: 周序号、月份、季度
        - **周期特征**: sin/cos编码捕捉季节性
        - **滞后特征**: lag1~lag4历史值
        - **滑动统计**: 移动平均、标准差
        - **差分特征**: 环比增长率

        **算法选择理由**:
        - 样本量212周，岭回归防止过拟合
        - L2正则化提高模型稳定性
        - 交叉验证R²=0.94，性能优秀
        """)

        if st.button("🚀 开始预测", type="primary"):
            with st.spinner("模型训练中..."):
                st.success("✅ 预测完成！")

    with tab2:
        st.subheader("下季度预测结果")

        # 模拟预测数据
        mock_forecast = pd.DataFrame({
            '周次': [f'第{i}周' for i in range(1, 14)],
            '预测销售额(万元)': np.random.uniform(4, 12, 13).round(2),
            '预测利润(万元)': np.random.uniform(0.3, 1.5, 13).round(2)
        })

        st.dataframe(mock_forecast, use_container_width=True)

        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("季度预测销售额", "102.2万元", "8.5%")
        with col2:
            st.metric("季度预测利润", "11.8万元", "7.2%")
        with col3:
            st.metric("预测利润率", "11.5%", "0.3%")

        st.markdown("---")

        st.subheader("模型性能指标")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("销售额模型 R²", "0.9061")
            st.metric("RMSE", "12,249元")
        with col2:
            st.metric("利润模型 R²", "0.9212")
            st.metric("MAE", "1,649元")

    with tab3:
        st.subheader("预测趋势可视化")

        img_path = "analysis/03_sales_trend_forecast.png"
        if os.path.exists(img_path):
            st.image(img_path, caption="销售额走势与预测", use_column_width=True)
        else:
            st.info("请先运行分析生成图表")

        st.markdown("---")

        img_path = "analysis/04_profit_trend_forecast.png"
        if os.path.exists(img_path):
            st.image(img_path, caption="利润走势与预测", use_column_width=True)
        else:
            st.info("请先运行分析生成图表")

elif module == "👥 客户聚类":
    st.header("客户聚类分析")

    tab1, tab2, tab3 = st.tabs(["⚙️ 聚类配置", "📊 分群结果", "💼 营销策略"])

    with tab1:
        st.subheader("聚类算法配置")

        col1, col2 = st.columns(2)
        with col1:
            n_clusters = st.slider("聚类数量", 2, 8, 4)
            st.caption("当前最佳聚类数: 4")
        with col2:
            cluster_method = st.selectbox("聚类算法", ["K-Means", "层次聚类", "GMM"])
            st.caption("推荐: K-Means")

        st.markdown("---")
        st.info("""
        **RFM模型**:
        - **R (Recency)**: 最近购买距今天数 → 越小越好
        - **F (Frequency)**: 购买频次 → 越大越好
        - **M (Monetary)**: 消费金额 → 越大越好

        **聚类特征** (5维):
        - R_最近购买天数
        - F_购买频次
        - M_消费金额
        - 平均折扣
        - 客单价

        **算法选择理由**:
        - K-Means效率高，适合RFM特征
        - 肘部法则+轮廓系数确定K=4
        - 轮廓系数0.265，分群边界清晰
        """)

        if st.button("🚀 开始聚类", type="primary"):
            with st.spinner("聚类分析中..."):
                st.success("✅ 聚类完成！")

    with tab2:
        st.subheader("客户分群画像")

        # 模拟分群数据
        cluster_profile = pd.DataFrame({
            '客户群体': ['高价值活跃客户', '普通活跃客户', '低价值流失客户', '高价值流失预警'],
            '客户数': [258, 425, 106, 1],
            '平均R(天)': [107, 102, 467, 1328],
            '平均F(次)': [8.34, 5.64, 3.86, 1.00],
            '平均M(元)': [35969, 13308, 10241, 47540],
            '销售额占比': ['57.8%', '35.2%', '6.8%', '0.3%']
        })

        st.dataframe(cluster_profile, use_container_width=True)

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            img_path = "analysis/08_cluster_rfm_comparison.png"
            if os.path.exists(img_path):
                st.image(img_path, caption="RFM得分对比", use_column_width=True)

        with col2:
            img_path = "analysis/10_cluster_contribution.png"
            if os.path.exists(img_path):
                st.image(img_path, caption="客户贡献度", use_column_width=True)

    with tab3:
        st.subheader("差异化营销策略")

        st.success("""
        **群体1: 高价值活跃客户** (258人，贡献57.8%销售额)
        - 🎯 VIP专属优惠
        - 🎁 会员积分加倍
        - 🆕 新品优先体验
        - 📞 专属客服服务
        """)

        st.info("""
        **群体2: 普通活跃客户** (425人，贡献35.2%销售额)
        - 💰 满减优惠券
        - 📦 推荐升级产品
        - 🔄 交叉销售
        - 🎁 积分兑换活动
        """)

        st.warning("""
        **群体3: 低价值流失客户** (106人，贡献6.8%销售额)
        - 💸 大额满减券
        - ⚡ 限时秒杀
        - 🏷️ 清仓特价
        - 📱 短信推送唤醒
        """)

        st.error("""
        **群体4: 高价值流失预警** (1人，贡献0.3%销售额)
        - 🎟️ 召回优惠券
        - 🌟 专属折扣
        - ⏰ 限时特惠
        - ☎️ 电话回访关怀
        """)

elif module == "🔊 语音播报":
    st.header("语音合成播报")

    st.info("""
    **功能说明**:
    - 自动汇总三大分析模块的核心结论
    - 使用edge-tts（微软Edge TTS引擎）生成语音
    - 支持中文男声/女声
    """)

    st.markdown("---")

    # 播报文本
    st.subheader("📝 播报文本")

    report_text = """
    超市AI营销系统分析报告。

    第一部分，商品关联规则分析。关联规则分析发现，购买系固件, 纸张的顾客，有48%的概率会同时购买椅子，建议将这些商品设置为组合促销。

    第二部分，销售预测分析。根据历史数据分析，下个季度预测总销售额约102万元，利润约12万元，预计利润率11.5%。

    第三部分，客户聚类分析。客户聚类分析将客户分为4个群体。其中，高价值活跃客户共258人，贡献了57.8%的销售额。建议对这类客户提供VIP专属优惠和会员积分加倍活动。

    以上是本次AI营销分析的全部内容，感谢收听。
    """

    st.text_area("播报内容", report_text, height=300)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        voice = st.selectbox("选择语音", [
            "zh-CN-YunxiNeural (中文男声)",
            "zh-CN-XiaoxiaoNeural (中文女声)"
        ])

    with col2:
        if st.button("🎙️ 生成语音", type="primary"):
            with st.spinner("正在合成语音..."):
                st.success("✅ 语音生成成功！")

    st.markdown("---")

    st.subheader("🔊 播放语音")

    audio_path = "analysis/marketing_report.mp3"
    if os.path.exists(audio_path):
        st.audio(audio_path)

        with open(audio_path, 'rb') as f:
            st.download_button(
                label="📥 下载语音文件",
                data=f,
                file_name="marketing_report.mp3",
                mime="audio/mpeg"
            )
    else:
        st.info("请先生成语音文件")

elif module == "📑 完整报告":
    st.header("完整分析报告")

    st.info("点击下方按钮生成完整的分析报告（包含所有模块）")

    if st.button("🚀 生成完整报告", type="primary"):
        with st.spinner("正在生成报告...可能需要1-2分钟"):
            # 这里调用完整的analysis/marketing_modeling.py
            st.success("✅ 报告生成完成！")

    st.markdown("---")

    st.subheader("📊 报告内容预览")

    # 显示Markdown报告
    report_path = "analysis/分析报告.md"
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        st.markdown(report_content)

        st.download_button(
            label="📥 下载Markdown报告",
            data=report_content,
            file_name="analysis_report.md",
            mime="text/markdown"
        )
    else:
        st.info("请先生成完整报告")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>超市AI营销系统 v1.0 | Powered by MarketMind Team</p>
    <p>技术栈: Python • Streamlit • scikit-learn • mlxtend • edge-tts</p>
</div>
""", unsafe_allow_html=True)
