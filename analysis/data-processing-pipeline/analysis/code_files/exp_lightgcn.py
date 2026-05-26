# -*- coding: utf-8 -*-
"""
深化模块 A：真正的 LightGCN 训练（torch + BPR），与截断 SVD 二部图嵌入同协议对比。
LightGCN (He et al. 2020)：无特征变换/非线性，纯邻域传播。
  归一化邻接 Â = D^{-1/2} A D^{-1/2}（A 为用户-商品二部图对称邻接）
  E^{(k+1)} = Â E^{(k)} ,  最终嵌入 E = (1/(L+1)) Σ_{k=0}^L E^{(k)}
  打分 score(u,i)=e_u·e_i ,  BPR 损失: -Σ logσ(s_{u,i+}-s_{u,i-}) + λ‖E^0‖²

评估：1–3月训练/4月验证，全目录排序(剔除训练已购)，HitRate/Recall/NDCG@K。
产出：
  output/csvs/lightgcn_vs_svd.csv
  output/figures/dl_LightGCN学习曲线.png
  output/figures/dl_LightGCN_vs_SVD.png
  output/pkls/lightgcn.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from config import load_clean, save_csv, set_style, savefig, save_pkl, PALETTE

SPLIT_DATE = pd.Timestamp("2025-04-01")
RNG = 42
np.random.seed(RNG); torch.manual_seed(RNG)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def build_interactions(train):
    users = np.sort(train["user_id"].unique())
    items = np.sort(train["item_id"].unique())
    uidx = {u: i for i, u in enumerate(users)}
    iidx = {it: j for j, it in enumerate(items)}
    agg = train.groupby(["user_id", "item_id"])["amount"].sum().reset_index()
    rows = agg["user_id"].map(uidx).values
    cols = agg["item_id"].map(iidx).values
    return users, items, uidx, iidx, rows, cols


def norm_adj(n_u, n_i, rows, cols):
    """构造对称归一化二部图邻接 Â (torch sparse)。"""
    N = n_u + n_i
    r = np.concatenate([rows, cols + n_u])
    c = np.concatenate([cols + n_u, rows])
    d = np.ones(len(r))
    deg = np.zeros(N)
    np.add.at(deg, r, 1.0)
    dinv = np.power(deg, -0.5, where=deg > 0); dinv[deg == 0] = 0
    vals = dinv[r] * d * dinv[c]
    idx = torch.tensor(np.vstack([r, c]), dtype=torch.long)
    return torch.sparse_coo_tensor(idx, torch.tensor(vals, dtype=torch.float32),
                                   (N, N)).coalesce().to(DEVICE)


class LightGCN(nn.Module):
    def __init__(self, n_u, n_i, dim=64, n_layers=3):
        super().__init__()
        self.n_u, self.n_i, self.L = n_u, n_i, n_layers
        self.emb = nn.Embedding(n_u + n_i, dim)
        nn.init.normal_(self.emb.weight, std=0.1)

    def propagate(self, adj):
        e = self.emb.weight
        outs = [e]
        for _ in range(self.L):
            e = torch.sparse.mm(adj, e)
            outs.append(e)
        e_final = torch.stack(outs, 0).mean(0)
        return e_final[:self.n_u], e_final[self.n_u:]

    def bpr_loss(self, adj, u, pi, ni, reg=1e-4):
        eu, ei = self.propagate(adj)
        pu, ppi, pni = eu[u], ei[pi], ei[ni]
        pos = (pu * ppi).sum(1)
        neg = (pu * pni).sum(1)
        loss = -torch.log(torch.sigmoid(pos - neg) + 1e-9).mean()
        reg_l = reg * (self.emb(torch.cat([u, pi + self.n_u, ni + self.n_u])).pow(2).sum() / len(u))
        return loss + reg_l


def train_lightgcn(adj, n_u, n_i, user_pos, dim=64, layers=3, epochs=260, bs=2048, lr=1e-3):
    model = LightGCN(n_u, n_i, dim, layers).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    u_arr = np.array([u for u, items in user_pos.items() for _ in items])
    i_arr = np.array([it for items in user_pos.values() for it in items])
    n = len(u_arr); curve = []
    for ep in range(epochs):
        perm = np.random.permutation(n)
        tot = 0.0; nb = 0
        for s in range(0, n, bs):
            b = perm[s:s + bs]
            u = u_arr[b]; pi = i_arr[b]
            ni = np.random.randint(0, n_i, size=len(b))
            # 重采样命中正样本的负样本
            for k in range(len(b)):
                while ni[k] in user_pos[u[k]]:
                    ni[k] = np.random.randint(0, n_i)
            ut = torch.tensor(u, dtype=torch.long, device=DEVICE)
            pit = torch.tensor(pi, dtype=torch.long, device=DEVICE)
            nit = torch.tensor(ni, dtype=torch.long, device=DEVICE)
            opt.zero_grad()
            loss = model.bpr_loss(adj, ut, pit, nit)
            loss.backward(); opt.step()
            tot += loss.item(); nb += 1
        if ep % 20 == 0 or ep == epochs - 1:
            curve.append((ep, tot / nb))
    model.eval()
    with torch.no_grad():
        eu, ei = model.propagate(adj)
    return model, eu.cpu().numpy(), ei.cpu().numpy(), curve


def eval_embeddings(P, Q, uidx, iidx, items, user_seen, truth, K_list=(5, 10)):
    """全目录排序(剔除训练已购)评估。"""
    iidx_inv = {j: it for it, j in iidx.items()}
    res = {k: dict(hit=0, rec=0.0, ndcg=0.0, n=0) for k in K_list}
    for u, tset in truth.items():
        if u not in uidx:
            continue
        scores = Q @ P[uidx[u]]
        seen = user_seen.get(u, set())
        for j in range(len(scores)):
            if iidx_inv[j] in seen:
                scores[j] = -1e9
        order = np.argsort(-scores)
        rec_items = [iidx_inv[j] for j in order[:max(K_list)]]
        for k in K_list:
            topk = rec_items[:k]
            hit = len(set(topk) & tset)
            res[k]["hit"] += 1 if hit > 0 else 0
            res[k]["rec"] += hit / len(tset)
            dcg = sum(1.0 / np.log2(r + 2) for r, it in enumerate(topk) if it in tset)
            idcg = sum(1.0 / np.log2(r + 2) for r in range(min(len(tset), k)))
            res[k]["ndcg"] += dcg / idcg if idcg > 0 else 0
            res[k]["n"] += 1
    out = {}
    for k in K_list:
        nz = res[k]["n"] or 1
        out[k] = dict(HitRate=res[k]["hit"] / nz, Recall=res[k]["rec"] / nz,
                      NDCG=res[k]["ndcg"] / nz)
    return out


def main():
    set_style()
    df = load_clean()
    pos = df[df["is_return"] == 0]
    train = pos[pos["sale_date"] < SPLIT_DATE]
    test = pos[pos["sale_date"] >= SPLIT_DATE]
    users, items, uidx, iidx, rows, cols = build_interactions(train)
    n_u, n_i = len(users), len(items)
    print(f"LightGCN 图: 用户 {n_u} 商品 {n_i} 交互 {len(rows)} | device={DEVICE}")

    user_pos = {}
    for u, it in zip(rows, cols):
        user_pos.setdefault(int(u), set()).add(int(it))
    user_seen = {users[u]: {items[i] for i in its} for u, its in user_pos.items()}
    truth = test.groupby("user_id")["item_id"].apply(set).to_dict()
    truth = {u: s for u, s in truth.items() if u in uidx}

    adj = norm_adj(n_u, n_i, rows, cols)

    # --- LightGCN ---
    model, P_lg, Q_lg, curve = train_lightgcn(adj, n_u, n_i, user_pos)
    res_lg = eval_embeddings(P_lg, Q_lg, uidx, iidx, items, user_seen, truth)

    # --- SVD baseline（同图、同评估）---
    M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_u, n_i))
    # 用与推荐模块一致的加权
    agg = train.groupby(["user_id", "item_id"]).agg(freq=("item_id", "size"),
                                                    amt=("amount", "sum")).reset_index()
    w = np.log1p(agg["freq"]) + np.log1p(agg["amt"].clip(lower=0))
    Mw = csr_matrix((w.values, (agg["user_id"].map(uidx), agg["item_id"].map(iidx))),
                    shape=(n_u, n_i))
    U, S, Vt = svds(Mw, k=64)
    P_svd = U * np.sqrt(S); Q_svd = Vt.T * np.sqrt(S)
    res_svd = eval_embeddings(P_svd, Q_svd, uidx, iidx, items, user_seen, truth)

    rows_out = []
    for name, res in [("二部图SVD嵌入", res_svd), ("LightGCN(训练)", res_lg)]:
        for k in (5, 10):
            rows_out.append({"模型": name, "K": k,
                             "HitRate": round(res[k]["HitRate"], 4),
                             "Recall": round(res[k]["Recall"], 4),
                             "NDCG": round(res[k]["NDCG"], 4)})
    comp = pd.DataFrame(rows_out)
    save_csv(comp, "lightgcn_vs_svd.csv")
    print("\n=== LightGCN vs SVD（全目录排序，剔除已购）===")
    print(comp.to_string(index=False))

    save_pkl({"P_lg": P_lg, "Q_lg": Q_lg, "uidx": uidx, "iidx": iidx}, "lightgcn.pkl")
    _plots(curve, comp)
    return comp


def _plots(curve, comp):
    ep, ls = zip(*curve)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(ep, ls, marker="o", color=PALETTE[0], lw=1.8, markerfacecolor="white")
    ax.set_xlabel("训练轮次 epoch"); ax.set_ylabel("BPR 损失")
    savefig(fig, "dl_LightGCN学习曲线.png")

    c10 = comp[comp["K"] == 10].set_index("模型")
    metrics = ["HitRate", "Recall", "NDCG"]
    x = np.arange(len(metrics)); wd = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(x - wd/2, c10.loc["二部图SVD嵌入", metrics].values, wd,
           label="二部图SVD嵌入", color=PALETTE[0], edgecolor="white")
    ax.bar(x + wd/2, c10.loc["LightGCN(训练)", metrics].values, wd,
           label="LightGCN(训练)", color=PALETTE[1], edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels([f"{m}@10" for m in metrics])
    ax.set_ylabel("指标值"); ax.legend()
    savefig(fig, "dl_LightGCN_vs_SVD.png")


if __name__ == "__main__":
    main()
