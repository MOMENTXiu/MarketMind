# 实验报告 07 · 深化：LightGCN 图神经推荐

> 脚本：`exp_lightgcn.py` ｜ 时间切分 1–3月训练/4月验证 ｜ device=CUDA

## 1. 动机
阶段5 的图召回用截断 SVD 低秩嵌入（线性）。本模块实现**可训练的 LightGCN**（He et al. 2020），验证图神经网络的非线性邻域传播能否进一步提升个性化召回。

## 2. 模型
二部图对称归一化邻接 (Â=D^{-1/2}AD^{-1/2})，逐层传播并层间平均：
$$E^{(k+1)}=\hat A E^{(k)},\quad E=\frac1{L+1}\sum_{k=0}^{L}E^{(k)},\quad score(u,i)=e_u^\top e_i$$
- 嵌入维度 64，层数 3，BPR 损失 + L2 正则，Adam(lr=1e-3)，260 epoch，负采样。
- **评估协议**：全目录排序，**剔除训练已购商品**（纯"发现型"任务，比阶段5允许复购的候选池更严格）。

## 3. 结果（全目录排序，剔除已购）

| 模型 | HitRate@10 | Recall@10 | NDCG@10 |
|---|---|---|---|
| 二部图 SVD 嵌入 | 0.206 | 0.024 | 0.030 |
| **LightGCN（训练）** | **0.351** | **0.053** | **0.072** |

LightGCN 相对 SVD：HitRate **+70%**、Recall **+119%**、NDCG **+140%**。BPR 损失随训练单调下降（`dl_LightGCN学习曲线.png`），收敛稳定。

## 4. 结论
可训练的图神经嵌入显著优于线性 SVD，验证了非线性高阶邻域传播对捕捉个性化偏好的价值。生产部署可用 LightGCN 替换阶段5 的 SVD 图召回路（其余融合框架不变）。

> 注：本协议剔除已购、全目录排序，数值低于阶段5（允许复购候选）的 0.443，二者口径不同，分别衡量"发现新品"与"含复购"两种场景。

## 5. 产出
- `output/csvs/lightgcn_vs_svd.csv`
- `output/figures/dl_LightGCN学习曲线.png`、`dl_LightGCN_vs_SVD.png`
- `output/pkls/lightgcn.pkl`
