from core.admin.models.base import BaseAdminModel
from core.models import Clicker


class ClickerAdmin(BaseAdminModel, model=Clicker):

    column_list = ["name", "coin", "audience", "app_launch_date", "token_launch_date", "is_active"]

    column_searchable_list = ["name", "coin", "audience"]

    column_sortable_list = ["name", "coin", "audience", "app_launch_date", "token_launch_date"]

    column_filters = ["coin", "app_launch_date", "token_launch_date", "is_active"]

    form_columns = [
        "name", "description", "time_spent", "link", "audience", "coin",
        "app_launch_date", "token_launch_date", "telegram_channel", "partners", "comment", "is_active"
    ]

    column_details_list = [
        "id", "name", "description", "time_spent", "link", "audience", "coin",
        "app_launch_date", "token_launch_date", "telegram_channel", "partners", "comment", "is_active"
    ]

    can_edit = True
    can_create = True
    can_delete = True
