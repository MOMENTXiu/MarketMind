<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  Sparkles,
  Upload,
  Lightbulb,
  ArrowRight,
  SlidersHorizontal,
  BadgePercent,
  Users,
  GitBranch,
  ArrowDown,
  Brain,
  Monitor,
  Route,
  Workflow,
  BrainCircuit,
  ShieldCheck,
  FileSpreadsheet,
  FolderPlus,
  FileCheck,
  ChartNoAxesCombined,
  CheckCircle2,
  Wrench,
  Construction,
  type LucideIcon,
} from 'lucide-vue-next'

const router = useRouter()
const goToProjects = () => router.push('/projects')
const $any = (v: unknown) => v as any

/* ===== DATA ===== */
interface PainPoint { pain: string; solution: string }
const painPoints: PainPoint[] = [
  { pain: '超市每天产生大量订单和商品数据，但业务人员缺乏 SQL、统计和机器学习技能来挖掘价值。', solution: '上传数据即可自动完成分析，无需编写代码或 SQL。' },
  { pain: '手工 Excel 报表只能看到表面指标，难以发现客户结构、组合购买和促销真实效果。', solution: '系统自动执行客户分群、关联规则、促销因果分析等多维度深度洞察。' },
  { pain: 'Support、Confidence、Lift、ATE、DML 等技术指标对业务人员不可读，无法直接用于决策。', solution: '每个分析结果都附带业务解释和可执行建议，让数据驱动决策成为可能。' },
  { pain: '客户分群、商品推荐、促销评估各自独立进行，缺少统一的数据处理和分析流程。', solution: '从原始数据到经营建议的完整链路在一个系统内自动完成，结果可追溯。' },
]

/* ===== ANALYSIS CAPABILITY MAP ===== */
interface ModuleInfo { icon: LucideIcon; title: string; summary: string; inputLabel: string; outputLabel: string; value: string; accent: string }
interface StageInfo { index: string; title: string; description: string; gridClass: string; modules: ModuleInfo[] }
const stages: StageInfo[] = [
  {
    index: '01',
    title: '数据治理',
    description: '让原始数据进入统一、可信的分析结构。',
    gridClass: 'governance',
    modules: [
      { icon: SlidersHorizontal, title: '数据标准化', summary: '将不同来源、不同命名方式的数据统一成系统可分析的标准结构。', inputLabel: 'CSV / Excel', outputLabel: '标准字段', value: '减少人工清洗成本，让后续分析可以自动执行。', accent: '#6366F1' },
      { icon: ShieldCheck, title: '数据质量检查', summary: '检查数据缺失、重复、异常日期和异常金额等问题。', inputLabel: '标准数据', outputLabel: '质量报告', value: '提前识别低质量数据，避免错误结论影响经营决策。', accent: '#0EA5E9' },
    ]
  },
  {
    index: '02',
    title: '业务建模',
    description: '从销售、客户、商品组合、推荐和促销等角度提取业务洞察。',
    gridClass: 'modeling',
    modules: [
      { icon: ChartNoAxesCombined, title: '销售概览', summary: '统计销售规模、订单量、客单价、品类贡献和销售趋势。', inputLabel: '订单数据', outputLabel: '销售指标', value: '快速掌握整体经营情况和关键波动。', accent: '#6366F1' },
      { icon: Users, title: '客户分群', summary: '根据消费行为将客户划分为不同类型。', inputLabel: '用户行为', outputLabel: '客户群体', value: '识别高价值、低频、价格敏感等客户，为运营分层提供依据。', accent: '#8B5CF6' },
      { icon: GitBranch, title: '关联分析', summary: '发现经常一起购买的商品组合。', inputLabel: '购物篮数据', outputLabel: '组合规则', value: '支持商品陈列、捆绑销售和收银推荐。', accent: '#F59E0B' },
      { icon: Sparkles, title: '个性化推荐', summary: '根据用户行为生成更匹配的商品推荐。', inputLabel: '用户画像', outputLabel: '推荐清单', value: '让推荐从"统一推送"变成"因人而异"。', accent: '#EC4899' },
      { icon: BadgePercent, title: '促销分析', summary: '评估促销活动是否带来额外销售增长。', inputLabel: '促销数据', outputLabel: '效果判断', value: '判断促销是否值得继续、扩大或调整。', accent: '#EF4444' },
    ]
  },
  {
    index: '03',
    title: '结果输出',
    description: '将模型结果转化为业务人员能看懂的图表、解释和行动建议。',
    gridClass: 'output',
    modules: [
      { icon: FileCheck, title: '结果摘要', summary: '将分析结果整理成业务人员能看懂的报告。', inputLabel: '分析结果', outputLabel: '业务建议', value: '让图表、指标和模型结果转化为可执行行动。', accent: '#10B981' },
    ]
  },
]


