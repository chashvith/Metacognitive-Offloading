"""
train_model.py
==============
Cognitive Coach â€“ ML Training Pipeline

Reads all session JSON files from the dataset/ folder,
extracts features, trains a Random Forest + XGBoost classifier,
evaluates them, saves the best model, and prints a full report.

Target (Y): minimum_help_required
  0 = Solved independently
  1 = Hint 1
  2 = Hint 2
  3 = Concept
  4 = Pseudocode
  5 = Full Solution
  6 = Could Not Solve

Usage:
  python scripts/train_model.py
"""

import os
import json
import numpy as np
import pandas as pd
import pickle
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

DATASET_DIR   = Path(__file__).parent.parent / 'dataset'
MODEL_DIR     = Path(__file__).parent.parent / 'model'
MODEL_PATH    = MODEL_DIR / 'cognitive_coach_model.pkl'
REPORT_PATH   = MODEL_DIR / 'training_report.txt'

MODEL_DIR.mkdir(exist_ok=True)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. LOAD ALL SESSION JSONS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_sessions(dataset_dir: Path) -> list[dict]:
    sessions = []
    skipped = 0
    for f in dataset_dir.glob('session_*.json'):
        try:
            with open(f) as fp:
                s = json.load(fp)
            # Only keep sessions with a valid outcome label
            if s.get('outcome') and s['outcome'].get('minimum_help_required') is not None:
                sessions.append(s)
            else:
                skipped += 1
        except Exception:
            skipped += 1
    print(f"âœ… Loaded {len(sessions)} sessions  ({skipped} skipped / no outcome label)")
    return sessions

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. FEATURE EXTRACTION
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

DIFFICULTY_MAP = {'Easy': 0, 'Medium': 1, 'Hard': 2}

