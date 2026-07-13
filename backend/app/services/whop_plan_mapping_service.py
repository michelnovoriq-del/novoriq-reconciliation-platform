from app.config import get_settings


def map_whop_plan_to_novoriq_plan(whop_plan_id: str | None, whop_product_id: str | None = None) -> str | None:
    settings = get_settings()
    if whop_plan_id and whop_plan_id == settings.whop_professional_plan_id:
        return "professional"
    if whop_plan_id and whop_plan_id == settings.whop_firm_plan_id:
        return "firm"
    if settings.whop_enterprise_plan_id and whop_plan_id == settings.whop_enterprise_plan_id:
        return "enterprise"
    if whop_product_id and whop_product_id == settings.whop_professional_product_id:
        return "professional"
    if whop_product_id and whop_product_id == settings.whop_firm_product_id:
        return "firm"
    if settings.whop_enterprise_product_id and whop_product_id == settings.whop_enterprise_product_id:
        return "enterprise"
    return None