const layerTechMap = [
  {
    layer: '前端层',
    icon: Monitor,
    iconColor: '#6366f1',
    techs: [
      { name: 'Vue 3', desc: '渐进式框架', icon: Monitor },
      { name: 'TypeScript', desc: '类型安全' },
      { name: 'ECharts 5', desc: '数据可视化' },
      { name: 'Vite', desc: '构建工具' },
      { name: 'Element Plus', desc: 'UI 组件库' },
    ],
  },
  {
    layer: 'API 层',
    icon: Route,
    iconColor: '#2563eb',
    techs: [
      { name: 'FastAPI', desc: '高性能 Web 框架', icon: Route },
      { name: 'Uvicorn', desc: 'ASGI 服务器' },
      { name: 'Pydantic', desc: '数据校验' },
    ],
  },
  {
    layer: '业务编排层',
    icon: Workflow,
    iconColor: '#7c3aed',
    techs: [
      { name: 'Business Flow', desc: '生命周期管理' },
      { name: 'Pipeline', desc: '阶段编排' },
      { name: 'State Machine', desc: '状态流转' },
    ],
  },
  {
    layer: '业务能力层',
    icon: BrainCircuit,
    iconColor: '#059669',
    techs: [
      { name: 'Pandas', desc: '数据处理' },
      { name: 'NumPy', desc: '科学计算' },
      { name: 'scikit-learn', desc: '机器学习' },
      { name: 'mlxtend', desc: '关联规则' },
      { name: 'statsmodels', desc: '统计建模' },
    ],
  },
  {
    layer: '边界层',
    icon: ShieldCheck,
    iconColor: '#0891b2',
    techs: [
      { name: 'Provider', desc: '接口抽象' },
      { name: 'Protocol', desc: '类型契约' },
      { name: 'DTO', desc: '数据传输' },
    ],
  },
  {
    layer: '基础设施层',
    icon: null,
    iconColor: '#2496ED',
    dockerSvg: true,
    techs: [
      { name: 'Docker', desc: '统一承载', color: '#2496ED' },
      { name: 'PostgreSQL', desc: '结构化存储', color: '#336791' },
      { name: 'Redis', desc: '缓存/队列', color: '#DC382D' },
      { name: 'MinIO', desc: '对象存储', color: '#C72E49' },
    ],
  },
]

</script>

