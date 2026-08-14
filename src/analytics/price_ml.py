"""
Modulo 2 - Price Intelligence: modelo ML (LightGBM) vs baseline. Fase 8.
Mesmo split temporal do ADR-0003, mesmo escopo do ADR-0015 (categorias
relevantes, outliers excluidos) via prepare_baseline_dataset.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import lightgbm as lgb

from src.analytics.price_baseline import prepare_baseline_dataset, split_temporal

FEATURES_CATEGORICAS = ["item_key", "categoria_relevante", "unidade_orgao_uf_sigla", "unit_flag"]
FEATURES_NUMERICAS = ["log_quantity"]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cria log_quantity e log_unit_price (target). Sem leakage: nao usa
    total_price/valor_total (funcao direta do target)."""
    df = df.copy()
    df["log_quantity"] = np.log1p(df["quantity"].clip(lower=0))
    df["log_unit_price"] = np.log(df["unit_price"].clip(lower=1e-6))
    return df


def align_categorical_dtypes(df_treino: pd.DataFrame, *dfs_avaliacao: pd.DataFrame, cols: list[str] = FEATURES_CATEGORICAS):
    """Define categorias com base SOMENTE no treino (ADR-0003) e aplica o
    mesmo dtype categorico nos conjuntos de avaliacao -- categoria nao
    vista no treino vira NaN (LightGBM trata como missing/branch propria),
    nao quebra nem vaza informacao futura."""
    df_treino = df_treino.copy()
    resultado_avaliacao = [df.copy() for df in dfs_avaliacao]
    for col in cols:
        df_treino[col] = df_treino[col].astype("category")
        categorias = df_treino[col].cat.categories
        for df in resultado_avaliacao:
            df[col] = pd.Categorical(df[col], categories=categorias)
    return (df_treino, *resultado_avaliacao)


def train_lightgbm_model(df_treino: pd.DataFrame) -> lgb.LGBMRegressor:
    modelo = lgb.LGBMRegressor(
        n_estimators=300, learning_rate=0.05, num_leaves=63,
        min_child_samples=10, random_state=42, verbosity=-1,
    )
    features = FEATURES_CATEGORICAS + FEATURES_NUMERICAS
    modelo.fit(
        df_treino[features], df_treino["log_unit_price"],
        categorical_feature=FEATURES_CATEGORICAS,
    )
    return modelo


def evaluate_model(df_avaliacao: pd.DataFrame, modelo: lgb.LGBMRegressor) -> dict[str, Any]:
    features = FEATURES_CATEGORICAS + FEATURES_NUMERICAS
    log_pred = modelo.predict(df_avaliacao[features])
    pred = np.exp(log_pred)

    erro = df_avaliacao["unit_price"] - pred
    erro_abs = erro.abs()
    erro_pct = 100 * erro_abs / df_avaliacao["unit_price"].replace(0, np.nan)

    return {
        "n_transacoes": len(df_avaliacao),
        "pct_cobertura": 100.0,  # ML sempre prediz, ao contrario do baseline
        "mae": round(float(erro_abs.mean()), 2),
        "rmse": round(float(np.sqrt((erro**2).mean())), 2),
        "mape_media": round(float(erro_pct.mean()), 2),
        "mape_mediana": round(float(erro_pct.median()), 2),
    }


def compute_shap_summary(modelo: lgb.LGBMRegressor, df_amostra: pd.DataFrame, n_amostra: int = 2000) -> pd.DataFrame:
    """SHAP via pred_contrib nativo do LightGBM (sem dependencia extra)."""
    features = FEATURES_CATEGORICAS + FEATURES_NUMERICAS
    amostra = df_amostra[features].sample(min(n_amostra, len(df_amostra)), random_state=42)
    contrib = modelo.booster_.predict(amostra, pred_contrib=True)
    contrib_df = pd.DataFrame(contrib[:, :-1], columns=features)  # ultima coluna = base value
    importancia = contrib_df.abs().mean().sort_values(ascending=False)
    return importancia.reset_index().rename(columns={"index": "feature", 0: "impacto_medio_abs_log_price"})


def build_ml_report(df_fact: pd.DataFrame) -> dict[str, Any]:
    df_preparado = prepare_baseline_dataset(df_fact)
    df_preparado = engineer_features(df_preparado)
    splits = split_temporal(df_preparado)

    treino, validacao, teste = align_categorical_dtypes(
        splits["treino"], splits["validacao"], splits["teste"]
    )

    modelo = train_lightgbm_model(treino)
    resultado_validacao = evaluate_model(validacao, modelo)
    resultado_teste = evaluate_model(teste, modelo)
    shap_summary = compute_shap_summary(modelo, treino)

    return {
        "n_transacoes_treino": len(treino),
        "avaliacao_validacao": resultado_validacao,
        "avaliacao_teste": resultado_teste,
        "shap_top_features": shap_summary.to_dict(orient="records"),
    }, modelo
