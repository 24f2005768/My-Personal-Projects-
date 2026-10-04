import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, FunctionTransformer
from sklearn.metrics import precision_recall_curve, auc, confusion_matrix

PCA = [f"V{i}" for i in range(1, 29)]
FEATURES = PCA + ['Amount', 'hour_sin', 'hour_cos']

def _time_feats(X):
    '''
    Convert raw seconds-since-first-transaction into two cyclical features.
    '''
    X = X.copy()
    h = (X['Time'] / 3600.0) % 24 
    X['hour_sin'] = np.sin(2 * np.pi * h / 24)
    X['hour_cos'] = np.cos(2 * np.pi * h / 24)
    return X.drop(columns = ['Time'])

def preprocessor():
    '''
    returns the shared ColumnTransformer
    '''
    amount = Pipeline([
        ('log', FunctionTransformer(np.log1p, validate = False)),
        ('scale', StandardScaler()),
    ])
    return ColumnTransformer([
        ('t', FunctionTransformer(_time_feats, validate=False), ['Time']),
        ('a', amount, ['Amount']),
        ('p', 'passthrough', PCA)
    ])

def pr_auc(y, p):
    ''' 
    Precision-Recall AUC
    '''
    prec, rec, _ = precision_recall_curve(y, p)
    return prec, rec, float(auc(rec, prec))

def cost_scan(y, p, c_fn = 100.0, c_fp = 5.0):
    '''Sweep thresholds return per-threshold metrics + the cost-minimizing threshold.'''
    ts = np.linspace(0.01, 0.99, 99)
    costs, precs, recs, f1s = [], [], [], []
    for t in ts:
        pred = (p >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels = [0,1]).ravel()
        costs.append(fn * c_fn + fp * c_fp)
        pr = tp / (tp + fp) if (tp + fp) else 0
        rc = tp / (tp + fn) if (tp + fn) else 0
        precs.append(pr)
        recs.append(rc)
        f1s.append(2 * pr * rc / (pr + rc) if (pr + rc) else 0)
    i = int(np.argmin(costs))
    return {
        "thresholds": ts.tolist(),
        "costs": costs,
        "precision": precs,
        "recall": recs,
        "f1": f1s,
        "best_threshold": float(ts[i]),
        "best_cost": float(costs[i]),
        "best_precision": float(precs[i]),
        "best_recall": float(recs[i]),
        "best_f1": float(f1s[i]),
    }

def pick_two_thresholds(y, p, c_fn, c_fp, review_cost, capacity_per_day, n_days):
    """
    Choose the two decision thresholds that split three outcomes:
      p < t_review              -> approve
      t_review <= p < t_decline -> review (human)
      p >= t_decline            -> decline
   
    """
    scan = cost_scan(y, p, c_fn, c_fp)
    t_decline = scan = scan['best_threshold']

    # Candidate review thresholds must sit below t_decline — otherwise the
    # review band is empty or inverted.
    candidates = np.linspace(0.01, t_decline - 0.001, 50)
    daily_budget = capacity_per_day * n_days

    best = {"t_review": 0.01, "cost": np.inf, "alerts": 0}
    for t_r in candidates:
        alerts = int(((p >= t_r) & (p < t_decline)).sum())
        if alerts > daily_budget:
            continue
        fn = int(((p < t_r) & (y == 1)).sum())
        fp = int(((p >= t_decline) & (y == 0)).sum())
        total = fn * c_fn + fp * c_fp + alerts * review_cost
        if total < best['cost']:
            best = {'t_review': float(t_r), 'cost': total, 'alerts': alerts}

    return {
        "t_decline": t_decline,
    "t_review": best["t_review"],
    "total_cost": best["cost"],
    "alerts_in_review": best["alerts"],
    "capacity_used_pct": 100.0 * best["alerts"] / max(daily_budget, 1),
    }