<template>
  <div class="intro-page">

    <!-- ===== SLIDE 0: HERO ===== -->
    <section class="snap-slide hero">
      <div class="bg-rings">
        <div class="ring r1"></div>
        <div class="ring r2"></div>
        <div class="ring r3"></div>
      </div>
      <div class="hero-content">
        <div class="hero-badge">
          <Sparkles class="badge-icon" />
          <span>面向零售场景的数据洞察平台</span>
        </div>
        <h1 class="hero-title">
          <span class="hero-title-main">MarketMind</span>
          <span class="hero-title-sub">零售营销数据洞察</span>
        </h1>
        <p class="hero-sub">
          从数据上传、自动诊断到业务建议生成，帮助用户把订单数据转化为<br />可执行的销售、客户、推荐与促销决策。
        </p>
      </div>
    </section>

    <!-- ===== SLIDE 1: WHAT ===== -->
    <section class="snap-slide slide what">
      <div class="slide-inner">
        <h2 class="slide-title"><span class="slide-num">01</span>它是什么？</h2>
        <p class="slide-lead">
          MarketMind 是一个面向超市和零售场景的数据分析平台。它接收用户上传的订单、商品、客户和销售数据，
          自动完成数据标准化、质量检查、多维分析和业务解释，最终生成可读的分析报告与行动建议。
        </p>
        <div class="triple-cards">
          <div class="triple-card">
            <div class="tc-icon"><Upload /></div>
            <h3>数据接入</h3>
            <p>支持 CSV/Excel 上传，自动识别中英文字段名和多种编码格式，无需手动整理数据。</p>
          </div>
          <div class="triple-card">
            <div class="tc-icon"><Brain /></div>
            <h3>自动分析</h3>
            <p>数据标准化后自动执行销售概览、客户分群、关联规则、推荐和促销六大分析模块。</p>
          </div>
          <div class="triple-card">
            <div class="tc-icon"><Lightbulb /></div>
            <h3>业务建议</h3>
            <p>技术指标被转换为业务可读的结论和建议，让分析结果直接支撑经营决策。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== SLIDE 2: WHY ===== -->
    <section class="snap-slide slide why">
      <div class="slide-inner">
        <h2 class="slide-title"><span class="slide-num">02</span>为什么需要它？</h2>
        <p class="slide-lead">
          传统的数据分析方式难以满足零售业务的实际需求。以下是业务人员每天面临的问题，以及 MarketMind 的解决方式。
        </p>
        <div class="pain-grid">
          <div v-for="(pp, i) in painPoints" :key="i" class="pain-card">
            <div class="pain-badge">痛点 {{ i + 1 }}</div>
            <p class="pain-text">{{ pp.pain }}</p>
            <div class="pain-arrow"><ArrowDown /></div>
            <p class="pain-solution">{{ pp.solution }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== SLIDE 3: HOW ===== -->
    <section class="snap-slide slide flow">
      <div class="slide-inner flow-inner">
        <h2 class="slide-title"><span class="slide-num">03</span>它是如何工作的？</h2>
        <p class="slide-lead">
          从数据上传到业务报告，系统自动完成字段识别、质量检查和多维分析，让每个阶段的状态与产物都可追溯。
        </p>
        <div class="workflow-diagram">
          <div class="workflow-track">

            <!-- CSV 输入 -->
            <div class="workflow-terminal terminal-input">
              <FileSpreadsheet class="terminal-icon" />
              <span class="terminal-label">CSV</span>
              <span class="terminal-sublabel">输入数据</span>
            </div>

            <div class="workflow-step">
              <span class="wf-step-num">01</span>
              <h3>创建项目</h3>
              <p>为分析任务建立独立工作空间</p>
              <FolderPlus class="wf-step-icon" />
            </div>

            <div class="workflow-step">
              <span class="wf-step-num">02</span>
              <h3>上传数据</h3>
              <p>导入 CSV / Excel 等业务数据</p>
              <Upload class="wf-step-icon" />
            </div>

            <div class="workflow-step">
              <span class="wf-step-num">03</span>
              <h3>字段标准化</h3>
              <p>识别字段并映射为标准结构</p>
              <BrainCircuit class="wf-step-icon" />
            </div>

            <div class="workflow-step">
              <span class="wf-step-num">04</span>
              <h3>质量检查</h3>
              <p>检查缺失、重复和异常数据</p>
              <ShieldCheck class="wf-step-icon" />
            </div>

            <div class="workflow-step">
              <span class="wf-step-num">05</span>
              <h3>多维分析</h3>
              <p>销售、客户、关联、推荐、促销</p>
              <ChartNoAxesCombined class="wf-step-icon" />
            </div>

            <div class="workflow-step">
              <span class="wf-step-num">06</span>
              <h3>业务报告</h3>
              <p>生成图表、指标和行动建议</p>
              <FileCheck class="wf-step-icon" />
            </div>

            <!-- Done 输出 -->
            <div class="workflow-terminal terminal-output">
              <CheckCircle2 class="terminal-icon" />
              <span class="terminal-label">Done</span>
              <span class="terminal-sublabel">分析完成</span>
            </div>

          </div>
        </div>
      </div>
    </section>

    <!-- ===== SLIDE 4: ARCHITECTURE — LAYERS + TECH ===== -->
    <section class="snap-slide slide arch">
      <div class="slide-inner arch-inner">
        <h2 class="slide-title"><span class="slide-num">04</span>系统架构 - 系统分层</h2>
        <p class="slide-lead">
          前端负责交互与报告呈现，后端通过分层架构完成请求接入、编排与能力调用，基础设施由 Docker 统一承载。
        </p>
        <div class="arch-two-col">
          <template v-for="(item, i) in layerTechMap" :key="item.layer">
            <div class="arch-row">
              <div class="arch-row-node" :style="{ '--accent': item.iconColor }">
                <component v-if="item.icon" :is="item.icon" class="arch-row-icon" :style="{ color: item.iconColor }" />
                <div class="arch-row-title">{{ item.layer }}</div>
              </div>
              <div class="arch-row-connector">
                <ChevronRight class="arch-connector-chev" />
              </div>
              <div class="arch-tech-card">
                <component v-if="item.icon" :is="item.icon" class="arch-tech-icon" :style="{ color: item.iconColor }" />
                <div class="arch-tech-chips">
                  <span
                    v-for="t in item.techs"
                    :key="t.name"
                    class="arch-tech-chip"
                    :style="($any(t).color) ? { borderColor: ($any(t).color) + '33', background: ($any(t).color) + '14', color: ($any(t).color) } : {}"
                  >
                    <span class="arch-tech-chip-name">{{ t.name }}</span>
                    <span class="arch-tech-chip-desc">{{ t.desc }}</span>
                  </span>
                </div>
              </div>
            </div>
            <div v-if="i < layerTechMap.length - 1" class="arch-row-arrow">
              <ArrowDown class="arch-arrow-icon" />
            </div>
          </template>
        </div>
      </div>
    </section>

    <!-- ===== SLIDE 5: ANALYSIS CAPABILITY MAP ===== -->
    <section class="snap-slide slide capability">
      <div class="slide-inner">
        <h2 class="slide-title"><span class="slide-num">05</span>数据分析能力</h2>
        <p class="slide-lead">
          系统将上传的数据拆解为可治理、可建模、可解释的分析流程，最终输出图表、指标和业务建议。
        </p>

        <div class="capability-map">
          <div v-for="(stage, si) in stages" :key="stage.title" class="capability-stage-group">
            <div class="capability-stage">
              <div class="capability-stage-header">
                <div>
                  <div class="capability-stage-head-row">
                    <span class="capability-stage-index">{{ stage.index }}</span>
                    <h3 class="capability-stage-title">{{ stage.title }}</h3>
                  </div>
                  <p class="capability-stage-description">{{ stage.description }}</p>
                </div>
              </div>
              <div class="analysis-module-grid" :class="stage.gridClass">
                <div
                  v-for="mod in stage.modules"
                  :key="mod.title"
                  class="analysis-module-card"
                  :style="{ '--module-accent': mod.accent }"
                >
                  <component :is="mod.icon" class="analysis-module-icon" />
                  <h3>{{ mod.title }}</h3>
                  <p class="module-summary">{{ mod.summary }}</p>
                  <div class="module-flow">
                    <span class="flow-label">{{ mod.inputLabel }}</span>
                    <ArrowRight class="flow-arrow-icon" />
                    <span class="flow-label">{{ mod.outputLabel }}</span>
                  </div>
                  <p class="module-value">{{ mod.value }}</p>
                </div>
              </div>
            </div>
            <div v-if="si < stages.length - 1" class="capability-stage-arrow">
              <ArrowDown />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== SLIDE 6: RESULT ===== -->
    <section class="snap-slide slide result">
      <div class="slide-inner">
        <h2 class="slide-title"><span class="slide-num">06</span>已经实现了什么？</h2>
        <p class="slide-lead">
          当前系统已具备完整的分析流水线能力，以下为核心功能的实现状态。
        </p>

        <div class="status-stack">
          <div class="status-section">
            <h3 class="status-title done"><CheckCircle2 class="status-icon" /> 已完成</h3>
            <div class="status-grid">
              <span class="status-chip done">项目创建与管理</span>
              <span class="status-chip done">CSV/Excel 上传与编码检测</span>
              <span class="status-chip done">数据标准化（190+ 字段别名）</span>
              <span class="status-chip done">数据质量检查与阻断</span>
              <span class="status-chip done">销售概览与品类分析</span>
              <span class="status-chip done">客户分群（RFM + KMeans + K-Scan）</span>
              <span class="status-chip done">关联规则（FP-Growth + HUIM）</span>
              <span class="status-chip done">个性化推荐（多召回 + 融合排序）</span>
              <span class="status-chip done">促销效果分析（DML ATE）</span>
              <span class="status-chip done">结果摘要</span>
              <span class="status-chip done">ECharts 可视化图表</span>
              <span class="status-chip done">异步任务执行（Redis/RQ + SSE）</span>
              <span class="status-chip done">Architecture Lint（262 测试通过）</span>
            </div>
          </div>

          <div class="status-section">
            <h3 class="status-title progress"><Wrench class="status-icon" /> 优化中</h3>
            <div class="status-grid">
              <span class="status-chip progress">Retail V2 链路高级分群</span>
              <span class="status-chip progress">DP 链路推荐能力增强</span>
              <span class="status-chip progress">前端业务解释层完善</span>
            </div>
          </div>

          <div class="status-section">
            <h3 class="status-title plan"><Construction class="status-icon" /> 规划中</h3>
            <div class="status-grid">
              <span class="status-chip plan">认证与安全（P4）</span>
              <span class="status-chip plan">产物存储治理（P5）</span>
              <span class="status-chip plan">LightGCN 图神经推荐</span>
              <span class="status-chip plan">流失预测 / CLV / 价格弹性</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== SLIDE 7: CTA ===== -->
    <section class="snap-slide slide cta">
      <div class="cta-inner">
        <h2>从一份数据集开始，<br />让分析结果变成业务行动。</h2>
        <p>MarketMind 将复杂的分析流程自动化，帮助零售团队把数据转化为可执行的决策。</p>
        <button class="btn-main" @click="goToProjects">
          开始探索
          <ArrowRight class="btn-icon-right" />
        </button>
      </div>
    </section>

  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap');

/* ===== SCROLL SNAP CONTAINER ===== */
.intro-page {
  position: fixed;
  inset: 0;
  height: 100vh;
  width: 100vw;
  overflow-y: scroll;
  scroll-snap-type: y mandatory;
  scroll-behavior: smooth;
  background:
    radial-gradient(circle at 85% 55%, rgba(99, 102, 241, 0.12), transparent 34%),
    radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.08), transparent 30%),
    linear-gradient(135deg, #f8fbff 0%, #f7f5ff 45%, #ffffff 100%);
}

