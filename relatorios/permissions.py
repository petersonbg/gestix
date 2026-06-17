from accounts.models import PerfilUsuario


RELATORIOS_PERMISSOES = {
    'vendas': {
        PerfilUsuario.Perfil.ADMINISTRADOR,
        PerfilUsuario.Perfil.GERENTE,
        PerfilUsuario.Perfil.VENDEDOR,
    },
    'estoque_baixo': {
        PerfilUsuario.Perfil.ADMINISTRADOR,
        PerfilUsuario.Perfil.GERENTE,
        PerfilUsuario.Perfil.ESTOQUISTA,
    },
    'contas_receber': {PerfilUsuario.Perfil.ADMINISTRADOR, PerfilUsuario.Perfil.GERENTE},
    'contas_pagar': {PerfilUsuario.Perfil.ADMINISTRADOR, PerfilUsuario.Perfil.GERENTE},
    'caixa_diario': {PerfilUsuario.Perfil.ADMINISTRADOR, PerfilUsuario.Perfil.GERENTE},
}
