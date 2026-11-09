"""Cadastro e edição sem excluir produtores nem alterar suas chaves internas."""
import re

CERTIFICACOES = ["OCS", "OPAC", "CERTIFICADORA", "AGRICULTURA_FAMILIAR"]
SITUACOES = ["ATIVO", "INATIVO", "SUSPENSO"]
UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
CAMPOS = (
    "nome_produtor", "cpf_cnpj", "tipo_certificacao", "entidade_certificadora",
    "escopo_producao", "cidade", "uf", "contato", "situacao",
)


def normalizar_documento(documento):
    return re.sub(r"[^0-9]", "", str(documento or ""))


def buscar_produtores(conectar, documento, por_codigo=False):
    if por_codigo:
        codigo = str(documento or "").strip()
        if not re.fullmatch(r"[0-9]+", codigo) or int(codigo) <= 0:
            raise ValueError("Informe um código de produtor válido, como o exibido na tabela.")
    else:
        chave = normalizar_documento(documento)
        if not chave:
            raise ValueError("Informe o CPF ou CNPJ para buscar.")
    conn = conectar("db_feira_online")
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            if por_codigo:
                cursor.execute("SELECT * FROM tb_produtor WHERE id_produtor = %s", (int(codigo),))
                return cursor.fetchall()
            cursor.execute("SELECT * FROM tb_produtor ORDER BY id_produtor")
            return [r for r in cursor.fetchall() if normalizar_documento(r["cpf_cnpj"]) == chave]
        finally:
            cursor.close()
    finally:
        conn.close()


def validar_dados(dados, original=None):
    valores = {campo: str(dados.get(campo) or "").strip() for campo in CAMPOS}
    doc = valores["cpf_cnpj"]
    chave = normalizar_documento(doc)
    # Permite corrigir outros dados de cadastros legados com documento incompleto.
    documento_inalterado = original is not None and doc == original["cpf_cnpj"]
    if not documento_inalterado:
        if re.search(r"[^0-9. /-]", doc) or len(chave) not in (11, 14):
            raise ValueError("Informe um CPF com 11 dígitos ou CNPJ com 14 dígitos.")
        valores["cpf_cnpj"] = chave
    for campo, rotulo in (("nome_produtor", "Nome"), ("cidade", "Município"), ("escopo_producao", "Escopo de produção")):
        if not valores[campo]:
            raise ValueError(f"{rotulo} é obrigatório.")
    valores["uf"] = valores["uf"].upper()
    valores["cidade"] = valores["cidade"].upper()
    if valores["uf"] not in UFS:
        raise ValueError("Informe uma UF válida.")
    if valores["tipo_certificacao"] not in CERTIFICACOES:
        raise ValueError("Selecione a modalidade de certificação.")
    if valores["situacao"] not in SITUACOES:
        raise ValueError("Selecione uma situação válida.")
    limites = {"nome_produtor": 150, "cpf_cnpj": 20, "entidade_certificadora": 200,
               "escopo_producao": 150, "cidade": 100, "contato": 120}
    for campo, limite in limites.items():
        if len(valores[campo]) > limite:
            raise ValueError(f"O campo {campo} aceita até {limite} caracteres.")
    for campo in ("entidade_certificadora", "contato"):
        valores[campo] = valores[campo] or None
    return valores


def salvar_produtor(conectar, dados, original=None):
    """Serializa gravações da aplicação e verifica CPF sem máscara antes de salvar."""
    valores = validar_dados(dados, original)
    conn = conectar("db_feira_online")
    cursor = None
    bloqueado = False
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT GET_LOCK('db_feira_online.produtores', 10) AS adquirido")
        bloqueado = cursor.fetchone()["adquirido"] == 1
        if not bloqueado:
            raise ValueError("Outro cadastro está sendo salvo. Tente novamente.")
        cursor.execute("SELECT * FROM tb_produtor ORDER BY id_produtor FOR UPDATE")
        registros = cursor.fetchall()
        id_atual = int(original["id_produtor"]) if original is not None else None
        if original is not None:
            atual = next((r for r in registros if r["id_produtor"] == id_atual), None)
            if atual is None or any(atual[c] != original[c] for c in CAMPOS):
                raise ValueError("O cadastro foi alterado em outra sessão. Busque novamente antes de salvar.")
        chave = normalizar_documento(valores["cpf_cnpj"])
        duplicados = [r for r in registros if r["id_produtor"] != id_atual
                      and normalizar_documento(r["cpf_cnpj"]) == chave]
        if duplicados and (original is None or chave != normalizar_documento(original["cpf_cnpj"])):
            raise ValueError("CPF/CNPJ já cadastrado. Use a busca para editar o produtor existente.")
        params = tuple(valores[c] for c in CAMPOS)
        if original is None:
            cursor.execute(
                "INSERT INTO tb_produtor (" + ", ".join(CAMPOS) + ") VALUES (" + ", ".join(["%s"] * len(CAMPOS)) + ")",
                params,
            )
        else:
            cursor.execute(
                "UPDATE tb_produtor SET " + ", ".join(c + " = %s" for c in CAMPOS) + " WHERE id_produtor = %s",
                params + (id_atual,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                try:
                    if bloqueado:
                        cursor.execute("SELECT RELEASE_LOCK('db_feira_online.produtores') AS liberado")
                        cursor.fetchone()
                finally:
                    cursor.close()
        finally:
            conn.close()