html.dark .intro-page {
  background:
    radial-gradient(circle at 85% 55%, rgba(99, 102, 241, 0.10), transparent 34%),
    radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.06), transparent 30%),
    linear-gradient(135deg, #0f0f17 0%, #12101f 45%, #0a0a10 100%);
}

.intro-page::-webkit-scrollbar { display: none; }

/* ===== SLIDE BASE ===== */
.snap-slide {
  scroll-snap-align: start;
  min-height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 60px 40px;
  box-sizing: border-box;
}

.slide-inner {
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
}

.flow-inner {
  max-width: 1280px;
}

.slide-title,
.cta-inner h2 {
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
}

.slide-title {
  font-size: clamp(36px, 4.5vw, 52px);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #111827;
  margin: 0 0 22px;
}

html.dark .slide-title { color: #f1f5f9; }

.slide-num {
  font-size: 18px;
  font-weight: 700;
  color: #6366f1;
  margin-right: 14px;
  letter-spacing: 0;
}

.slide-lead {
  font-size: 18px;
  line-height: 1.7;
  color: #64748b;
  max-width: 800px;
  margin: 0 0 40px;
}

html.dark .slide-lead { color: #94a3b8; }

/* ===== HERO ===== */
.hero {
  position: relative;
  text-align: center;
  flex-direction: column;
}

.bg-rings {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(99, 102, 241, 0.12);
  right: -180px;
  top: 50%;
  transform: translateY(-50%);
}

.r1 { width: 560px; height: 560px; }
.r2 { width: 720px; height: 720px; opacity: 0.6; }
.r3 { width: 880px; height: 880px; opacity: 0.3; }

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 880px;
  padding: 0 40px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 24px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(99, 102, 241, 0.18);
  color: #4f46e5;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.08);
  margin-bottom: 44px;
}

html.dark .hero-badge {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(99, 102, 241, 0.24);
  color: #a5b4fc;
}

.badge-icon { width: 16px; height: 16px; }

.hero-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.hero-title-main {
  font-size: clamp(56px, 7vw, 84px);
  line-height: 1.08;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: #111827;
}

html.dark .hero-title-main { color: #f1f5f9; }

.hero-title-sub {
  font-size: clamp(38px, 5.5vw, 62px);
  line-height: 1.12;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-sub {
  margin-top: 28px;
  font-size: 20px;
  line-height: 1.8;
  color: #64748b;
  max-width: 740px;
  margin-left: auto;
  margin-right: auto;
}

html.dark .hero-sub { color: #94a3b8; }

/* ===== BUTTONS ===== */
.btn-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 34px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  font-size: 1.05rem;
  font-family: inherit;
  font-weight: 700;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 52%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 16px 36px rgba(99, 102, 241, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.28);
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.btn-main:hover {
  transform: translateY(-1px);
  box-shadow: 0 20px 44px rgba(99, 102, 241, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.32);
}

.btn-icon-right { width: 20px; height: 20px; }

/* ===== WHAT — TRIPLE CARDS ===== */
.triple-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.triple-card {
  padding: 34px 26px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(16px);
}

html.dark .triple-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(99, 102, 241, 0.14);
}

.tc-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: rgba(99, 102, 241, 0.10);
  color: #6366f1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.tc-icon svg { width: 24px; height: 24px; }

.triple-card h3 {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 10px;
}

html.dark .triple-card h3 { color: #f1f5f9; }

.triple-card p {
  font-size: 15px;
  line-height: 1.65;
  color: #64748b;
  margin: 0;
}

html.dark .triple-card p { color: #94a3b8; }

/* ===== WHY — PAIN CARDS ===== */
.pain-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.pain-card {
  padding: 24px 26px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
}

html.dark .pain-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(99, 102, 241, 0.12);
}

.pain-badge {
  display: inline-block;
  font-size: 13px;
  font-weight: 700;
  color: #e11d48;
  background: rgba(225, 29, 72, 0.08);
  padding: 3px 10px;
  border-radius: 999px;
  margin-bottom: 10px;
}

.pain-text {
  font-size: 15px;
  line-height: 1.6;
  color: #64748b;
  margin: 0 0 12px;
}

html.dark .pain-text { color: #94a3b8; }

.pain-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
  margin-bottom: 12px;
}

.pain-arrow svg { width: 18px; height: 18px; }

.pain-solution {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.6;
  color: #059669;
  margin: 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(5, 150, 105, 0.06);
  border: 1px solid rgba(5, 150, 105, 0.12);
}

/* ===== WORKFLOW DIAGRAM ===== */
.workflow-diagram {
  max-width: 1120px;
  margin: 32px auto 0;
}

.workflow-track {
  position: relative;
  display: grid;
  grid-template-columns: 80px repeat(6, 1fr) 80px;
  align-items: stretch;
  gap: 12px;
  width: 100%;
  z-index: 1;
}

/* 横向连接背景线 */
.workflow-track::before {
  content: '';
  position: absolute;
  left: 64px;
  right: 64px;
  top: 50%;
  height: 2px;
  transform: translateY(-50%);
  background: linear-gradient(
    90deg,
    rgba(16,185,129,0.28),
    rgba(99,102,241,0.32),
    rgba(34,197,94,0.28)
  );
  z-index: 0;
}

/* 流动光点 */
.workflow-track::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 64px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  transform: translateY(-50%);
  background: #818cf8;
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.5);
  animation: flow-dot-travel 5.5s linear infinite;
  z-index: 0;
}

@keyframes flow-dot-travel {
  0%   { left: 64px;  opacity: 0; }
  8%   { opacity: 1; }
  92%  { opacity: 1; }
  100% { left: calc(100% - 64px); opacity: 0; }
}

/* 端节点 */
.workflow-terminal {
  position: relative;
  z-index: 1;
  min-height: 140px;
  border-radius: 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
  overflow: hidden;
}

.terminal-input {
  border: 1px solid rgba(16, 185, 129, 0.22);
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.08), rgba(255,255,255,0.82));
  box-shadow: 0 14px 36px rgba(16, 185, 129, 0.06);
}

