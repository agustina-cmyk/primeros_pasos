import argparse
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from agent import run_agent
from config import load_settings
from jira_client import JiraClient
from memory import AgentMemory
from roam_client import RoamClient

_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def run(dry_run: bool, cpo_only: bool = False, roadmap_only: bool = False,
        notify_only: bool = False, force_roadmap: bool = False, weekly: bool = False) -> int:
    settings = load_settings()
    memory = AgentMemory(settings.agent_state_path)
    memory_state = memory.load()

    is_weekly_run = weekly or datetime.now(_ARGENTINA_TZ).weekday() == 4

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

    # Siempre traemos finalizados para que el sync de soporte pueda marcar
    # tickets como cerrados (resolvedAt). El análisis de recurrencia los usa
    # adicionalmente cuando roam_cpo_channel_id + llm_webhook_url están seteados.
    #
    # Importante: los boards de Jira filtran tickets Done por default (solo
    # muestran lo activo). Si `JIRA_BASE_JQL` no está seteado y derivamos a
    # `board = X`, no traemos ningún Done. Si tenemos `project_key` del board
    # context, lo preferimos para que la query alcance al historial completo.
    if settings.jira_base_jql and not settings.jira_base_jql.startswith("board "):
        finalized_base_jql = settings.jira_base_jql
    elif board_context and board_context.project_key:
        finalized_base_jql = f'project = "{board_context.project_key}"'
    else:
        finalized_base_jql = settings.jira_base_jql

    finalized_tickets = []
    try:
        finalized_tickets = jira.search_finalized_tickets(
            base_jql=finalized_base_jql,
            lookback_days=settings.recurrence_lookback_days,
        )
        print(f"[FINALIZED] base_jql='{finalized_base_jql}' lookback={settings.recurrence_lookback_days}d → {len(finalized_tickets)} tickets")
    except Exception as exc:
        print(f"[WARN] No se pudieron traer tickets finalizados: {exc}")

    plans, outbound_messages, cpo_body, next_memory, roadmap_plan, grouped_facts = run_agent(
        settings=settings,
        tickets=tickets,
        finalized_tickets=finalized_tickets,
        board_context=board_context,
        memory_state=memory_state,
        skip_roadmap=notify_only,
        force_roadmap=force_roadmap,
        is_weekly_run=is_weekly_run,
    )

    if not notify_only:
        _sync_support_tickets(settings, grouped_facts, finalized_tickets, memory_state)

    sent = 0
    skipped = 0
    skip_channels = roadmap_only
    if not outbound_messages and not cpo_only and not roadmap_only:
        print("Sin cambios relevantes para comunicar en esta corrida.")
        if not dry_run:
            cpo_channel_id = settings.roam_cpo_channel_id
            if cpo_channel_id and cpo_body:
                roam.post_message(chat_id=cpo_channel_id, text=cpo_body)
                print(f"[OK] Análisis CPO enviado a canal {cpo_channel_id}.")
            if not notify_only and roadmap_plan and roadmap_plan.actions:
                created_ideas = _execute_roadmap_plan(settings, roadmap_plan, next_memory)
                if created_ideas:
                    _notify_cpo_roadmap(settings, roam, created_ideas)
            if is_weekly_run and not roadmap_only:
                next_memory.weekly_last_run_at = datetime.now(timezone.utc).isoformat()
            memory.save(next_memory)
        return 0

    for vertical, title, body in ([] if (cpo_only or skip_channels) else outbound_messages):
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
    if cpo_channel_id and cpo_body and not roadmap_only:
        if dry_run:
            print("=" * 80)
            print(f"[CPO] Canal: {cpo_channel_id}")
            print(cpo_body)
        else:
            roam.post_message(chat_id=cpo_channel_id, text=cpo_body)
            print(f"[OK] Análisis CPO enviado a canal {cpo_channel_id}.")

    if dry_run and not cpo_only:
        if roadmap_plan:
            print("=" * 80)
            print("[ROADMAP DRY-RUN]")
            if roadmap_plan.skip_reason:
                print(f"Sin acciones: {roadmap_plan.skip_reason}")
            else:
                for i, action in enumerate(roadmap_plan.actions, 1):
                    print(f"\n--- Acción {i}: {action.action.upper()} ---")
                    if action.idea_id:
                        print(f"  Idea ID: {action.idea_id}")
                    if action.vote_type:
                        print(f"  Voto: {action.vote_type}")
                    if action.comment_body:
                        print(f"  Comentario:\n{action.comment_body}")
                    if action.new_idea:
                        print(f"  Título: {action.new_idea.title}")
                        print(f"  Categoría: {action.new_idea.category}")
                        print(f"  Descripción:\n{action.new_idea.description}")
        _save_html_report(
                project_label=board_context.project_name or board_context.project_key if board_context else f"Board {settings.jira_board_id}",
                plans=plans,
                outbound_messages=outbound_messages,
                cpo_body=cpo_body,
            )
    else:
        # Ejecutar acciones del roadmap (siempre, salvo --notify-only)
        if not notify_only and roadmap_plan and roadmap_plan.actions:
            created_ideas = _execute_roadmap_plan(settings, roadmap_plan, next_memory)
            if created_ideas:
                _notify_cpo_roadmap(settings, roam, created_ideas)
        if sent > 0:
            next_memory.last_message_sent_at = datetime.now(timezone.utc).isoformat()
            next_memory.last_sent_tickets = dict(next_memory.tickets)
        if is_weekly_run and not roadmap_only:
            next_memory.weekly_last_run_at = datetime.now(timezone.utc).isoformat()
        memory.save(next_memory)
    print(f"Finalizado. Enviadas: {sent}, Saltadas: {skipped}.")
    return 0


