from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def pesos(valor):
    if valor is None or valor == "":
        return ""
    numero = Decimal(valor)
    texto = f"{abs(numero):,.0f}".replace(",", ".")
    if numero < 0:
        return f"-${texto}"
    return f"${texto}"


@register.filter
def cantidad(valor):
    if valor is None or valor == "":
        return ""
    texto = f"{Decimal(valor):,.3f}"
    texto = texto.rstrip("0").rstrip(".")
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")
