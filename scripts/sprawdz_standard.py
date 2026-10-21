"""Kontrola komentarzy przed funkcjami i niedozwolonego znaku w tworzonym kodzie."""

import ast
from pathlib import Path


# Sprawdza własny kod Python projektu; zwraca listę braków, nie modyfikuje plików.
def sprawdz_standard(korzen: Path) -> list[str]:
    problemy: list[str] = []
    for folder in ("backend", "database", "scripts", "tests"):
        for plik in (korzen / folder).rglob("*.py"):
            tresc = plik.read_text(encoding="utf-8")
            linie = tresc.splitlines()
            if "\u2014" in tresc:
                problemy.append(f"{plik}: niedozwolony znak U+2014")
            for wezel in ast.walk(ast.parse(tresc)):
                if isinstance(wezel, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    poczatek = min([wezel.lineno] + [d.lineno for d in wezel.decorator_list])
                    nr = poczatek - 2
                    while nr >= 0 and not linie[nr].strip():
                        nr -= 1
                    if nr < 0 or not linie[nr].lstrip().startswith("#"):
                        problemy.append(
                            f"{plik}:{wezel.lineno}: brak polskiego komentarza przed funkcją {wezel.name}"
                        )
    return problemy


if __name__ == "__main__":
    wynik = sprawdz_standard(Path(__file__).resolve().parents[1])
    if wynik:
        raise SystemExit("\n".join(wynik))
    print(
        "Komentarze przed funkcjami i brak U+2014: sprawdzono. Nazwy i treść komentarzy wymagają także przeglądu człowieka."
    )