def _save_html_report(project_label, plans, outbound_messages, cpo_body) -> None:
    from report_builder import build_html_report
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"reports/report_{timestamp}.html"
    html = build_html_report(
        project_label=project_label,
        plans=plans,
        outbound_messages=outbound_messages,
        cpo_body=cpo_body,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[REPORT] Reporte HTML guardado en: {path}")


def _execute_roadmap_plan(settings, roadmap_plan, next_memory):
    """Ejecuta las acciones del plan de roadmap y actualiza la memoria."""
    import roadmap_client

    try:
        token = roadmap_client.login(
            supabase_url=settings.roadmap_supabase_url,
            anon_key=settings.roadmap_supabase_anon_key,
            email=settings.ps_agent_email,
            password=settings.ps_agent_password,
        )
    except Exception as exc:
        print(f"[WARN] Roadmap login falló al ejecutar plan: {exc}")
        return []

    created_ideas = []

    for action in roadmap_plan.actions:
        try:
            if action.action == "vote" and action.idea_id in next_memory.roadmap.created_idea_ids:
                print(f"[ROADMAP] Skip voto en idea propia {action.idea_id}")
                continue

            if action.action == "vote" and action.idea_id:
                roadmap_client.vote(settings.roadmap_app_url, token, action.idea_id, action.vote_type)
                next_memory.roadmap.voted_idea_ids[action.idea_id] = action.vote_type
                print(f"[ROADMAP] Voto '{action.vote_type}' en idea {action.idea_id}")
                if action.comment_body and action.idea_id not in next_memory.roadmap.commented_idea_ids:
                    roadmap_client.add_comment(settings.roadmap_app_url, token, action.idea_id, action.comment_body)
                    next_memory.roadmap.commented_idea_ids.append(action.idea_id)
                    print(f"[ROADMAP] Comentario de evidencia en idea {action.idea_id}")

            elif action.action == "comment" and action.idea_id and action.comment_body:
                roadmap_client.add_comment(settings.roadmap_app_url, token, action.idea_id, action.comment_body)
                if action.idea_id not in next_memory.roadmap.commented_idea_ids:
                    next_memory.roadmap.commented_idea_ids.append(action.idea_id)
                print(f"[ROADMAP] Comentario en idea {action.idea_id}")

            elif action.action == "reply_comment" and action.idea_id and action.comment_id and action.comment_body:
                roadmap_client.add_comment(
                    settings.roadmap_app_url, token, action.idea_id,
                    action.comment_body, parent_comment_id=action.comment_id,
                )
                next_memory.roadmap.replied_comment_ids.append(action.comment_id)
                print(f"[ROADMAP] Respuesta al comentario {action.comment_id}")

            elif action.action == "create_idea" and action.new_idea:
                result = roadmap_client.create_idea(settings.roadmap_app_url, token, action.new_idea)
                idea_id = result["id"]
                next_memory.roadmap.created_idea_ids.append(idea_id)
                created_ideas.append({"id": idea_id, "title": action.new_idea.title})
                print(f"[ROADMAP] Idea creada: {idea_id} — {action.new_idea.title}")

        except Exception as exc:
            print(f"[WARN] Acción de roadmap falló ({action.action}): {exc}")

    return created_ideas


def _sync_support_tickets(settings, grouped_facts, finalized_tickets, memory_state) -> None:
    """Pushea los tickets clasificados a la roadmap-app. Best-effort.

    Incluye tanto activos (de grouped_facts, ya clasificados por run_agent)
    como finalizados recientes (clasificados acá para obtener su vertical).
    El upsert por key actualiza el resolvedAt de tickets que pasaron a Done
    desde la última corrida.

    No interrumpe el resto del flow si falla (notificaciones, análisis CPO, etc.).
    """
    if not settings.roadmap_app_url:
        return
    if not settings.roadmap_supabase_url or not settings.ps_agent_email:
        return

    # Activos: ya vienen clasificados
    all_facts = [f for facts in grouped_facts.values() for f in facts]

    # Finalizados: clasificarlos para obtener vertical. Las flags
    # (created_today, is_stale, etc.) no las usa el sync — solo necesitamos
    # vertical + datos crudos del ticket.
    if finalized_tickets:
        try:
            from classifier import classify_tickets
            finalized_grouped = classify_tickets(
                tickets=finalized_tickets,
                memory_state=memory_state,
                label_prefix=settings.vertical_label_prefix,
                label_to_vertical=settings.label_to_vertical,
                unchanged_stale_days=settings.unchanged_stale_days,
                last_message_sent_at=memory_state.last_message_sent_at,
                last_sent_tickets=memory_state.last_sent_tickets,
            )
            all_facts.extend(f for facts in finalized_grouped.values() for f in facts)
        except Exception as exc:
            print(f"[WARN] No se pudieron clasificar finalizados para sync: {exc}")

    if not all_facts:
        return

    # Breakdown for diagnostics: cuántos abiertos vs cerrados estamos por enviar
    open_count = sum(1 for f in all_facts if f.status_category.lower() != "done")
    closed_count = sum(1 for f in all_facts if f.status_category.lower() == "done")

    try:
        import roadmap_client
        import roadmap_support_client

        token = roadmap_client.login(
            supabase_url=settings.roadmap_supabase_url,
            anon_key=settings.roadmap_supabase_anon_key,
            email=settings.ps_agent_email,
            password=settings.ps_agent_password,
        )
        result = roadmap_support_client.sync_support_tickets(
            app_url=settings.roadmap_app_url,
            token=token,
            facts=all_facts,
        )
        print(f"[SUPPORT-SYNC] {result.synced} tickets sincronizados ({open_count} abiertos, {closed_count} cerrados), {len(result.errors)} errores.")
        if result.errors:
            for err in result.errors[:5]:
                print(f"  [ERROR] {err.get('key')}: {err.get('message')}")
    except Exception as exc:
        print(f"[WARN] Sync de soporte falló: {exc}")


def _notify_cpo_roadmap(settings, roam, created_ideas):
    """Notifica al CPO sobre ideas creadas en el roadmap."""
    if not settings.roam_cpo_channel_id or not created_ideas:
        return
    lines = ["Nueva idea creada en el roadmap (revisión pendiente)\n"]
    for idea in created_ideas:
        link = f"{settings.roadmap_app_url}/ideas/{idea['id']}"
        lines.append(f"• [{idea['title']}]({link})")
    message = "\n".join(lines)
    try:
        roam.post_message(chat_id=settings.roam_cpo_channel_id, text=message)
        print(f"[ROADMAP] CPO notificado sobre {len(created_ideas)} idea(s) nueva(s).")
    except Exception as exc:
        print(f"[WARN] No se pudo notificar al CPO sobre ideas nuevas: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jira vertical updates a Roam")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el mensaje final por vertical sin enviar a Roam",
    )
    parser.add_argument(
        "--cpo-only",
        action="store_true",
        help="Envía solo el mensaje al canal del CPO, sin notificar canales verticales",
    )
    parser.add_argument(
        "--roadmap-only",
        action="store_true",
        help="Monitorea Jira y ejecuta acciones en el roadmap sin enviar mensajes a los canales de Roam",
    )
    parser.add_argument(
        "--notify-only",
        action="store_true",
        help="Envía mensajes a los canales de Roam sin ejecutar el análisis de roadmap (modo notificación diaria)",
    )
    parser.add_argument(
        "--force-roadmap",
        action="store_true",
        help="Fuerza el análisis de roadmap aunque no haya cambios detectados en Jira",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Fuerza la corrida semanal: envía mensaje CPO al canal C-level y ejecuta el roadmap agent",
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

    raise SystemExit(run(
        dry_run=args.dry_run,
        cpo_only=args.cpo_only,
        roadmap_only=args.roadmap_only,
        notify_only=args.notify_only,
        force_roadmap=args.force_roadmap,
        weekly=args.weekly,
    ))
