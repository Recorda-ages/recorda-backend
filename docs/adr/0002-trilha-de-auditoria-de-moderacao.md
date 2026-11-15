# Trilha de auditoria de moderação

A tabela `moderation_action` registra as ações administrativas de moderação: quem agiu, qual ação, sobre qual alvo, quando e por qual motivo. Ela foi criada na issue #83, antes da US47 que a motiva, porque a US47 é classificada como *Could* mas suas estruturas são pré-requisito das US44, US45 e US46: é em `moderation_action.reason` que vive o motivo obrigatório de toda ação administrativa (D-02).

A decisão reverte o que o modelo de dados v3.0 havia fechado. A decisão **D55** e a linha *Moderação* da Parte 7 colocavam `MODERATION_ACTION` (auditoria) explicitamente fora do MVP, e a regra escrita na tabela `report` afirmava não existir tabela de auditoria. Essas três afirmações deixam de valer.

## Decisões de modelagem

- **Append-only.** Uma ação registrada nunca é alterada nem apagada. A tabela não tem `updated_at` nem `deleted_at`, e o repository expõe apenas inserção e leitura — não há `save`, `update` nem `delete`.
- **Imutabilidade imposta no banco, não por convenção.** A migration `0008_moderation_action` cria a função `moderation_action_immutable()` e o trigger `trg_moderation_action_immutable`, `BEFORE UPDATE OR DELETE ... FOR EACH ROW`, que levanta a exceção `moderation_action é imutável`. Uma trilha que o próprio código pode reescrever não é auditoria; a garantia tem de estar abaixo da aplicação.
- **O trigger é específico do PostgreSQL.** O SQLite da suíte de testes não tem equivalente e não recebe imitação artificial. A imutabilidade é testada contra PostgreSQL real, numa fixture opt-in.
- **Quatro `action_type`**, em `VARCHAR` + `CHECK` (D67): `REMOVE_RECORDA`, `CHANGE_REPORT_STATUS`, `SUSPEND_USER`, `REACTIVATE_USER`. O vocabulário é fechado; tipos novos exigem decisão nova.
- **Dois alvos possíveis, `target_user_id` e `target_recorda_id`**, com `CHECK (target_user_id IS NOT NULL OR target_recorda_id IS NOT NULL)` — pelo menos um, não exatamente um. É uma diferença deliberada em relação a `ck_report_single_target`, que exige exatamente um.
- **`REMOVE_RECORDA` preenche os dois alvos:** `target_recorda_id` com a Recorda e `target_user_id` com o autor dela. Assim o histórico administrativo de uma conta sai de uma consulta direta a `target_user_id`, sem join com `recorda` — é o que a US46 precisa.
- **`reason` é `TEXT NOT NULL`** (D-02). O limite de 500 caracteres é validado na aplicação (D-04), não no banco — coerente com a Parte 7 do modelo, que mantém limites de texto fora do schema. O service normaliza com `strip()` antes de validar e de persistir, e o limite vale para o texto já normalizado.
- **`details` é `JSON` nullable e livre**, para contexto da decisão — por exemplo `{"from":"OPEN","to":"DISMISSED","report_count":3,"target_type":"RECORDA"}`. Não há schema por `action_type` nem validação de estrutura. É `JSON`, não `JSONB`: não há requisito de indexar o conteúdo.
- **FKs sem `ondelete`.** `admin_id`, `target_user_id` e `target_recorda_id` ficam em `NO ACTION`: o hard delete do registro referenciado é bloqueado e nenhuma linha da trilha é apagada em cascata. É a mesma semântica adotada em `report`.
- **Quatro índices**, nomeados pela convenção `ix_<tabela>_<colunas>`: `ix_moderation_action_created_at` (`created_at DESC`), `ix_moderation_action_admin_id_created_at` (`admin_id`, `created_at DESC`), `ix_moderation_action_target_user_id` e `ix_moderation_action_target_recorda_id`. Os dois últimos deixam o banco pronto para as consultas das US45 e US46.
- **Fronteira transacional.** `moderation_service.record_action` e `moderation_action_repository.add` não fazem commit: o `add` faz `flush`, para popular `action_id` e disparar as constraints ainda dentro da transação. O commit é do service da operação auditada, de modo que a mudança de estado e o registro caem na mesma transação. Não existe estado alterado sem auditoria, nem auditoria de algo que não aconteceu.

