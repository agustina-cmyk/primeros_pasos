import json
import os
from dataclasses import dataclass
from typing import Dict

from dotenv import load_dotenv


# Mapping default de label de Jira → vertical de producto. Coincide con la
# configuración documentada en docs/business/glossary.md. Se usa cuando la env
# var LABEL_TO_VERTICAL_JSON no está seteada (o está vacía). Override total
# vía LABEL_TO_VERTICAL_JSON cuando el cliente necesita otros mappings.
DEFAULT_LABEL_TO_VERTICAL: Dict[str, str] = {
    "fefo-team":  "payments",
    "payments":   "payments",
    "eze-team":   "verification",
    "borbotones": "verification",
    "pablo-team": "core",
    "frontend":   "fe",
}


@dataclass(frozen=True)
class Settings:
    jira_base_url: str
    jira_cloud_id: str
    jira_email: str
    jira_api_token: str
    jira_board_id: str
    jira_base_jql: str
    jira_jql: str
    jira_max_results: int
    jira_section_field: str
    jira_criticality_field: str
    jira_environment_field: str
    jira_type_field: str
    vertical_label_prefix: str
    label_to_vertical: Dict[str, str]
    roam_api_token: str
    roam_channel_ids: Dict[str, str]
    roam_channel_urls: Dict[str, str]
    roam_cpo_channel_id: str
    llm_webhook_url: str
    llm_webhook_secret: str
    recurrence_lookback_days: int
    vertical_webhooks: Dict[str, str]
    default_roam_webhook: str
    max_items_per_vertical: int
    unchanged_stale_days: int
    agent_state_path: str
    jira_board_url: str = ""
    roadmap_app_url: str = ""
    roadmap_supabase_url: str = ""
    roadmap_supabase_anon_key: str = ""
    ps_agent_email: str = ""
    ps_agent_password: str = ""


def _load_json_env(var_name: str) -> Dict[str, str]:
    raw = os.getenv(var_name, "{}").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Variable {var_name} no es JSON válido") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Variable {var_name} debe ser un objeto JSON")
    return {str(k).strip().lower(): str(v).strip().lower() for k, v in parsed.items()}


def _required(var_name: str) -> str:
    value = os.getenv(var_name, "").strip()
    if not value:
        raise ValueError(f"Falta variable requerida: {var_name}")
    return value


def load_settings() -> Settings:
    load_dotenv()

    jira_board_id = _required("JIRA_BOARD_ID")

    # Base JQL: filtro de "qué tickets le importan a este agente" SIN filtros de
    # recencia ni estado. Se reusa para el daily (agregando recency) y para el
    # search de finalizados (agregando statusCategory = Done AND updated >= -Nd).
    jira_base_jql = os.getenv("JIRA_BASE_JQL", "").strip()
    if not jira_base_jql:
        jira_base_jql = f"board = {jira_board_id}"

    jira_jql = os.getenv("JIRA_JQL", "").strip()
    if not jira_jql:
        # Incluye todos los tickets abiertos + los que se finalizaron hoy
        jira_jql = (
            f"({jira_base_jql}) AND "
            f"(statusCategory != Done OR updatedDate >= startOfDay()) "
            f"ORDER BY updated DESC"
        )

    return Settings(
        jira_base_url=_required("JIRA_BASE_URL").rstrip("/"),
        jira_cloud_id=os.getenv("JIRA_CLOUD_ID", "").strip(),
        jira_email=_required("JIRA_EMAIL"),
        jira_api_token=_required("JIRA_API_TOKEN"),
        jira_board_id=jira_board_id,
        jira_base_jql=jira_base_jql,
        jira_jql=jira_jql,
        jira_max_results=int(os.getenv("JIRA_MAX_RESULTS", "100")),
        jira_section_field=os.getenv("JIRA_SECTION_FIELD", "").strip(),
        jira_criticality_field=os.getenv("JIRA_CRITICALITY_FIELD", "").strip(),
        jira_environment_field=os.getenv("JIRA_ENVIRONMENT_FIELD", "environment").strip(),
        jira_type_field=os.getenv("JIRA_TYPE_FIELD", "issuetype").strip(),
        vertical_label_prefix=os.getenv("VERTICAL_LABEL_PREFIX", "vertical:").strip().lower(),
        label_to_vertical=_load_json_env("LABEL_TO_VERTICAL_JSON") or DEFAULT_LABEL_TO_VERTICAL,
        roam_api_token=os.getenv("ROAM_API_TOKEN", "").strip(),
        roam_channel_ids=_load_json_env("ROAM_CHANNEL_IDS_JSON"),
        roam_channel_urls=_load_json_env("ROAM_CHANNEL_URLS_JSON"),
        roam_cpo_channel_id=os.getenv("ROAM_CPO_CHANNEL_ID", "").strip(),
        llm_webhook_url=os.getenv("LLM_WEBHOOK_URL", "").strip(),
        llm_webhook_secret=os.getenv("LLM_WEBHOOK_SECRET", "").strip(),
        recurrence_lookback_days=int(os.getenv("RECURRENCE_LOOKBACK_DAYS", "90")),
        vertical_webhooks=_load_json_env("VERTICAL_WEBHOOKS_JSON"),
        default_roam_webhook=os.getenv("DEFAULT_ROAM_WEBHOOK", "").strip(),
        max_items_per_vertical=int(os.getenv("MAX_ITEMS_PER_VERTICAL", "20")),
        unchanged_stale_days=int(os.getenv("UNCHANGED_STALE_DAYS", "5")),
        jira_board_url=os.getenv("JIRA_BOARD_URL", "").strip(),
        agent_state_path=os.getenv("AGENT_STATE_PATH", "data/agent_state.json").strip(),
        roadmap_app_url=os.getenv("ROADMAP_APP_URL", "").strip(),
        roadmap_supabase_url=os.getenv("ROADMAP_SUPABASE_URL", "").strip(),
        roadmap_supabase_anon_key=os.getenv("ROADMAP_SUPABASE_ANON_KEY", "").strip(),
        ps_agent_email=os.getenv("PS_AGENT_EMAIL", "").strip(),
        ps_agent_password=os.getenv("PS_AGENT_PASSWORD", "").strip(),
    )
