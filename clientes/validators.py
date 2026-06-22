import re

from django.core.exceptions import ValidationError


def somente_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def cpf_valido(valor):
    cpf = somente_digitos(valor)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False

    for tamanho in (9, 10):
        soma = sum(int(cpf[indice]) * (tamanho + 1 - indice) for indice in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[tamanho]):
            return False
    return True


def cnpj_valido(valor):
    cnpj = somente_digitos(valor)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    pesos_primeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_segundo = [6] + pesos_primeiro

    def calcular_digito(digitos, pesos):
        soma = sum(int(digito) * peso for digito, peso in zip(digitos, pesos))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    primeiro = calcular_digito(cnpj[:12], pesos_primeiro)
    segundo = calcular_digito(cnpj[:12] + primeiro, pesos_segundo)
    return cnpj[-2:] == primeiro + segundo


def validar_cpf_ou_cnpj(valor, tipo_pessoa=None):
    documento = somente_digitos(valor)
    if tipo_pessoa == 'fisica' or len(documento) == 11:
        if cpf_valido(documento):
            return
        raise ValidationError('Informe um CPF valido.')

    if tipo_pessoa == 'juridica' or len(documento) == 14:
        if cnpj_valido(documento):
            return
        raise ValidationError('Informe um CNPJ valido.')

    raise ValidationError('Informe um CPF com 11 digitos ou CNPJ com 14 digitos.')