.terminal-output {
  border: 1px solid rgba(34, 197, 94, 0.24);
  background: linear-gradient(180deg, rgba(34, 197, 94, 0.10), rgba(255,255,255,0.84));
  box-shadow: 0 14px 36px rgba(34, 197, 94, 0.06);
}

.terminal-icon {
  width: 28px;
  height: 28px;
  color: #10b981;
}

.terminal-output .terminal-icon { color: #22c55e; }

.terminal-label {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
}

.terminal-sublabel {
  font-size: 10px;
  color: #64748b;
  font-weight: 600;
}

/* 流程卡片 */
.workflow-step {
  position: relative;
  z-index: 1;
  min-height: 140px;
  border-radius: 22px;
  border: 1px solid rgba(99, 102, 241, 0.14);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(18px);
  padding: 16px 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  box-sizing: border-box;
}

/* 边框扫光动画 */
.workflow-step::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    120deg,
    transparent 0%,
    transparent 30%,
    rgba(99, 102, 241, 0.45) 50%,
    transparent 70%,
    transparent 100%
  );
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  opacity: 0;
  background-size: 200% 100%;
  animation: wf-border-scan 5.5s ease-in-out infinite;
}

.workflow-step:nth-child(2)::after { animation-delay: 0.3s; }
.workflow-step:nth-child(3)::after { animation-delay: 0.9s; }
.workflow-step:nth-child(4)::after { animation-delay: 1.5s; }
.workflow-step:nth-child(5)::after { animation-delay: 2.1s; }
.workflow-step:nth-child(6)::after { animation-delay: 2.7s; }
.workflow-step:nth-child(7)::after { animation-delay: 3.3s; }

