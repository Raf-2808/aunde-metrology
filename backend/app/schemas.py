"""Kontrakty API walidowane niezależnie od interfejsu przeglądarki."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from datetime import date
from .domain import liczba


class Credentials(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class Reauth(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    scope: Literal["real", "simulated", "spc"]


class UserInput(Credentials):
    role: Literal["admin", "manager", "technician", "reporter", "reader"]


class UserUpdate(BaseModel):
    role: Literal["admin", "manager", "technician", "reporter", "reader"]
    active: bool
    password: str | None = Field(default=None, min_length=12, max_length=256)


class MethodInput(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=250)


class Spec(BaseModel):
    key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=200)
    method_id: int
    unit: str = Field(default="", max_length=40)
    kind: Literal["numeric", "qualitative"] = "numeric"
    count: int = Field(ge=1, le=10)
    labels: list[str] = Field(min_length=1, max_length=10)
    lsl: str | None = None
    usl: str | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    decimals: int = Field(default=2, ge=0, le=10)
    frequency: Literal["every", "nth", "extra"] = "every"
    every_n: int = Field(default=1, ge=1, le=10000)
    allowed: list[str] = Field(default_factory=list, max_length=100)
    passing: list[str] = Field(default_factory=list, max_length=100)
    simulation_offset: str | None = None

    @model_validator(mode="after")
    def sprawdz(self):
        """Zapewnia spójność liczby punktów, tolerancji i katalogu ocen."""
        if len(self.labels) != self.count or len(set(self.labels)) != self.count:
            raise ValueError("Wymagane unikalne etykiety każdego pomiaru")
        if self.kind == "numeric":
            if self.lsl is None and self.usl is None:
                raise ValueError("Wymagana granica specyfikacji")
            for x in (self.lsl, self.usl, self.simulation_offset):
                if x is not None:
                    liczba(x)
            if (
                self.lsl is not None
                and self.usl is not None
                and liczba(self.lsl) >= liczba(self.usl)
            ):
                raise ValueError("LSL musi być mniejsze od USL")
            if (
                self.simulation_offset is not None
                and liczba(self.simulation_offset) <= 0
            ):
                raise ValueError("Korekta musi być dodatnia")
        elif (
            not self.allowed
            or not self.passing
            or not set(self.passing) <= set(self.allowed)
        ):
            raise ValueError("Wymagany katalog i zbiór ocen zgodnych")
        return self


class ArticleInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    specs: list[Spec] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unikalne(self):
        """Nie pozwala ukryć charakterystyki przez powielenie klucza."""
        if len(set(x.key for x in self.specs)) != len(self.specs):
            raise ValueError("Powtórzony klucz charakterystyki")
        return self


class OrderInput(BaseModel):
    article_id: int
    lot: str = Field(min_length=1, max_length=120)
    roll: str = Field(default="", max_length=120)
    quantity: str = Field(default="", max_length=80)
    required_sessions: int = Field(default=1, ge=1, le=100)
    extra: list[str] = Field(default_factory=list, max_length=100)


class SaveInput(BaseModel):
    order_id: int
    cycle: int = Field(ge=1)
    config_id: int
    test_date: date
    values: dict[str, list[str | None]]
    acknowledged: bool = False
    delivery_note: str = Field(default="", max_length=120)
    production_level: str = Field(default="", max_length=120)
    device: str = Field(default="", max_length=250)
    started_on: date | None = None
    ended_on: date | None = None
    notes: str = Field(default="", max_length=4000)
    correction_of: int | None = None
    reason: str = Field(default="", max_length=2000)


class DispositionInput(BaseModel):
    held: bool
    reason: str = Field(min_length=3, max_length=2000)


class SpcInput(BaseModel):
    characteristic_id: int
    sampling_plan: str = Field(min_length=10, max_length=2000)
    n: int = Field(ge=1, le=10)
    cl: float
    lcl: float
    ucl: float
    rcl: float = Field(ge=0)
    rlcl: float = Field(ge=0)
    rucl: float = Field(ge=0)
    run_length: int = Field(default=8, ge=0, le=20)

    @model_validator(mode="after")
    def granice(self):
        """Odrzuca odwrócone i nieskończone granice kontrolne."""
        import math

        if (
            not all(
                math.isfinite(x)
                for x in (self.cl, self.lcl, self.ucl, self.rcl, self.rlcl, self.rucl)
            )
            or not self.lcl <= self.cl <= self.ucl
            or not self.rlcl <= self.rcl <= self.rucl
        ):
            raise ValueError("Nieprawidłowe granice kontrolne")
        return self


class RuleInput(BaseModel):
    characteristic_id: int
    email: str = Field(
        pattern=r"^[^\s@,;\r\n]+@[^\s@,;\r\n]+\.[^\s@,;\r\n]+$", max_length=254
    )
    events: list[Literal["UCL", "LCL", "R_UCL", "R_LCL", "SPECIFICATION", "RUN"]] = (
        Field(min_length=1)
    )
    enabled: bool = False