## Ausências deliberadas

- **Sem `report_id`.** A trilha tem como alvo o usuário e a Recorda, e não referencia a denúncia que motivou a ação.
- **Sem `comment_id`.** Não há alvo de comentário, porque não há rota de denúncia de comentário no MVP.
- **Sem `reason_code` nem `reason_note`.** O motivo é um único campo de texto livre.
- **Sem `report.resolved_by_id`.** O autor de uma resolução de denúncia é lido da trilha, não denormalizado em `report`.

## Decisões anteriores supersedidas ou qualificadas

- **D55 — "Sem `MODERATION_ACTION`" — supersedida.** É a reversão central desta decisão.
- **Parte 7, linha Moderação, item `MODERATION_ACTION` (auditoria) — supersedido.** Os outros itens da linha (papel `MODERATOR`, status `UNDER_REVIEW`, motivos estruturados de denúncia) continuam fora do MVP.
- **D71 e o princípio de soft delete universal — qualificados, não revertidos.** A regra vale para conteúdo: conta, Recorda, comentário. `moderation_action` é exceção explícita, por ser append-only e imutável.
- **D56 — qualificada.** A moderação continua removendo conteúdo pelo mesmo `deleted_at`; o mecanismo não muda. Passa a ser acompanhado do registro em `moderation_action`, na mesma transação.
- **D51 — intacta.** `report` continua sem motivo estruturado, com `description` livre e opcional. O `reason` desta tabela é o motivo da **decisão do moderador**, não o motivo alegado pelo denunciante. São conceitos distintos e não se substituem.
- **Parte 7, papel `MODERATOR` — intacto.** `app_user.role = 'ADMIN'` atende as US44 a US47.
- **ADR 0001 — nada supersedido.** Esta decisão é aditiva.

## Consequências

- A Parte 2 do modelo de dados passa de 13 para 14 tabelas. A migration `0008_moderation_action` é aditiva: não altera nenhuma estrutura existente.
- O trigger de imutabilidade bloqueia DML, não DDL — o `downgrade` da migration derruba trigger, função, índices e tabela normalmente, mesmo com linhas registradas.
- Toda rota administrativa das US44/45/46 passa a precisar de um motivo para agir, e a gravar a auditoria no mesmo commit da operação. Quem não registrar a ação não consegue mais justificar a mudança de estado.
- Como a imutabilidade vive em trigger do PostgreSQL, os testes que a cobrem só rodam contra PostgreSQL real e ficam fora da suíte padrão do CI, que usa SQLite. A fixture correspondente é opt-in e recria o schema, por isso exige confirmação explícita para rodar.
- O contrato de saída `AuditEntry` (C-2) não foi localizado no repositório e ficou em aberto nesta decisão. Ele foi definido na issue #91 (`GET /admin/audit-log`), em `app/schemas/moderation.py`, a partir do que a tela de auditoria do front consome: `action_id`, `action_type`, `admin {user_id, username}`, `target_user_id`, `target_recorda_id`, `target_label`, `reason`, `details` e `created_at`. O `target_label` continua sem ser armazenado: é montado na leitura, com o `song_title` da Recorda quando há Recorda alvo (caso de `REMOVE_RECORDA`, que preenche os dois alvos) e o `username` do usuário alvo nos demais casos. A consulta não filtra `deleted_at`, para que admin e alvos excluídos continuem identificados no log.