@keyframes wf-border-scan {
  0%, 10%, 100%   { opacity: 0; background-position: -100% 0; }
  14%, 20%         { opacity: 1; background-position: 100% 0; }
}

/* 右上角 icon */
.wf-step-icon {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 18px;
  height: 18px;
  color: #818cf8;
  opacity: 0.75;
}

/* 编号 badge */
.wf-step-num {
  display: inline-flex;
  height: 22px;
  min-width: 32px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.10);
  color: #6366f1;
  font-size: 11px;
  font-weight: 800;
  margin-bottom: 12px;
}

.workflow-step h3 {
  font-size: 14px;
  font-weight: 800;
  color: #111827;
  margin: 0 0 6px;
}

html.dark .workflow-step h3 { color: #f1f5f9; }

.workflow-step p {
  font-size: 11px;
  line-height: 1.5;
  color: #64748b;
  margin: 0;
  max-width: 120px;
}

html.dark .workflow-step p { color: #94a3b8; }

/* dark mode */
html.dark .workflow-step {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(99, 102, 241, 0.20);
}

html.dark .terminal-input {
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.12), rgba(15, 23, 42, 0.5));
}

html.dark .terminal-output {
  background: linear-gradient(180deg, rgba(34, 197, 94, 0.14), rgba(15, 23, 42, 0.5));
}