def extract_features(session: dict) -> dict | None:
    """Extract the flat feature vector from a single session JSON."""
    try:
        dm = session.get('derived_metrics') or {}
        hr = session.get('hints_requested') or {}
        ss = session.get('struggle_scores') or []

        # Struggle score stats
        scores = [e['score'] for e in ss] if ss else [0]
        struggle_max   = max(scores)
        struggle_mean  = float(np.mean(scores))
        struggle_final = scores[-1] if scores else 0
        struggle_trend = (scores[-1] - scores[0]) if len(scores) > 1 else 0

        # Timeline stats
        timeline = session.get('timeline') or []
        compile_events = [e for e in timeline if e['event'] in ('compile_error', 'compile_success')]
        first_compile_t = compile_events[0]['time'] if compile_events else -1

        hint_events = [e for e in timeline if 'hint' in e['event'] or e['event'] == 'solution_requested']
        first_hint_t = hint_events[0]['time'] if hint_events else -1

        time_spent = session.get('time_spent') or 1

        return {
            # â”€â”€ Time features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'time_spent':           time_spent,
            'idle_ratio':           (session.get('idle_time') or 0) / time_spent,

            # â”€â”€ Typing features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'chars_typed':          session.get('characters_typed') or 0,
            'chars_deleted':        session.get('characters_deleted') or 0,
            'deletion_ratio':       session.get('deletion_ratio') or 0,
            'typing_speed':         session.get('typing_speed') or 0,

            # â”€â”€ Pause features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'pause_count':          session.get('pause_count') or 0,
            'pause_duration':       session.get('pause_duration') or 0,
            'avg_pause_duration':   dm.get('average_pause_duration') or 0,
            'hesitation_index':     dm.get('hesitation_index') or 0,

            # â”€â”€ Compile features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'compile_attempts':     session.get('compile_attempts') or 0,
            'compile_errors':       session.get('compile_errors') or 0,
            'successful_runs':      session.get('successful_runs') or 0,
            'runtime_errors':       session.get('runtime_errors') or 0,
            'compile_failure_rate': dm.get('compile_failure_rate') or 0,
            'same_error_peak':      session.get('same_error_peak') or 0,
            'first_compile_time':   first_compile_t,

            # â”€â”€ Hint features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'hints_used':           session.get('hints_used') or 0,
            'hints_available':      session.get('hints_available') or 0,
            'hint1':                hr.get('hint1') or 0,
            'hint2':                hr.get('hint2') or 0,
            'concept':              hr.get('concept') or 0,
            'pseudocode':           hr.get('pseudocode') or 0,
            'solution':             hr.get('solution') or 0,
            'help_dependency':      dm.get('help_dependency_score') or 0,
            'first_hint_time':      first_hint_t,
            'independent_fix_rate': session.get('independent_fix_rate') or 1,

            # â”€â”€ Editing features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'editing_intensity':    dm.get('editing_intensity') or 0,
            'file_save_count':      session.get('file_save_count') or 0,

            # â”€â”€ Struggle score features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'struggle_max':         struggle_max,
            'struggle_mean':        struggle_mean,
            'struggle_final':       struggle_final,
            'struggle_trend':       struggle_trend,

            # â”€â”€ Problem metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            'difficulty':           DIFFICULTY_MAP.get(session.get('difficulty') or 'Easy', 0),
        }
    except Exception as e:
        return None

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 3. BUILD DATAFRAME
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_dataframe(sessions: list[dict]) -> tuple[pd.DataFrame, pd.Series]:
    rows, labels = [], []
    for s in sessions:
        feats = extract_features(s)
        if feats is None:
            continue
        rows.append(feats)
        labels.append(s['outcome']['minimum_help_required'])

    X = pd.DataFrame(rows)
    y = pd.Series(labels, name='minimum_help_required')
    return X, y

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4. TRAIN + EVALUATE
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def train(X: pd.DataFrame, y: pd.Series):
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
    from sklearn.preprocessing import LabelEncoder
    from xgboost import XGBClassifier

    print(f"\nðŸ“Š Dataset: {len(X)} samples, {X.shape[1]} features")
    print(f"\n📊 Dataset: {len(X)} samples, {X.shape[1]} features")
    print(f"📊 Label distribution:\n{y.value_counts().sort_index()}\n")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Model 1: Random Forest ─────────────────────────────────────────────
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_acc  = accuracy_score(y_test, rf_pred)
    rf_cv   = cross_val_score(rf, X, y, cv=5, scoring='accuracy').mean()

    print("=" * 60)
    print(f"🌲 Random Forest  — Test Acc: {rf_acc:.3f}  |  CV-5 Acc: {rf_cv:.3f}")
    print("=" * 60)
    print(classification_report(y_test, rf_pred,
          target_names=[f"Help={i}" for i in range(5)],
          zero_division=0))

    # ── Model 2: XGBoost ──────────────────────────────────────────────────
    from sklearn.utils.class_weight import compute_sample_weight
    
    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc  = le.transform(y_test)
    
    sample_weights = compute_sample_weight('balanced', y_train_enc)

    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )
    xgb.fit(X_train, y_train_enc, eval_set=[(X_test, y_test_enc)], sample_weight=sample_weights, verbose=False)
    xgb_pred     = le.inverse_transform(xgb.predict(X_test))
    xgb_acc      = accuracy_score(y_test, xgb_pred)
    y_enc_all    = le.transform(y)
    xgb_cv       = cross_val_score(
        XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                      use_label_encoder=False, eval_metric='mlogloss',
                      random_state=42, verbosity=0),
        X, y_enc_all, cv=5, scoring='accuracy'
    ).mean()

    print("=" * 60)
    print(f"âš¡ XGBoost         â€” Test Acc: {xgb_acc:.3f}  |  CV-5 Acc: {xgb_cv:.3f}")
    print("=" * 60)
    print(classification_report(y_test, xgb_pred,
          target_names=[f"Help={i}" for i in range(5)],
          zero_division=0))

    # â”€â”€ Feature Importance (Random Forest) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    importances = pd.Series(rf.feature_importances_, index=X.columns)
    top10 = importances.sort_values(ascending=False).head(10)
    print("\nðŸ”‘ Top 10 Most Important Features (Random Forest):")
    for feat, imp in top10.items():
        bar = "â–ˆ" * int(imp * 40)
        print(f"  {feat:<30} {bar} {imp:.4f}")

    # â”€â”€ Choose best model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    best_model  = rf if rf_acc >= xgb_acc else xgb
    best_name   = "RandomForest" if rf_acc >= xgb_acc else "XGBoost"
    best_acc    = max(rf_acc, xgb_acc)

    return best_model, best_name, best_acc, rf, xgb, rf_acc, xgb_acc, le

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 5. SAVE MODEL
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_model(model, label_encoder, feature_names, model_name, accuracy):
    artifact = {
        'model':         model,
        'label_encoder': label_encoder,
        'feature_names': feature_names,
        'model_name':    model_name,
        'accuracy':      accuracy,
    }
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(artifact, f)
    print(f"\nâœ… Saved best model ({model_name}, acc={accuracy:.3f}) to: {MODEL_PATH}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 6. PREDICT HELPER (can be imported separately later)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def predict_from_session(session_json: dict) -> dict:
    """
    Given a raw session JSON dict, returns the predicted
    minimum_help_required label and confidence scores.
    """
    with open(MODEL_PATH, 'rb') as f:
        artifact = pickle.load(f)

    model    = artifact['model']
    le       = artifact['label_encoder']
    features = artifact['feature_names']

    feats = extract_features(session_json)
    if feats is None:
        return {'error': 'Could not extract features from session'}

    X = pd.DataFrame([feats])[features]
    
    # Random Forest: predict_proba gives class probabilities
    from sklearn.ensemble import RandomForestClassifier
    if isinstance(model, RandomForestClassifier):
        proba  = model.predict_proba(X)[0]
        pred   = int(model.predict(X)[0])
        confidence = float(proba[pred])
    else:
        # XGBoost: decode label
        pred_enc   = model.predict(X)[0]
        pred       = int(le.inverse_transform([pred_enc])[0])
        proba      = model.predict_proba(X)[0]
        confidence = float(proba[pred_enc])

    help_labels = {
        0: "Independent",
        1: "Hint 1",
        2: "Hint 2",
        3: "Concept",
        4: "Pseudocode",
        5: "Full Solution",
        6: "Could Not Solve"
    }

    return {
        'predicted_min_help': pred,
        'label':              help_labels.get(pred, str(pred)),
        'confidence':         round(confidence, 3),
        'probabilities':      {help_labels.get(i, str(i)): round(float(p), 3)
                               for i, p in enumerate(proba)}
    }

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == '__main__':
    print("ðŸ§  Cognitive Coach â€” ML Training Pipeline")
    print("=" * 60)

    sessions = load_sessions(DATASET_DIR)

    if len(sessions) < 10:
        print("âŒ Not enough data. Run generate_synthetic_data.py first.")
        exit(1)

    X, y = build_dataframe(sessions)
    best_model, best_name, best_acc, rf, xgb, rf_acc, xgb_acc, le = train(X, y)

    save_model(best_model, le, list(X.columns), best_name, best_acc)

    print("\nðŸŽ‰ Training complete!")
    print(f"   Best model  : {best_name}")
    print(f"   Test accuracy: {best_acc:.1%}")
    print(f"   Model saved : {MODEL_PATH}")
    print("\n   You can now import predict_from_session() to use the model!")

