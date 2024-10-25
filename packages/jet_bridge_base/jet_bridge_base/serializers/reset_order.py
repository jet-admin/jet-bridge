from sqlalchemy import case
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import load_only

from jet_bridge_base import fields
from jet_bridge_base.db_types import desc_uniform
from jet_bridge_base.serializers.serializer import Serializer


def get_reset_order_serializer(Model, queryset, session):
    class ResetOrderSerializer(Serializer):
        ordering_field = fields.CharField()
        ordering = fields.CharField(required=False, allow_null=True)
        value_ordering = fields.CharField(required=False, allow_null=True)

        def save(self):
            ordering_field = self.validated_data['ordering_field']
            ordering = self.validated_data.get('ordering')
            value_ordering = self.validated_data.get('value_ordering')

            qs = queryset
            order_by = []

            if value_ordering:
                field, values_str = value_ordering.split('-', 2)
                values = values_str.split(',')
                order_by.append(case(
                    [(getattr(Model, field) == x, i) for i, x in enumerate(values)],
                    else_=len(values)
                ))

            if ordering:
                def map_field(name):
                    descending = False
                    if name.startswith('-'):
                        name = name[1:]
                        descending = True
                    field = getattr(Model, name)
                    if descending:
                        field = desc_uniform(field)
                    return field

                order_by.extend(map(lambda x: map_field(x), ordering.split(',')))

            if order_by:
                qs = qs.order_by(*order_by)

            i = 1

            try:
                items = qs.options(load_only(ordering_field)).all()
            except SQLAlchemyError:
                queryset.session.rollback()
                raise

            for instance in items:
                setattr(instance, ordering_field, i)
                i += 1

            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    return ResetOrderSerializer