html.dark .terminal-label { color: #f1f5f9; }

/* ===== ARCHITECTURE TWO-COLUMN LAYOUT ===== */
.arch-inner {
  max-width: 1300px;
}


.arch-two-col {
  display: flex;
  flex-direction: column;
  max-width: 1060px;
  margin: 20px auto 0;
}

.arch-row {
  display: grid;
  grid-template-columns: 280px 50px 1fr;
  gap: 0;
  align-items: stretch;
}

.arch-row-node {
  position: relative; border-radius: 18px;
  border: 1px solid rgba(99, 102, 241, 0.14);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(14px); padding: 20px 18px;
  display: flex; align-items: center; justify-content: center;
}
.arch-row-node::before {
  content: ''; position: absolute; left: 50%; top: 0;
  width: 44px; height: 2px; transform: translateX(-50%);
  border-radius: 999px; background: var(--accent, #6366f1); opacity: 0.6;
}
.arch-row-icon { position: absolute; top: 8px; right: 10px; width: 18px; height: 18px; opacity: 0.7; }
.arch-row-title { font-size: 16px; font-weight: 700; color: #111827; text-align: center; line-height: 1.2; }

.arch-row-connector {
  display: flex; align-items: center; justify-content: center;
  color: #c7d2fe; opacity: 0.5;
}
.arch-connector-chev { width: 22px; height: 22px; }

.arch-tech-card {
  position: relative; border-radius: 18px;
  border: 1px solid rgba(99, 102, 241, 0.10);
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
  backdrop-filter: blur(12px); padding: 18px 22px;
  display: flex; align-items: center;
}
.arch-tech-icon { position: absolute; top: 8px; right: 12px; width: 18px; height: 18px; opacity: 0.6; }
.arch-tech-chips { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.arch-tech-chip {
  display: inline-flex; flex-direction: column; align-items: center; gap: 0;
  padding: 5px 12px; border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  background: rgba(99, 102, 241, 0.05);
}
.arch-tech-chip-name { font-size: 15px; font-weight: 700; color: #4f46e5; line-height: 1.3; }
.arch-tech-chip-desc { font-size: 10px; color: #64748b; font-weight: 500; line-height: 1.3; }

.arch-row-arrow {
  display: flex; align-items: center; justify-content: center;
  min-height: 30px; color: #818cf8; opacity: 0.5;
}
.arch-arrow-icon { width: 15px; height: 15px; }

html.dark .arch-row-node { background: rgba(255, 255, 255, 0.04); border-color: rgba(99, 102, 241, 0.22); }
html.dark .arch-row-title { color: #f1f5f9; }
html.dark .arch-tech-card { background: rgba(255, 255, 255, 0.03); border-color: rgba(99, 102, 241, 0.14); }
html.dark .arch-tech-chip { background: rgba(255, 255, 255, 0.03); border-color: rgba(99, 102, 241, 0.16); }
html.dark .arch-tech-chip-name { color: #a5b4fc; }
html.dark .arch-tech-chip-desc { color: #94a3b8; }

/* ===== ANALYSIS CAPABILITY MAP ===== */
.capability {
  padding-top: 24px;
  padding-bottom: 24px;
}

.capability .slide-title {
  font-size: clamp(22px, 2.8vw, 34px);
  margin-bottom: 6px;
}

.capability .slide-lead {
  font-size: 12px;
  margin-bottom: 0;
  max-width: 640px;
}

.capability-map {
  max-width: 1040px;
  margin: 10px auto 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.capability-stage-group {
  display: contents;
}

.capability-stage {
  position: relative;
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.16);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(14px);
  padding: 12px 16px;
}

html.dark .capability-stage {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(99, 102, 241, 0.20);
}

.capability-stage-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 6px;
}

.capability-stage-head-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.capability-stage-index {
  display: inline-flex;
  height: 20px;
  min-width: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.10);
  color: #6366f1;
  font-size: 10px;
  font-weight: 800;
}

.capability-stage-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin: 0;
}

html.dark .capability-stage-title { color: #f1f5f9; }

.capability-stage-description {
  margin-top: 1px;
  font-size: 10px;
  line-height: 1.4;
  color: #64748b;
}

html.dark .capability-stage-description { color: #94a3b8; }

.capability-stage-arrow {
  display: flex;
  justify-content: center;
  color: #818cf8;
  opacity: 0.8;
  padding: 2px 0;
}

.capability-stage-arrow svg {
  width: 12px;
  height: 12px;
}

.analysis-module-grid {
  display: grid;
  gap: 6px;
}

.analysis-module-grid.governance {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.analysis-module-grid.modeling {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.analysis-module-grid.output {
  grid-template-columns: minmax(0, 1fr);
}

.analysis-module-card {
  position: relative;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
  padding: 10px 12px;
  overflow: hidden;
  transition: box-shadow 160ms ease, transform 160ms ease;
}

.analysis-module-card:hover {
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

html.dark .analysis-module-card {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(99, 102, 241, 0.10);
}

.analysis-module-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 13px;
  height: 13px;
  color: var(--module-accent, #6366f1);
  opacity: 0.74;
}

.analysis-module-card h3 {
  padding-right: 20px;
  font-size: 12px;
  font-weight: 800;
  color: #111827;
  margin: 0 0 3px;
}

html.dark .analysis-module-card h3 { color: #f1f5f9; }

.module-summary {
  margin: 0 0 4px;
  font-size: 10px;
  line-height: 1.4;
  color: #64748b;
}

html.dark .module-summary { color: #94a3b8; }

.module-flow {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 5px;
}

.flow-label {
  font-size: 9px;
  font-weight: 700;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.07);
  padding: 1px 6px;
  border-radius: 999px;
}

.flow-arrow-icon {
  width: 11px;
  height: 11px;
  color: #818cf8;
  opacity: 0.7;
  flex-shrink: 0;
}

/* Business value */
.module-value {
  margin: 0;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.07);
  padding: 5px 8px;
  font-size: 10px;
  line-height: 1.45;
  color: #047857;
}

/* Remove old module styles that are no longer used */

/* ===== RESULT ===== */
.status-stack {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.status-section {
  margin-bottom: 0;
}

.status-icon { width: 20px; height: 20px; flex-shrink: 0; }

.status-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 12px;
}

.status-title.done { color: #059669; }
.status-title.progress { color: #d97706; }
.status-title.plan { color: #64748b; }

.status-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.status-chip {
  font-size: 14px;
  font-weight: 600;
  padding: 8px 14px;
  border-radius: 999px;
}

.status-chip.done {
  background: rgba(5, 150, 105, 0.08);
  color: #059669;
  border: 1px solid rgba(5, 150, 105, 0.16);
}

.status-chip.progress {
  background: rgba(217, 119, 6, 0.08);
  color: #d97706;
  border: 1px solid rgba(217, 119, 6, 0.16);
}

.status-chip.plan {
  background: rgba(100, 116, 139, 0.08);
  color: #64748b;
  border: 1px solid rgba(100, 116, 139, 0.14);
}

/* ===== CTA ===== */
.cta {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(168, 85, 247, 0.06) 100%);
}

html.dark .cta {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.04) 0%, rgba(168, 85, 247, 0.04) 100%);
}

.cta-inner {
  max-width: 600px;
  text-align: center;
  padding: 0 40px;
}

.cta-inner h2 {
  font-size: clamp(26px, 3.5vw, 38px);
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #111827;
  margin: 0 0 14px;
  line-height: 1.2;
}

html.dark .cta-inner h2 { color: #f1f5f9; }

.cta-inner p {
  font-size: 15px;
  color: #64748b;
  line-height: 1.7;
  margin: 0 0 28px;
}

html.dark .cta-inner p { color: #94a3b8; }

/* ===== RESPONSIVE ===== */
@media (max-width: 1024px) {
  .triple-cards { grid-template-columns: 1fr; }
  .analysis-module-grid.modeling { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tech-grid { grid-template-columns: repeat(2, 1fr); }
  .pain-grid { grid-template-columns: 1fr; }
  .status-stack { gap: 20px; }
}

@media (max-width: 768px) {
  .snap-slide { padding: 40px 24px; }
  .slide-inner { max-width: 100%; }
  .hero-content { padding: 0 24px; }
  .workflow-track {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    max-width: 280px;
    margin: 0 auto;
    gap: 10px;
  }
  .workflow-track::before { display: none; }
  .workflow-track::after { display: none; }
  .workflow-terminal,
  .workflow-step { min-height: auto; padding: 14px 16px; }
  .infra-elements { grid-template-columns: 1fr; }
  .tech-grid { grid-template-columns: repeat(2, 1fr); }
  .backend-boundary,
  .infrastructure-boundary { padding: 18px; border-radius: 24px; }
}

@media (max-width: 480px) {
  .tech-grid { grid-template-columns: 1fr; }
  .analysis-module-grid.governance,
  .analysis-module-grid.modeling,
  .analysis-module-grid.output { grid-template-columns: 1fr; }
}
</style>
