'''
Fraud teams have run hand-written rules for decades. Three classic ones:
  - amount > threshold (large purchases are riskier)
  - velocity: too many transactions in a short window
  - (in a real system: geo-impossibility, new merchant, unusual hour)

The ML model has to beat these to earn its place. Without this baseline, a
reader has no way to judge whether the model is actually doing anything.
'''

import pandas as pd 

def rule_decisions(df, cfg):
    '''
    Returns a Series: 0 = approve, 1 = review, 2 = decline.

    Velocity is computed by bucketing Time into fixed windows and counting
    rows per bucket. This is a crude approximation of a real rolling count
    but matches the spirit of what a production rule engine would do.
    '''
    n_per_time = df.groupby(df['Time'] // cfg['window'])['Time'].transform('size')
    high_amount = df['Amount'] > cfg['amount_threshold']
    high_velocity = n_per_time >= cfg['velocity_max']

    decision = pd.Series(0, index = df.index)
    decision[high_amount] = 1   # amount alone is a soft signal -> review
    decision[high_velocity] = 2 # velocity pattern is a hard signal -> decline
    return decision 

def evaluate_rules(df, y, cfg, c_fn, c_fp, review_cost):
    d = rule_decisions(df, cfg)
    y = y.values 
    fn = int(((d == 0) & (y ==1)).sum()) # approved but actually fraud
    fp = int(((d == 2) & (y == 0)).sum()) # declined but actually legit 
    reviews = int((d == 1).sum())
    tp_decline = int(((d == 2) & (y == 1)).sum())
    tp_review = int(((d == 1) & (y == 1)).sum())
    cost = fn * c_fn + fp * c_fp + reviews * review_cost
    recall = (tp_decline + tp_review) / max(int(y.sum()), 1)

    return {
        "cost": float(cost),
        "recall": float(recall),
        "missed_frauds": fn,
        "false_alarms": fp,
        "reviews": reviews,
    }
s