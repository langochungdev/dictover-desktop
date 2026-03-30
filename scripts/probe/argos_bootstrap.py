from __future__ import annotations

from typing import Any


def install_required_argos_pairs(
    required_pairs: list[tuple[str, str]], installed_pairs: set[tuple[str, str]]
) -> dict[str, Any]:
    report = {
        "attempted": 0,
        "installed": [],
        "missing_in_index": [],
        "install_errors": [],
        "error": None,
    }
    try:
        import argostranslate.package as apkg
    except Exception as exc:
        report["error"] = str(exc)
        return report

    try:
        apkg.update_package_index()
        available = apkg.get_available_packages()
    except Exception as exc:
        report["error"] = str(exc)
        return report

    by_pair: dict[tuple[str, str], Any] = {}
    for pkg in available:
        pair = (pkg.from_code, pkg.to_code)
        if pair not in by_pair:
            by_pair[pair] = pkg

    for pair in required_pairs:
        if pair in installed_pairs:
            continue
        report["attempted"] += 1
        pkg = by_pair.get(pair)
        if not pkg:
            report["missing_in_index"].append({"source": pair[0], "target": pair[1]})
            continue
        try:
            path = pkg.download()
            apkg.install_from_path(path)
            report["installed"].append({"source": pair[0], "target": pair[1]})
        except Exception as exc:
            report["install_errors"].append(
                {"source": pair[0], "target": pair[1], "error": str(exc)}
            )
    return report
