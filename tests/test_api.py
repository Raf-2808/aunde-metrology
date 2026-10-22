from fastapi.testclient import TestClient
from argon2 import PasswordHasher
from backend.api import aplikacja
from backend.baza import pobierz_baze
from backend.modele import Uzytkownik


# Sprawdza logowanie, wymaganie CSRF, role i wylogowanie na izolowanej bazie testowej.
def test_sesji_i_csrf(baza):
    baza.add(
        Uzytkownik(
            login="admin-test",
            skrot_hasla=PasswordHasher().hash("testowe-haslo-123"),
            rola="Administrator",
        )
    )
    baza.commit()

    # Udostępnia wyłącznie testową sesję jako zależność API.
    def testowa_baza():
        try:
            yield baza
        finally:
            baza.rollback()

    aplikacja.dependency_overrides[pobierz_baze] = testowa_baza
    try:
        with TestClient(aplikacja) as klient:
            assert klient.post("/api/przyrzady/szukaj", json={}).status_code == 401
            odp = klient.post(
                "/api/logowanie",
                json={"login": "admin-test", "haslo": "testowe-haslo-123"},
            )
            assert odp.status_code == 200
            assert "httponly" in odp.headers["set-cookie"].lower()
            assert (
                klient.post(
                    "/api/przyrzady",
                    json={"numer": "X", "typ": "Miara", "wydzial": "ESD"},
                ).status_code
                == 403
            )
            klient.headers["X-CSRF-Token"] = odp.json()["csrf"]
            assert (
                klient.post(
                    "/api/przyrzady",
                    json={"numer": "X", "typ": "Miara", "wydzial": "ESD"},
                ).status_code
                == 200
            )
            wynik = klient.post("/api/przyrzady/szukaj", json={})
            assert wynik.json()["liczba"] == 1
            konta = klient.get("/api/uzytkownicy").json()
            admin_id = konta[0]["id"]
            assert "skrot_hasla" not in konta[0]
            assert (
                klient.patch("/api/uzytkownicy/" + admin_id, json={"aktywny": False}).status_code
                == 422
            )
            nowy = klient.post(
                "/api/uzytkownicy",
                json={
                    "login": "viewer-test",
                    "haslo": "haslo-testowe-456",
                    "rola": "Viewer",
                },
            )
            assert nowy.status_code == 200
            assert (
                klient.patch(
                    "/api/uzytkownicy/" + nowy.json()["id"], json={"aktywny": False}
                ).status_code
                == 200
            )
            assert klient.post("/api/wylogowanie").status_code == 200
            assert klient.get("/api/sesja").status_code == 401
    finally:
        aplikacja.dependency_overrides.clear()
