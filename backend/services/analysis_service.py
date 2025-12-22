"""
分析服务 - 整合所有分析模块
"""
import traceback
from pathlib import Path
import pandas as pd

from backend.core.storage import storage
from backend.models.project import ProjectStatus, AnalysisResults
from backend.services.association_service import AssociationService
from backend.services.prediction_service import PredictionService
from backend.services.clustering_service import ClusteringService
from backend.services.tts_service import TTSService
from backend.services.model_builder_service import ModelBuilderService
from backend.services.recommender_service import clear_recommender_cache


async def run_project_analysis(project_id: str):
    """
    执行项目完整分析流程

    包括：
    1. 关联规则分析
    2. 销售预测
    3. 客户聚类
    4. 生成分析报告
    5. 语音合成
    6. 构建推荐模型 (model_data.pkl)
    """
    try:
        # 获取项目
        project = storage.get_project(project_id)
        if not project:
            print(f"项目不存在: {project_id}")
            return

        print(f"开始分析项目: {project.name} ({project_id})")

        # 获取项目路径
        project_dir = storage.get_project_dir(project_id)
        dataset_path = Path(project.dataset_path)
        outputs_dir = project_dir / "outputs"
        charts_dir = outputs_dir / "charts"
        reports_dir = outputs_dir / "reports"
        audio_dir = outputs_dir / "audio"

        # 验证数据集
        if not dataset_path.exists():
            raise FileNotFoundError(f"数据集不存在: {dataset_path}")

        # 加载数据
        df = pd.read_csv(dataset_path, encoding='utf-8')
        print(f"数据集加载成功，共 {len(df)} 条记录")

        # 初始化结果对象
        results = AnalysisResults(charts={})

        # ========== 1. 关联规则分析 ==========
        print("正在执行关联规则分析...")
        association_service = AssociationService(str(dataset_path))
        association_result = await association_service.analyze(
            min_support=project.parameters.min_support,
            min_confidence=project.parameters.min_confidence,
            min_lift=project.parameters.min_lift,
            top_n=10
        )
        results.association_rules = association_result.rules
        print(f"关联规则分析完成，发现 {len(association_result.rules)} 条规则")

        # ========== 2. 销售预测 ==========
        print("正在执行销售预测...")
        prediction_service = PredictionService(str(dataset_path))
        prediction_result = await prediction_service.analyze(
            forecast_weeks=project.parameters.forecast_weeks
        )
        results.prediction_data = prediction_result.get('data', {})
        print(f"销售预测完成，R²得分: 销售={prediction_result['data'].get('sales_r2', 0):.4f}, 利润={prediction_result['data'].get('profit_r2', 0):.4f}")

        # ========== 3. 客户聚类 ==========
        print("正在执行客户聚类分析...")
        clustering_service = ClusteringService(str(dataset_path))
        customers_csv_path = project_dir / "customers.csv"
        clustering_result = await clustering_service.analyze(
            n_clusters=project.parameters.n_clusters,
            save_path=str(customers_csv_path)
        )
        results.clustering_data = clustering_result.get('data', {})
        results.clustering_data['customers_csv'] = str(customers_csv_path)
        print(f"客户聚类完成，共分为 {clustering_result['data'].get('n_clusters', 0)} 个群体，轮廓系数={clustering_result['data'].get('silhouette_score', 0):.4f}")

        # ========== 4. 生成分析报告 ==========
        print("正在生成分析报告...")
        report_content = generate_analysis_report(project, results)
        report_path = reports_dir / f"report_{project_id}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        results.report_path = str(report_path)
        print(f"分析报告已生成: {report_path}")

        # ========== 5. 语音合成 ==========
        print("正在生成语音播报...")
        try:
            tts_service = TTSService()
            speech_text = generate_speech_text(project, results)
            audio_path = audio_dir / f"report_{project_id}.mp3"
            await tts_service.synthesize(speech_text, str(audio_path))
            results.audio_path = str(audio_path)
            print(f"语音文件已生成: {audio_path}")
        except Exception as e:
            print(f"语音合成失败（跳过）: {e}")
            # 语音失败不影响整体分析

        # ========== 6. 构建推荐模型 ==========
        print("正在构建推荐模型 (model_data.pkl)...")
        try:
            model_builder = ModelBuilderService(str(dataset_path))
            model_result = await model_builder.build_and_save(
                n_clusters=project.parameters.n_clusters,
                association_rules=results.association_rules,
                output_path="backend/data/model_data.pkl"
            )
            if model_result.get('success'):
                print(f"✓ 推荐模型构建完成: {model_result['total_customers']}个客户, {model_result['n_clusters']}个群体, {model_result['n_rules']}条规则")
                # 清除推荐系统缓存，以便下次调用时加载新模型
                clear_recommender_cache()
            else:
                print(f"✗ 推荐模型构建失败: {model_result.get('error')}")
        except Exception as e:
            print(f"推荐模型构建失败（跳过）: {e}")
            # 模型构建失败不影响整体分析

        # ========== 更新项目状态 ==========
        storage.update_project(project_id, {
            'status': ProjectStatus.COMPLETED,
            'results': results.model_dump()
        })
        print(f"项目分析完成: {project.name}")

    except Exception as e:
        error_msg = f"分析失败: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        storage.update_project(project_id, {
            'status': ProjectStatus.FAILED,
            'error_message': error_msg
        })


