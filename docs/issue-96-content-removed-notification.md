# Notificação de conteúdo removido — US 42 / issue #96

## Contrato

`POST /api/v1/admin/recordas/{recorda_id}/removal` exige `reason`. Na mesma
transação da remoção física, da resolução das denúncias e da auditoria, o
backend cria um aviso `CONTENT_REMOVED` para o autor da Recorda.

`GET /api/v1/notifications` devolve o aviso com `sender: null`,
`recorda_id: null`, `removal_reason` e `recorda_song_title`. Os dois campos
ficam nulos nos outros tipos. Nenhum dado do administrador é exposto.

## Modelo

A Recorda removida é apagada fisicamente, então o aviso não pode depender de
`recorda_id`. A coluna `notification.moderation_action_id` (migration
`0013_notification_moderation_action`) aponta para a ação `REMOVE_RECORDA`,
que é imutável:

- `removal_reason` vem de `moderation_action.reason`;
- `recorda_song_title` vem de `moderation_action.details.song_title`,
  gravado no momento da remoção.

## Regras

- Exatamente um aviso por remoção bem-sucedida; repetir a remoção retorna
  `409` e não cria outro aviso.
- Se a criação do aviso falhar, a remoção, a auditoria e a resolução das
  denúncias são revertidas juntas.
- Autores suspensos ou excluídos não recebem o aviso, pois perdem o acesso à
  plataforma e não há serviço de e-mail (D-03).
- A exclusão pelo próprio autor (`DELETE /api/v1/recordas/{id}`) não gera aviso.

## Validação

`tests/test_content_removed_notification.py` cobre o fluxo pelo endpoint real,
privacidade do administrador, repetição, autor suspenso, rollback, paginação,
leitura e isolamento entre autores. `tests/test_content_removed_migration.py`
executa upgrade e downgrade em PostgreSQL real.
