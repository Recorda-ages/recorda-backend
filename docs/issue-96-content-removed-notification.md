# Notificação de conteúdo removido — issue #96

## Contrato

`GET /api/v1/notifications` aceita o tipo `CONTENT_REMOVED`. O aviso tem
`sender: null`, `recorda_id`, `removal_reason` e `recorda_song_title`. Os dois
campos novos são opcionais e ficam nulos nos outros tipos. O motivo vem da ação
`REMOVE_RECORDA` mais recente da Recorda, ordenada por `created_at` e `action_id`;
sem ação correspondente, retorna nulo. Nenhum dado do administrador é exposto.

O aviso permanece visível após o soft delete e participa da contagem de não lidas
e da marcação como lido. Os avisos sociais de Recordas removidas continuam ocultos.
A subconsulta escalar do motivo não multiplica os itens nem altera a paginação.

## Transação e integração pendente

`notification_service.notify_content_removed(db, recorda)` adiciona o aviso e faz
`flush`, sem `commit`. O service da remoção administrativa deve chamá-lo depois
do soft delete, na mesma transação da resolução de denúncias e da auditoria. O
commit e o tratamento de rollback pertencem ao service da operação administrativa.

Em 2026-10-08, a `origin/dev` no commit `8c20e88` contém a trilha de auditoria,
mas ainda não contém o endpoint `POST /admin/recordas/{recorda_id}/removal` da
[issue #87](https://github.com/Recorda-ages/recorda-backend/issues/87).
Assim, o disparo pelo endpoint real permanece pendente. A função de notificação
não deduplica chamadas: o fluxo da #87 deve recusar uma Recorda já removida antes
de criar o aviso, inclusive protegendo a operação de remoções concorrentes.

Para concluir a #96 depois da integração da #87:

- Conectar a chamada na transação administrativa e testar o endpoint real.
- Verificar exatamente um aviso para uma remoção bem-sucedida e nenhum novo
  aviso ao repetir a remoção ou em uma operação revertida.
- Verificar rollback conjunto quando a criação do aviso ou a auditoria falha.

A exclusão pelo próprio autor não chama esse serviço; um teste pelo endpoint
`DELETE /api/v1/recordas/{id}` verifica que nenhuma notificação é criada.
Os testes atuais de rollback exercitam a composição dos serviços no banco;
não substituem a validação do endpoint administrativo ainda ausente.

## Migration

Arquivo: `0009_notification_content_removed.py`, após `0008_moderation_action`.
O ID é `0009_content_removed`, pois o nome completo ultrapassa o `VARCHAR(32)`
de `alembic_version.version_num`. O upgrade substitui `ck_notification_type`.
O downgrade apaga os avisos `CONTENT_REMOVED` antes de restaurar a constraint
anterior; os avisos sociais são preservados. Essa perda dos avisos do tipo novo
é necessária para retornar ao contrato anterior com a constraint restritiva.

## Validação

- `tests/test_content_removed_notification.py`: criação sem commit, rollback
  conjunto, motivo mais recente, privacidade, visibilidade após exclusão,
  campos nulos nos demais tipos, paginação, leitura, isolamento entre autores
  e exclusão pelo autor.
- `tests/test_content_removed_migration.py`: upgrade e downgrade em PostgreSQL
  real, preservação dos avisos sociais, rejeição do tipo novo após downgrade
  e aceitação após novo upgrade; também executa a consulta de notificações.
- A fixture PostgreSQL exige `TEST_DATABASE_URL` apontando a um banco
  descartável com nome `test_*` ou `*_test`, separado do banco da aplicação,
  e `TEST_DATABASE_ALLOW_DESTRUCTIVE=1`.
- Gates do projeto: `pytest --cov=app --cov-report=term-missing`,
  `ruff check .` e `ruff format --check .`, com cobertura mínima de 80%.

Resultado em 2026-10-08, Python 3.13.16 e PostgreSQL 16 descartável:
**614 testes passaram, 2 foram pulados; cobertura de 98,05%; Ruff e formatação
passaram.** Os dois testes pulados parametrizam as rotas administrativas reais,
pois o router ainda não contém endpoints. O container de teste foi removido
após a validação. A integração da #87 continua pendente.