def generate_analysis_report(project, results: AnalysisResults) -> str:
    """生成分析报告"""
    report = f"""# {project.name} - 营销分析报告

**生成时间**: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
**数据集**: {project.dataset_filename}

---

## 1. 关联规则分析

本次分析发现 {len(results.association_rules) if results.association_rules else 0} 条关联规则。

### Top 10 规则

"""
    if results.association_rules:
        for i, rule in enumerate(results.association_rules[:10], 1):
            antecedents = ', '.join(rule.antecedents)
            report += f"{i}. {antecedents} → **{rule.consequent}**\n"
            report += f"   - 支持度: {rule.support:.4f}\n"
            report += f"   - 置信度: {rule.confidence:.4f}\n"
            report += f"   - 提升度: {rule.lift:.4f}\n"
            report += f"   - 策略: {rule.strategy}\n\n"

    report += """
---

## 2. 销售预测

"""
    if results.prediction_data and results.prediction_data.get('forecast_data'):
        pred_data = results.prediction_data
        report += f"""
**模型性能**:
- 销售额预测 R² 得分: {pred_data.get('sales_r2', 0):.4f}
- 利润预测 R² 得分: {pred_data.get('profit_r2', 0):.4f}
- 训练样本数: {pred_data.get('train_samples', 0)}
- 预测周数: {pred_data.get('forecast_weeks', 0)}

**未来{pred_data.get('forecast_weeks', 0)}周预测**（显示前5周）:

"""
        forecast_list = pred_data.get('forecast_data', [])[:5]
        for week_data in forecast_list:
            report += f"- 第{week_data['week']}周: 销售额 {week_data['sales']:,.2f}元, 利润 {week_data['profit']:,.2f}元\n"
    else:
        report += "销售预测数据不可用\n"

    report += """
---

## 3. 客户聚类

"""
    if results.clustering_data and results.clustering_data.get('cluster_profiles'):
        clust_data = results.clustering_data
        report += f"""
**聚类概况**:
- 客户总数: {clust_data.get('total_customers', 0)}
- 聚类数量: {clust_data.get('n_clusters', 0)}
- 轮廓系数: {clust_data.get('silhouette_score', 0):.4f}

**客户群体画像**:

"""
        for profile in clust_data.get('cluster_profiles', []):
            report += f"""
### {profile['cluster_name']} ({profile['customer_count']}人)
- 平均最近购买天数: {profile['avg_recency']:.0f}天
- 平均购买频次: {profile['avg_frequency']:.1f}次
- 平均消费金额: {profile['avg_monetary']:,.2f}元
- 平均客单价: {profile['avg_order_value']:,.2f}元
- 营销策略: {profile['marketing_strategy']}

"""
    else:
        report += "客户聚类数据不可用\n"

    report += """
---

## 总结

本报告基于 Apriori 算法进行关联规则分析、Ridge回归进行销售预测、K-Means算法进行客户聚类分析生成。
"""
    return report


def generate_speech_text(project, results: AnalysisResults) -> str:
    """生成语音播报文本"""
    speech = f"""
{project.name}营销分析报告播报。

本次分析共发现{len(results.association_rules) if results.association_rules else 0}条关联规则。

"""
    if results.association_rules and len(results.association_rules) > 0:
        speech += "以下是支持度最高的前三条规则：\n\n"
        for i, rule in enumerate(results.association_rules[:3], 1):
            antecedents = '、'.join(rule.antecedents)
            speech += f"第{i}条规则：{antecedents}，推荐搭配{rule.consequent}。"
            speech += f"置信度{rule.confidence*100:.1f}%，提升度{rule.lift:.2f}倍。"
            speech += f"建议策略：{rule.strategy}。\n\n"

    # 销售预测播报
    if results.prediction_data and results.prediction_data.get('forecast_data'):
        pred_data = results.prediction_data
        forecast_list = pred_data.get('forecast_data', [])[:3]
        speech += f"\n销售预测模型训练完成，销售额预测R²得分{pred_data.get('sales_r2', 0):.2f}，利润预测R²得分{pred_data.get('profit_r2', 0):.2f}。"
        speech += f"未来{pred_data.get('forecast_weeks', 0)}周预测显示，"
        if forecast_list:
            speech += f"第1周预计销售额{forecast_list[0]['sales']:,.0f}元，利润{forecast_list[0]['profit']:,.0f}元。"

    # 客户聚类播报
    if results.clustering_data and results.clustering_data.get('cluster_profiles'):
        clust_data = results.clustering_data
        speech += f"\n\n客户聚类分析将{clust_data.get('total_customers', 0)}位客户分为{clust_data.get('n_clusters', 0)}个群体。"

        # 播报最大的两个群体
        profiles = clust_data.get('cluster_profiles', [])
        sorted_profiles = sorted(profiles, key=lambda x: x['customer_count'], reverse=True)[:2]
        for profile in sorted_profiles:
            speech += f"{profile['cluster_name']}共{profile['customer_count']}人，平均消费{profile['avg_monetary']:,.0f}元。"
            speech += f"建议策略：{profile['marketing_strategy'].split('、')[0]}。"

    speech += "\n\n报告播报完毕。"

    return speech
