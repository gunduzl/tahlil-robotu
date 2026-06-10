"""Kan tahlili referans araligi motoru."""

from __future__ import annotations

import re
from typing import Any

REFERENCE_RANGES: dict[str, dict[str, Any]] = {
    "Hemoglobin": {
        "unit": "g/dL",
        "rules": [
            {"gender": "Erkek", "min": 13.5, "max": 17.5, "label": "Yetiskin erkek"},
            {"gender": "Kadin", "min": 12.0, "max": 15.5, "label": "Yetiskin kadin"},
            {"min_age": 0, "max_age": 17, "min": 11.0, "max": 16.0, "label": "Cocuk"},
        ],
    },
    "Ferritin": {
        "unit": "ng/mL",
        "rules": [
            {"gender": "Erkek", "min": 30, "max": 400, "label": "Yetiskin erkek"},
            {"gender": "Kadin", "min": 13, "max": 150, "label": "Yetiskin kadin"},
            {"min_age": 0, "max_age": 17, "min": 7, "max": 140, "label": "Cocuk"},
        ],
    },
    "B12": {
        "unit": "pg/mL",
        "rules": [
            {"min": 200, "max": 900, "label": "Genel referans"},
        ],
    },
    "D Vitamini": {
        "unit": "ng/mL",
        "rules": [
            {"min": 30, "max": 100, "label": "Genel referans"},
        ],
    },
    "Aclik Kan Sekeri": {
        "unit": "mg/dL",
        "rules": [
            {"min": 70, "max": 99, "label": "Genel referans"},
        ],
    },
    "Toplam Kolesterol": {
        "unit": "mg/dL",
        "rules": [
            {"min": 0, "max": 200, "label": "Genel referans"},
        ],
    },
}

TEST_NAME_ALIASES = {
    "Glukoz (Açlık Kan Şekeri)": "Aclik Kan Sekeri",
    "Glukoz (Aclik Kan Sekeri)": "Aclik Kan Sekeri",
    "Kolesterol": "Toplam Kolesterol",
    "Vitamin B12": "B12",
}


def get_available_tests() -> list[str]:
    """Arayuzde secilebilecek testleri listeler."""
    return sorted(REFERENCE_RANGES.keys())


def normalize_test_name(test_name: str) -> str:
    """Dokumanlarda gecen farkli test isimlerini standartlastirir."""
    cleaned = " ".join((test_name or "").replace("\n", " ").split())
    return TEST_NAME_ALIASES.get(cleaned, cleaned)


def get_test_unit(test_name: str) -> str:
    """Testin beklenen birimini dondurur."""
    normalized_name = normalize_test_name(test_name)
    return REFERENCE_RANGES.get(normalized_name, {}).get("unit", "")


def resolve_reference_rule(test_name: str, age: int, gender: str) -> dict[str, Any]:
    """Yasa ve cinsiyete gore uygun referans kuralini bulur."""
    normalized_name = normalize_test_name(test_name)
    test_config = REFERENCE_RANGES.get(normalized_name)
    if not test_config:
        raise ValueError(f"'{normalized_name}' icin referans araligi tanimli degil.")

    rules = test_config.get("rules", [])
    matching_rules = []
    fallback_rules = []

    for rule in rules:
        age_ok = (
            ("min_age" not in rule or age >= rule["min_age"])
            and ("max_age" not in rule or age <= rule["max_age"])
        )
        if not age_ok:
            continue

        if "gender" in rule:
            if rule["gender"].lower() == gender.lower():
                matching_rules.append(rule)
        else:
            fallback_rules.append(rule)

    if matching_rules:
        return matching_rules[0]
    if fallback_rules:
        return fallback_rules[0]
    if rules:
        return rules[0]

        raise ValueError(f"'{normalized_name}' icin uygun referans kurali bulunamadi.")


def format_reference_text(rule: dict[str, Any], unit: str) -> str:
    """Referans araligini insanlarin okuyabilecegi bicimde hazirlar."""
    return f"{rule['min']} - {rule['max']} {unit}".strip()


def evaluate_result(test_name: str, value: float, age: int, gender: str) -> dict[str, Any]:
    """Test sonucunu referans araligina gore degerlendirir."""
    normalized_name = normalize_test_name(test_name)
    rule = resolve_reference_rule(normalized_name, age=age, gender=gender)
    unit = get_test_unit(normalized_name)
    reference_text = format_reference_text(rule, unit)

    if value < rule["min"]:
        status = "Dusuk"
    elif value > rule["max"]:
        status = "Yuksek"
    else:
        status = "Normal"

    return {
        "test_name": normalized_name,
        "value": value,
        "unit": unit,
        "status": status,
        "reference_text": reference_text,
        "reference_rule": rule,
        "is_out_of_range": status != "Normal",
    }


def evaluate_against_reference_text(value: float, reference_text: str) -> str:
    """Belge ustundeki referans metnine gore sonuc durumunu hesaplar."""
    cleaned = " ".join((reference_text or "").replace("\n", " ").split())
    if not cleaned:
        return "Bilinmiyor"

    between_match = re.search(r"(-?\d+(?:[.,]\d+)?)\s*-\s*(-?\d+(?:[.,]\d+)?)", cleaned)
    if between_match:
        min_value = float(between_match.group(1).replace(",", "."))
        max_value = float(between_match.group(2).replace(",", "."))
        if value < min_value:
            return "Dusuk"
        if value > max_value:
            return "Yuksek"
        return "Normal"

    greater_match = re.search(r">\s*(-?\d+(?:[.,]\d+)?)", cleaned)
    if greater_match:
        threshold = float(greater_match.group(1).replace(",", "."))
        if "Karar" in cleaned or "risk" in cleaned.lower():
            return "Yuksek" if value > threshold else "Normal"
        return "Dusuk" if value <= threshold else "Normal"

    less_match = re.search(r"<\s*(-?\d+(?:[.,]\d+)?)", cleaned)
    if less_match:
        threshold = float(less_match.group(1).replace(",", "."))
        if "Karar" in cleaned or "risk" in cleaned.lower():
            return "Dusuk" if value < threshold else "Normal"
        return "Yuksek" if value >= threshold else "Normal"

    return "Bilinmiyor"
