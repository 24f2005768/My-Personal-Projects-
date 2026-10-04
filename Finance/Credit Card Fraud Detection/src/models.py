# --- sklearn: linear, distance, probabilistic, margin ---
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

# --- sklearn: trees and ensembles ---
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)

# --- pipelines ---
from sklearn.pipeline import Pipeline
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

# --- boosted libraries ---
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from src.config import SEED
from src.pipeline import preprocessor

# Wrappers
def _plain(clf):
    """
    Preprocessor + classifier. Use when the model handles imbalance itself
    """
    return Pipeline([('prep', preprocessor()), ('clf', clf)])

def _smote(clf):
    '''
    Preprocessor + SMOTE + classifier.
    '''
    return ImbPipeline([
        ('prep', preprocessor()),
        ('smote', SMOTE(random_state = SEED, k_neighbors = 5)),
        ('clf', clf),
    ])

# Builders
# Linear 
def build_logistic():
    # Linear baseline. `class_weight="balanced"` reweights the loss by
    # inverse class frequency, which is enough for a linear model.
    return _plain(LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        random_state=SEED
    ))

# Distance based
def build_knn():
    # KNN has no class_weight, so SMOTE balances classes at fit time.
    # n_jobs=-1 parallelizes the neighbor lookups at predict time.
    return _smote(KNeighborsClassifier(n_neighbors=5, n_jobs = -1))

# Probabilistic
def build_naive_bayes():
    # GaussianNB assumes features are independent and Gaussian.
    # PCA components are correlated, so this assumption is violated —
    # part of the lesson is seeing how much that costs.
    return _smote(GaussianNB())

# Margin based 
def build_linear_svc():
    # LinearSVC has no predict_proba. CalibratedClassifierCV wraps it and
    # learns a sigmoid mapping from decision scores to probabilities, which
    # we need for the cost-sensitive threshold logic downstream.
    # class_weight handles imbalance directly.
    return _plain(CalibratedClassifierCV(
        LinearSVC(class_weight='balanced', random_state=SEED, max_iter=5000),
        method = 'sigmoid',
        cv = 3,
    ))

# Trees
def build_decision_tree():
    # A single tree overfits on 0.17% fraud unless heavily constrained.
    # max_depth and min_samples_leaf are the two knobs that matter most.
    return _smote(DecisionTreeClassifier(
        max_depth=8,
        min_samples_leaf=5,
        random_state=SEED
    ))

def build_random_forest():
    # Bagged trees. class_weight="balanced_subsample" recomputes weights
    # per bootstrap sample, which is slightly better than "balanced" here.
    return _plain(RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        class_weight='balanced_subsample',
        n_jobs=-1,
        random_state=SEED
    ))

def build_gradient_boosting():
    # Classic sklearn booster. Slower than HistGradientBoosting but useful
    # as a reference point. No class_weight, so SMOTE.
    return _smote(GradientBoostingClassifier(
        n_estimators=150,
        max_depth=3,
        learning_rate=0.1,
        random_state=SEED
    ))

def build_hist_gradient_boosting():
    # sklearn's fast booster (histogram-binned, similar idea to LightGBM).
    # 10–50× faster than GradientBoosting on this data size, with similar
    # accuracy. Uses SMOTE because it has no class_weight parameter.
    return _smote(HistGradientBoostingClassifier(
        max_iter=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=SEED
    ))

# Boosted
def build_xgboost():
    # XGBoost handles imbalance via scale_pos_weight, so no SMOTE needed.
    return _plain(XGBClassifier(
        n_estimators = 200,
        max_depth = 6,
        learning_rate = 0.1,
        scale_pos_weight = 100,
        eval_metric = 'aucpr',
        tree_method = 'hist',
        n_jobs = -1, 
        random_state = SEED
    ))

def build_lightgbm():
    # LightGBM handles imbalance via class_weight, so no SMOTE needed.
    return _plain(LGBMClassifier(
        n_estimators = 200,
        max_depth = 6,
        num_leaves = 31,
        learning_rate = 0.1,
        min_child_samples = 20,
        class_weight = 'balanced',
        n_jobs = -1,
        random_state = SEED,
        verbose = -1
    ))

_BUILDERS = {
    "LogisticRegression":     build_logistic,
    "KNeighborsClassifier":   build_knn,
    "GaussianNB":             build_naive_bayes,
    "LinearSVC (calibrated)": build_linear_svc,
    "DecisionTree":           build_decision_tree,
    "RandomForest":           build_random_forest,
    "GradientBoosting":       build_gradient_boosting,
    "HistGradientBoosting":   build_hist_gradient_boosting,
    "XGBoost":                build_xgboost,
    "LightGBM":               build_lightgbm,
}

def all_models():
    return dict(_BUILDERS)