# =============================================================================
# src/schemas/consulta_recarga.py — Schema Pydantic v2 do domínio EV (Aula 03)
# =============================================================================
#
# Usado pela chain de saída estruturada (src/chain/builder.py ->
# build_structured_chain) para transformar o texto operacional do
# ChargeGrid em um objeto Python tipado e validado, em vez de texto livre.

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class EstacaoStatus(BaseModel):
    """Estado de uma estação de recarga individual (objeto aninhado)."""

    nome: str = Field(description="Identificador da estação, ex.: 'Estação 1'")
    status: Literal["Operacional", "FALHA", "Manutenção"] = Field(
        description="Estado atual da estação"
    )
    modelo: str = Field(description="Modelo do carregador GoodWe, ex.: 'GoodWe HCA G2 22kW'")
    kwh_hoje: float = Field(ge=0, description="Energia entregue por essa estação hoje, em kWh")


class ConsultaRecarga(BaseModel):
    """Resposta estruturada para uma consulta operacional ao ChargeGrid.

    O campo `limite_kw` é definido ANTES de `demanda_kw` de propósito: o
    field_validator de `demanda_kw` lê `limite_kw` via `info.data`, e no
    Pydantic v2 os campos só ficam disponíveis em `info.data` depois de
    terem sido validados — a ordem de declaração importa aqui.
    """

    sessoes_ativas: int = Field(ge=0, description="Número de sessões de recarga ativas agora")
    kwh_hoje: float = Field(ge=0, description="Consumo total de energia hoje, em kWh")
    limite_kw: float = Field(gt=0, description="Limite de demanda contratado, em kW")
    demanda_kw: float = Field(ge=0, description="Demanda de potência atual, em kW")
    tarifa_atual: Literal["pico", "fora_pico"] = Field(
        description="Faixa tarifária vigente no momento da consulta"
    )
    estacoes: List[EstacaoStatus] = Field(description="Situação de cada estação monitorada")
    alerta: Optional[str] = Field(
        None, description="Descrição do alerta ativo mais relevante, se houver"
    )

    @field_validator("demanda_kw")
    @classmethod
    def demanda_dentro_do_plausivel(cls, v: float, info) -> float:
        """Guardrail de sanidade sobre a própria extração: uma demanda maior
        que 3x o limite contratado é sinal de erro de leitura/alucinação do
        modelo, não um dado operacional real — rejeita antes de propagar."""
        limite = info.data.get("limite_kw")
        if limite and v > limite * 3:
            raise ValueError(
                "demanda_kw muito acima de limite_kw — provável erro de "
                "extração do modelo, não um valor operacional real"
            )
        return v
