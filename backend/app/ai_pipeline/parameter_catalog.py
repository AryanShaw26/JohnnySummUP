"""
Canonical Parameter Catalog for JohnnySummUP V1.
Maps raw lab test names and synonyms to standardized parameter codes,
canonical display names, approved units, and comparability rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParameterDefinition:
    parameter_code: str
    canonical_name: str
    category: str
    synonyms: List[str]
    supported_units: List[str]
    comparability_notes: str = ""


PARAMETER_CATALOG: Dict[str, ParameterDefinition] = {
    "hemoglobin": ParameterDefinition(
        parameter_code="hemoglobin",
        canonical_name="Hemoglobin",
        category="Hematology",
        synonyms=["hb", "hgb", "haemoglobin", "blood hemoglobin", "total hemoglobin"],
        supported_units=["g/dl", "g/l", "mmol/l"],
        comparability_notes="Directly comparable when units match.",
    ),
    "wbc": ParameterDefinition(
        parameter_code="wbc",
        canonical_name="White Blood Cell Count",
        category="Hematology",
        synonyms=["wbc", "white blood cells", "leukocyte count", "total leukocyte count", "tlc", "leukocytes"],
        supported_units=["10^3/ul", "k/ul", "/cumm", "cells/cumm", "10^9/l", "/ul", "thou/ul"],
        comparability_notes="Comparable when normalized or matching units.",
    ),
    "rbc": ParameterDefinition(
        parameter_code="rbc",
        canonical_name="Red Blood Cell Count",
        category="Hematology",
        synonyms=["rbc", "red blood cells", "erythrocyte count", "total rbc", "erythrocytes"],
        supported_units=["10^6/ul", "mil/ul", "m/ul", "10^12/l"],
        comparability_notes="Comparable across standard counts.",
    ),
    "platelets": ParameterDefinition(
        parameter_code="platelets",
        canonical_name="Platelet Count",
        category="Hematology",
        synonyms=["platelets", "platelet count", "thrombocytes", "plt", "total platelets"],
        supported_units=["10^3/ul", "k/ul", "/cumm", "lakhs/cumm", "10^9/l", "/ul"],
        comparability_notes="Comparable across standard counts.",
    ),
    "fasting_glucose": ParameterDefinition(
        parameter_code="fasting_glucose",
        canonical_name="Fasting Blood Glucose",
        category="Metabolic / Glycemic",
        synonyms=["fasting glucose", "fbs", "glucose fasting", "blood sugar fasting", "fasting blood sugar"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="Only compare with documented fasting status.",
    ),
    "postprandial_glucose": ParameterDefinition(
        parameter_code="postprandial_glucose",
        canonical_name="Post-Prandial Glucose",
        category="Metabolic / Glycemic",
        synonyms=["ppbs", "glucose post prandial", "blood sugar pp", "post prandial blood sugar", "pp glucose"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="Compare with standardized post-meal timing.",
    ),
    "hba1c": ParameterDefinition(
        parameter_code="hba1c",
        canonical_name="Hemoglobin A1c (HbA1c)",
        category="Metabolic / Glycemic",
        synonyms=["hba1c", "glycated hemoglobin", "glycosylated hemoglobin", "a1c"],
        supported_units=["%", "mmol/mol"],
        comparability_notes="Gold standard 3-month glycemic marker.",
    ),
    "total_cholesterol": ParameterDefinition(
        parameter_code="total_cholesterol",
        canonical_name="Total Cholesterol",
        category="Lipid Profile",
        synonyms=["total cholesterol", "cholesterol total", "serum cholesterol", "cholesterol"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="Fasting sample preferred.",
    ),
    "hdl_cholesterol": ParameterDefinition(
        parameter_code="hdl_cholesterol",
        canonical_name="HDL Cholesterol",
        category="Lipid Profile",
        synonyms=["hdl", "hdl cholesterol", "high density lipoprotein", "hdl-c"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="Comparable across lipid profiles.",
    ),
    "ldl_cholesterol": ParameterDefinition(
        parameter_code="ldl_cholesterol",
        canonical_name="LDL Cholesterol",
        category="Lipid Profile",
        synonyms=["ldl", "ldl cholesterol", "low density lipoprotein", "ldl-c"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="Calculated vs direct measurement noted.",
    ),
    "triglycerides": ParameterDefinition(
        parameter_code="triglycerides",
        canonical_name="Triglycerides",
        category="Lipid Profile",
        synonyms=["triglycerides", "tg", "serum triglycerides", "trigs"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="High sensitivity to fasting status.",
    ),
    "creatinine": ParameterDefinition(
        parameter_code="creatinine",
        canonical_name="Serum Creatinine",
        category="Renal Function",
        synonyms=["creatinine", "serum creatinine", "creat", "s. creatinine"],
        supported_units=["mg/dl", "umol/l", "µmol/l"],
        comparability_notes="Comparable when method and assay are standardized.",
    ),
    "blood_urea_nitrogen": ParameterDefinition(
        parameter_code="blood_urea_nitrogen",
        canonical_name="Blood Urea Nitrogen (BUN)",
        category="Renal Function",
        synonyms=["bun", "blood urea nitrogen", "urea", "serum urea"],
        supported_units=["mg/dl", "mmol/l"],
        comparability_notes="Note whether reporting Urea vs BUN.",
    ),
    "tsh": ParameterDefinition(
        parameter_code="tsh",
        canonical_name="Thyroid Stimulating Hormone (TSH)",
        category="Endocrine / Thyroid",
        synonyms=["tsh", "thyroid stimulating hormone", "thyrotropin", "ultrasensitive tsh"],
        supported_units=["uiu/ml", "miu/l", "uu/ml", "mcu/ml"],
        comparability_notes="Comparable across standard immunoassays.",
    ),
    "free_t3": ParameterDefinition(
        parameter_code="free_t3",
        canonical_name="Free T3",
        category="Endocrine / Thyroid",
        synonyms=["ft3", "free t3", "triiodothyronine free"],
        supported_units=["pg/ml", "pmol/l"],
        comparability_notes="Compare with identical assay types.",
    ),
    "free_t4": ParameterDefinition(
        parameter_code="free_t4",
        canonical_name="Free T4",
        category="Endocrine / Thyroid",
        synonyms=["ft4", "free t4", "thyroxine free"],
        supported_units=["ng/dl", "pmol/l"],
        comparability_notes="Compare with identical assay types.",
    ),
    "alt_sgpt": ParameterDefinition(
        parameter_code="alt_sgpt",
        canonical_name="ALT (SGPT)",
        category="Hepatic / Liver",
        synonyms=["alt", "sgpt", "alanine aminotransferase", "alanine transaminase"],
        supported_units=["u/l", "iu/l"],
        comparability_notes="Enzymatic activity at 37°C.",
    ),
    "ast_sgot": ParameterDefinition(
        parameter_code="ast_sgot",
        canonical_name="AST (SGOT)",
        category="Hepatic / Liver",
        synonyms=["ast", "sgot", "aspartate aminotransferase", "aspartate transaminase"],
        supported_units=["u/l", "iu/l"],
        comparability_notes="Enzymatic activity at 37°C.",
    ),
    "bilirubin_total": ParameterDefinition(
        parameter_code="bilirubin_total",
        canonical_name="Total Bilirubin",
        category="Hepatic / Liver",
        synonyms=["total bilirubin", "bilirubin total", "t. bilirubin", "serum bilirubin"],
        supported_units=["mg/dl", "umol/l"],
        comparability_notes="Protect sample from light.",
    ),
    "vitamin_d": ParameterDefinition(
        parameter_code="vitamin_d",
        canonical_name="Vitamin D (25-OH)",
        category="Vitamins & Minerals",
        synonyms=["vitamin d", "25-oh vitamin d", "vit d3", "25-hydroxy vitamin d", "total vitamin d"],
        supported_units=["ng/ml", "nmol/l"],
        comparability_notes="Check 25-OH total vs D3.",
    ),
    "vitamin_b12": ParameterDefinition(
        parameter_code="vitamin_b12",
        canonical_name="Vitamin B12",
        category="Vitamins & Minerals",
        synonyms=["vitamin b12", "b12", "cyanocobalamin", "serum b12"],
        supported_units=["pg/ml", "pmol/l"],
        comparability_notes="Fasting sample preferred.",
    ),
}


def map_parameter_name(raw_label: str) -> Optional[ParameterDefinition]:
    """
    Attempt to map a raw test label string to a canonical ParameterDefinition.
    Returns None if no confident mapping is found.
    """
    if not raw_label:
        return None
    cleaned = raw_label.lower().strip()
    # Direct match on parameter_code or canonical_name
    for code, defn in PARAMETER_CATALOG.items():
        if cleaned == code or cleaned == defn.canonical_name.lower():
            return defn
        for synonym in defn.synonyms:
            if cleaned == synonym or cleaned.startswith(synonym + " ") or f"({synonym})" in cleaned:
                return defn
    return None

