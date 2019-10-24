
def get_queryset_model(qs):
    return qs._primary_entity.entity_zero_or_selectable.entity
