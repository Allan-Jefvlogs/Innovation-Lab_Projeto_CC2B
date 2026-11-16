function "Inventory/record_audit_event" {
  description = "Registra evento de auditoria sem aceitar segredos nos dados de alteração. Deve ser chamado somente por operações autenticadas após validação de sucesso."
  input {
    int actor_user_id
    text action_type
    text entity_type
    int? entity_id?
    text summary
    json? changes?
  }
  stack {
    db.get user {
      field_name = "id"
      field_value = $input.actor_user_id
      output = ["id", "name"]
    } as $actor

    precondition ($actor != null) {
      error_type = "accessdenied"
      error = "AUDIT_ACTOR_NOT_FOUND"
    }

    db.add inventory_audit_log {
      data = {
        actor_user_id: $actor.id,
        actor_name: $actor.name,
        action_type: $input.action_type,
        entity_type: $input.entity_type,
        entity_id: $input.entity_id,
        summary: $input.summary,
        changes: $input.changes
      }
    } as $event
  }
  response = {id: $event.id, occurred_at: $event.occurred_at}
}
