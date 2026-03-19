import argparse

from agent import run_agent
from config import load_settings
from jira_client import JiraClient
from memory import AgentMemory
from roam_client import RoamClient


def run(dry_run: bool) -> int:
    settings = load_settings()
    memory = AgentMemory(settings.agent_state_path)
    memory_state = memory.load()

    jira = JiraClient(
        base_url=settings.jira_base_url,
        email=settings.jira_email,
        api_token=settings.jira_api_token,
        cloud_id=settings.jira_cloud_id,
        section_field=settings.jira_section_field,
        criticality_field=settings.jira_criticality_field,
        environment_field=settings.jira_environment_field,
        type_field=settings.jira_type_field,
    )
    roam = RoamClient(api_token=settings.roam_api_token)

    board_context = None
    try:
        board_context = jira.get_board_context(settings.jira_board_id)
    except Exception as exc:
        print(f"[WARN] No se pudo obtener contexto del board: {exc}")

    tickets = jira.search_tickets(
        jql=settings.jira_jql,
        max_results=settings.jira_max_results,
    )
    if not tickets:
        print("No se encontraron tickets.")
        return 0

    finalized_tickets = []
    if settings.roam_cpo_channel_id and settings.llm_webhook_url:
        try:
            base_jql = settings.jira_jql.split(" ORDER BY")[0]
            finalized_tickets = jira.search_finalized_tickets(
                base_jql=base_jql,
                lookback_days=settings.recurrence_lookback_days,
            )
        except Exception as exc:
            print(f"[WARN] No se pudieron traer tickets finalizados: {exc}")

    plans, outbound_messages, cpo_body, next_memory = run_agent(
        settings=settings,
        tickets=tickets,
        finalized_tickets=finalized_tickets,
        board_context=board_context,
        memory_state=memory_state,
    )

    sent = 0
    skipped = 0
    if not outbound_messages:
        print("Sin cambios relevantes para comunicar en esta corrida.")
        if not dry_run:
            memory.save(next_memory)
        return 0

    for vertical, title, body in outbound_messages:
        plan = plans[vertical]
        channel_url = settings.roam_channel_urls.get(vertical, "")
        channel_id = settings.roam_channel_ids.get(vertical, "")

        if dry_run:
            print("=" * 80)
            print(f"Plan para vertical '{vertical}': {[action.action_type for action in plan.actions]}")
            if channel_id:
                print(f"Canal Roam ID: {channel_id}")
            elif channel_url:
                print(f"Canal Roam URL: {channel_url}")
            print(body)
            sent += 1
            continue

        # Prioridad: channel ID (API real) > webhook URL (fallback)
        if channel_id and settings.roam_api_token:
            full_message = f"**{title}**\n\n{body}"
            roam.post_message(chat_id=channel_id, text=full_message)
            print(f"[OK] Vertical '{vertical}' enviada a canal {channel_id}.")
            sent += 1
            continue

        webhook = settings.vertical_webhooks.get(vertical) or channel_url or settings.default_roam_webhook
        if not webhook:
            print(f"[SKIP] Vertical '{vertical}' sin canal configurado.")
            skipped += 1
            continue

        roam.post_update(webhook_url=webhook, title=title, body=body)
        print(f"[OK] Vertical '{vertical}' enviada via webhook.")
        sent += 1

    cpo_channel_id = settings.roam_cpo_channel_id
    if cpo_channel_id and cpo_body:
        if dry_run:
            print("=" * 80)
            print(f"[CPO] Canal: {cpo_channel_id}")
            print(cpo_body)
        else:
            roam.post_message(chat_id=cpo_channel_id, text=cpo_body)
            print(f"[OK] Análisis CPO enviado a canal {cpo_channel_id}.")

    if not dry_run:
        memory.save(next_memory)
    print(f"Finalizado. Enviadas: {sent}, Saltadas: {skipped}.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jira vertical updates a Roam")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el mensaje final por vertical sin enviar a Roam",
    )
    parser.add_argument(
        "--list-roam-chats",
        action="store_true",
        help="Lista los chats accesibles en Roam y sus IDs",
    )
    args = parser.parse_args()

    if args.list_roam_chats:
        settings = load_settings()
        roam = RoamClient(api_token=settings.roam_api_token)
        chats = roam.list_chats()
        print(f"{'ID':<50} {'Tipo':<10} Nombre")
        print("-" * 90)
        for chat in sorted(chats, key=lambda c: c.get("name") or ""):
            cid = chat.get("id") or chat.get("chatId") or ""
            ctype = cid[:1] + "-" if cid else "?"
            name = chat.get("name") or "(sin nombre)"
            print(f"{cid:<50} {ctype:<10} {name}")
        raise SystemExit(0)

    raise SystemExit(run(dry_run=args.dry_run))
